"""WebSocket handler for real-time canvas collaboration."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any
from uuid import UUID

import structlog
from litestar import Router, WebSocket, websocket

from scribbl_py.core.models import Point
from scribbl_py.core.style import ElementStyle
from scribbl_py.core.types import ShapeType
from scribbl_py.exceptions import CanvasNotFoundError
from scribbl_py.realtime.manager import ConnectionManager
from scribbl_py.realtime.messages import (
    CursorMoveMessage,
    ElementAddMessage,
    ElementDeleteMessage,
    ErrorMessage,
    MessageType,
    StrokeContinueMessage,
    StrokeEndMessage,
    StrokeStartMessage,
    SyncMessage,
)
from scribbl_py.web.dto import element_to_response

if TYPE_CHECKING:
    from scribbl_py.services.canvas import CanvasService

logger = structlog.get_logger(__name__)


class CanvasWebSocketHandler:
    """Handler for canvas WebSocket connections.

    This handler manages WebSocket connections for canvas sessions,
    handling user connections, element changes, and cursor synchronization.
    """

    def __init__(
        self,
        connection_manager: ConnectionManager,
        canvas_service: CanvasService,
    ) -> None:
        """Initialize the WebSocket handler.

        Args:
            connection_manager: The connection manager instance.
            canvas_service: The canvas service instance.
        """
        self._manager = connection_manager
        self._service = canvas_service
        self._user_data: dict[int, dict[str, Any]] = {}
        self._temp_strokes: dict[str, dict[str, Any]] = {}

    async def handle_connection(self, socket: WebSocket, canvas_id: UUID) -> None:
        """Handle a WebSocket connection for a canvas.

        Args:
            socket: The WebSocket connection.
            canvas_id: The canvas ID from the URL.
        """
        # Verify canvas exists before accepting
        try:
            await self._service.get_canvas(canvas_id)
        except CanvasNotFoundError:
            await socket.close(code=4004, reason="Canvas not found")
            return

        await socket.accept()

        # Store connection data
        socket_id = id(socket)
        self._user_data[socket_id] = {
            "canvas_id": canvas_id,
            "user_id": None,
            "user_name": "Anonymous",
        }

        logger.debug(
            "WebSocket connection accepted",
            canvas_id=str(canvas_id),
        )

        try:
            await self._receive_loop(socket)
        except Exception:
            logger.exception("WebSocket error", canvas_id=str(canvas_id))
        finally:
            await self._handle_disconnect(socket)

    async def _receive_loop(self, socket: WebSocket) -> None:
        """Main receive loop for WebSocket messages.

        Args:
            socket: The WebSocket connection.
        """
        async for message in socket.iter_data():
            socket_id = id(socket)
            user_data = self._user_data.get(socket_id)

            if not user_data:
                await self._send_error(socket, "connection_error", "Connection not initialized")
                continue

            try:
                data = json.loads(message) if isinstance(message, str) else message
            except json.JSONDecodeError:
                await self._send_error(socket, "invalid_json", "Invalid JSON message")
                continue

            msg_type = data.get("type")
            if not msg_type:
                await self._send_error(socket, "missing_type", "Message type is required")
                continue

            try:
                await self._handle_message(socket, user_data, data)
            except Exception:
                logger.exception(
                    "Error handling message",
                    message_type=msg_type,
                    canvas_id=str(user_data.get("canvas_id")),
                )
                await self._send_error(socket, "internal_error", "Internal server error")

    async def _handle_disconnect(self, socket: WebSocket) -> None:
        """Handle WebSocket disconnection.

        Args:
            socket: The WebSocket connection.
        """
        socket_id = id(socket)
        user_data = self._user_data.pop(socket_id, None)

        if user_data and user_data.get("user_id"):
            canvas_id = user_data["canvas_id"]
            user_id = user_data["user_id"]

            await self._manager.disconnect(canvas_id, user_id)

            # Notify other users
            await self._manager.broadcast(
                canvas_id,
                {
                    "type": MessageType.USER_LEFT.value,
                    "user_id": user_id,
                    "user_name": user_data.get("user_name", "Anonymous"),
                },
            )

            logger.info(
                "User left canvas",
                user_id=user_id,
                canvas_id=str(canvas_id),
            )

    async def _handle_message(
        self,
        socket: WebSocket,
        user_data: dict[str, Any],
        message: dict[str, Any],
    ) -> None:
        """Route message to appropriate handler.

        Args:
            socket: The WebSocket connection.
            user_data: The user's connection data.
            message: The parsed message.
        """
        msg_type = message.get("type")

        handlers = {
            MessageType.JOIN.value: self._handle_join,
            MessageType.ELEMENT_ADD.value: self._handle_element_add,
            MessageType.ELEMENT_UPDATE.value: self._handle_element_update,
            MessageType.ELEMENT_DELETE.value: self._handle_element_delete,
            MessageType.CURSOR_MOVE.value: self._handle_cursor_move,
            MessageType.UNDO.value: self._handle_undo,
            MessageType.REDO.value: self._handle_redo,
            MessageType.STROKE_START.value: self._handle_stroke_start,
            MessageType.STROKE_CONTINUE.value: self._handle_stroke_continue,
            MessageType.STROKE_END.value: self._handle_stroke_end,
            "get_elements": self._handle_get_elements,
            "layer_action": self._handle_layer_action,
        }

        handler = handlers.get(msg_type)
        if handler:
            await handler(socket, user_data, message)
        else:
            await self._send_error(socket, "unknown_type", f"Unknown message type: {msg_type}")

    async def _handle_join(
        self,
        socket: WebSocket,
        user_data: dict[str, Any],
        message: dict[str, Any],
    ) -> None:
        """Handle user joining a canvas session.

        Args:
            socket: The WebSocket connection.
            user_data: The user's connection data.
            message: The join message.
        """
        canvas_id = user_data["canvas_id"]
        user_id = message.get("user_id", str(id(socket)))
        user_name = message.get("user_name", "Anonymous")

        # Update user data
        user_data["user_id"] = user_id
        user_data["user_name"] = user_name

        # Register connection
        await self._manager.connect(socket, canvas_id, user_id, user_name)

        # Get canvas data
        canvas = await self._service.get_canvas(canvas_id)
        elements = await self._service.list_elements(canvas_id)
        connected_users = await self._manager.get_connected_users(canvas_id)

        # Send sync message to joining user
        sync_msg = SyncMessage(
            canvas_id=canvas_id,
            canvas_data={
                "id": str(canvas.id),
                "name": canvas.name,
                "width": canvas.width,
                "height": canvas.height,
                "background_color": canvas.background_color,
                "elements": [self._element_to_dict(e) for e in elements],
            },
            connected_users=[u.to_dict() for u in connected_users],
        )
        await socket.send_json(sync_msg.to_dict())

        # Notify other users
        await self._manager.broadcast(
            canvas_id,
            {
                "type": MessageType.USER_JOINED.value,
                "user_id": user_id,
                "user_name": user_name,
            },
            exclude_user=user_id,
        )

        logger.info(
            "User joined canvas",
            user_id=user_id,
            user_name=user_name,
            canvas_id=str(canvas_id),
        )

    def _element_to_dict(self, element: Any) -> dict[str, Any]:
        """Convert element to dict for serialization.

        Args:
            element: The element to convert.

        Returns:
            Dictionary representation of the element.
        """
        response = element_to_response(element)
        result = {
            "id": str(response.id),
            "element_type": response.element_type.value,
            "position": {"x": response.position.x, "y": response.position.y, "pressure": response.position.pressure},
            "style": {
                "stroke_color": response.style.stroke_color,
                "fill_color": response.style.fill_color,
                "stroke_width": response.style.stroke_width,
                "opacity": response.style.opacity,
            },
            "z_index": element.z_index,
            "visible": element.visible,
            "locked": element.locked,
            "created_at": response.created_at.isoformat(),
        }

        if response.stroke_data:
            result["stroke_data"] = {
                "points": [{"x": p.x, "y": p.y, "pressure": p.pressure} for p in response.stroke_data.points],
                "smoothing": response.stroke_data.smoothing,
            }
        if response.shape_data:
            result["shape_data"] = {
                "shape_type": response.shape_data.shape_type.value,
                "width": response.shape_data.width,
                "height": response.shape_data.height,
                "rotation": response.shape_data.rotation,
            }
        if response.text_data:
            result["text_data"] = {
                "content": response.text_data.content,
                "font_size": response.text_data.font_size,
                "font_family": response.text_data.font_family,
            }

        return result

    async def _handle_element_add(
        self,
        socket: WebSocket,
        user_data: dict[str, Any],
        message: dict[str, Any],
    ) -> None:
        """Handle adding a new element.

        Args:
            socket: The WebSocket connection.
            user_data: The user's connection data.
            message: The element add message.
        """
        canvas_id = user_data["canvas_id"]
        user_id = user_data.get("user_id")

        if not user_id:
            await self._send_error(socket, "not_joined", "Must join canvas first")
            return

        element_type = message.get("element_type")
        element_data = message.get("element_data", {})

        try:
            element = await self._create_element(canvas_id, element_type, element_data)
        except ValueError as e:
            await self._send_error(socket, "invalid_element", str(e))
            return

        # Broadcast to all users including sender
        broadcast_msg = ElementAddMessage(
            canvas_id=canvas_id,
            user_id=user_id,
            element_type=element_type,
            element_data=self._element_to_dict(element),
        )
        broadcast_data = broadcast_msg.to_dict()
        broadcast_data["type"] = MessageType.ELEMENT_ADDED.value

        await self._manager.broadcast(canvas_id, broadcast_data)

        logger.debug(
            "Element added",
            element_id=str(element.id),
            element_type=element_type,
            canvas_id=str(canvas_id),
            user_id=user_id,
        )

    async def _create_element(
        self,
        canvas_id: UUID,
        element_type: str,
        data: dict[str, Any],
    ) -> Any:
        """Create an element based on type.

        Args:
            canvas_id: The canvas ID.
            element_type: Type of element (stroke, shape, text).
            data: Element data.

        Returns:
            The created element.

        Raises:
            ValueError: If element type is invalid or data is missing.
        """
        style = None
        if "style" in data:
            style_data = data["style"]
            style = ElementStyle(
                stroke_color=style_data.get("stroke_color", "#000000"),
                fill_color=style_data.get("fill_color"),
                stroke_width=style_data.get("stroke_width", 2.0),
                opacity=style_data.get("opacity", 1.0),
            )

        if element_type == "stroke":
            points_data = data.get("points", [])
            if not points_data:
                msg = "Stroke requires points"
                raise ValueError(msg)
            points = [
                Point(
                    x=p.get("x", 0),
                    y=p.get("y", 0),
                    pressure=p.get("pressure", 1.0),
                )
                for p in points_data
            ]
            return await self._service.add_stroke(
                canvas_id,
                points=points,
                style=style,
                smoothing=data.get("smoothing", 0.5),
            )

        if element_type == "shape":
            return await self._service.add_shape(
                canvas_id,
                shape_type=ShapeType(data.get("shape_type", "rectangle")),
                position=Point(x=data.get("x", 0), y=data.get("y", 0)),
                width=data.get("width", 100),
                height=data.get("height", 100),
                style=style,
                rotation=data.get("rotation", 0.0),
            )

        if element_type == "text":
            return await self._service.add_text(
                canvas_id,
                content=data.get("content", ""),
                position=Point(x=data.get("x", 0), y=data.get("y", 0)),
                style=style,
                font_size=data.get("font_size", 16),
                font_family=data.get("font_family", "sans-serif"),
            )

        msg = f"Unknown element type: {element_type}"
        raise ValueError(msg)

    async def _handle_element_update(
        self,
        socket: WebSocket,
        user_data: dict[str, Any],
        message: dict[str, Any],
    ) -> None:
        """Handle element update with conflict resolution.

        Uses last-write-wins strategy with version tracking.

        Args:
            socket: The WebSocket connection.
            user_data: The user's connection data.
            message: The element update message.
        """
        canvas_id = user_data["canvas_id"]
        user_id = user_data.get("user_id")

        if not user_id:
            await self._send_error(socket, "not_joined", "Must join canvas first")
            return

        element_id_str = message.get("element_id")
        if not element_id_str:
            await self._send_error(socket, "missing_element_id", "Element ID required")
            return

        try:
            element_id = UUID(element_id_str)
        except ValueError:
            await self._send_error(socket, "invalid_element_id", "Invalid element ID format")
            return

        updates = message.get("updates", {})
        version = message.get("version", 1)

        # Broadcast update to all users
        broadcast_data = {
            "type": MessageType.ELEMENT_UPDATED.value,
            "canvas_id": str(canvas_id),
            "user_id": user_id,
            "element_id": str(element_id),
            "updates": updates,
            "version": version,
        }

        await self._manager.broadcast(canvas_id, broadcast_data)

        logger.debug(
            "Element updated",
            element_id=str(element_id),
            canvas_id=str(canvas_id),
            user_id=user_id,
            version=version,
        )

    async def _handle_element_delete(
        self,
        socket: WebSocket,
        user_data: dict[str, Any],
        message: dict[str, Any],
    ) -> None:
        """Handle element deletion.

        Args:
            socket: The WebSocket connection.
            user_data: The user's connection data.
            message: The element delete message.
        """
        canvas_id = user_data["canvas_id"]
        user_id = user_data.get("user_id")

        if not user_id:
            await self._send_error(socket, "not_joined", "Must join canvas first")
            return

        element_id_str = message.get("element_id")
        if not element_id_str:
            await self._send_error(socket, "missing_element_id", "Element ID required")
            return

        try:
            element_id = UUID(element_id_str)
        except ValueError:
            await self._send_error(socket, "invalid_element_id", "Invalid element ID format")
            return

        # Delete element
        deleted = await self._service.delete_element(canvas_id, element_id)

        if deleted:
            # Broadcast deletion
            delete_msg = ElementDeleteMessage(
                canvas_id=canvas_id,
                user_id=user_id,
                element_id=element_id,
            )
            broadcast_data = delete_msg.to_dict()
            broadcast_data["type"] = MessageType.ELEMENT_DELETED.value

            await self._manager.broadcast(canvas_id, broadcast_data)

            logger.debug(
                "Element deleted",
                element_id=str(element_id),
                canvas_id=str(canvas_id),
                user_id=user_id,
            )
        else:
            await self._send_error(socket, "element_not_found", "Element not found")

    async def _handle_cursor_move(
        self,
        socket: WebSocket,
        user_data: dict[str, Any],
        message: dict[str, Any],
    ) -> None:
        """Handle cursor position updates.

        Args:
            socket: The WebSocket connection.
            user_data: The user's connection data.
            message: The cursor move message.
        """
        canvas_id = user_data["canvas_id"]
        user_id = user_data.get("user_id")

        if not user_id:
            return  # Silently ignore cursor moves before join

        x = message.get("x", 0.0)
        y = message.get("y", 0.0)

        # Update cursor position
        await self._manager.update_cursor(canvas_id, user_id, x, y)

        # Broadcast to other users
        cursor_msg = CursorMoveMessage(
            canvas_id=canvas_id,
            user_id=user_id,
            user_name=user_data.get("user_name", "Anonymous"),
            x=x,
            y=y,
        )
        broadcast_data = cursor_msg.to_dict()
        broadcast_data["type"] = MessageType.CURSOR_MOVED.value

        await self._manager.broadcast(canvas_id, broadcast_data, exclude_user=user_id)

    async def _handle_undo(
        self,
        socket: WebSocket,
        user_data: dict[str, Any],
        message: dict[str, Any],
    ) -> None:
        """Handle undo operation.

        Args:
            socket: The WebSocket connection.
            user_data: The user's connection data.
            message: The undo message.
        """
        canvas_id = user_data["canvas_id"]
        user_id = user_data.get("user_id")

        if not user_id:
            await self._send_error(socket, "not_joined", "Must join canvas first")
            return

        # Perform undo operation
        success = await self._service.undo(canvas_id, user_id)

        if success:
            # Get updated canvas state
            elements = await self._service.list_elements(canvas_id)
            can_undo = self._service.can_undo(canvas_id)
            can_redo = self._service.can_redo(canvas_id)

            # Broadcast result to all users
            broadcast_data = {
                "type": MessageType.UNDO_RESULT.value,
                "canvas_id": str(canvas_id),
                "user_id": user_id,
                "success": True,
                "can_undo": can_undo,
                "can_redo": can_redo,
                "elements": [self._element_to_dict(e) for e in elements],
            }

            await self._manager.broadcast(canvas_id, broadcast_data)

            logger.debug(
                "Undo operation completed",
                canvas_id=str(canvas_id),
                user_id=user_id,
            )
        else:
            await self._send_error(socket, "nothing_to_undo", "No operation to undo")

    async def _handle_redo(
        self,
        socket: WebSocket,
        user_data: dict[str, Any],
        message: dict[str, Any],
    ) -> None:
        """Handle redo operation.

        Args:
            socket: The WebSocket connection.
            user_data: The user's connection data.
            message: The redo message.
        """
        canvas_id = user_data["canvas_id"]
        user_id = user_data.get("user_id")

        if not user_id:
            await self._send_error(socket, "not_joined", "Must join canvas first")
            return

        # Perform redo operation
        success = await self._service.redo(canvas_id, user_id)

        if success:
            # Get updated canvas state
            elements = await self._service.list_elements(canvas_id)
            can_undo = self._service.can_undo(canvas_id)
            can_redo = self._service.can_redo(canvas_id)

            # Broadcast result to all users
            broadcast_data = {
                "type": MessageType.REDO_RESULT.value,
                "canvas_id": str(canvas_id),
                "user_id": user_id,
                "success": True,
                "can_undo": can_undo,
                "can_redo": can_redo,
                "elements": [self._element_to_dict(e) for e in elements],
            }

            await self._manager.broadcast(canvas_id, broadcast_data)

            logger.debug(
                "Redo operation completed",
                canvas_id=str(canvas_id),
                user_id=user_id,
            )
        else:
            await self._send_error(socket, "nothing_to_redo", "No operation to redo")

    async def _handle_stroke_start(
        self,
        socket: WebSocket,
        user_data: dict[str, Any],
        message: dict[str, Any],
    ) -> None:
        """Handle stroke start event.

        Args:
            socket: The WebSocket connection.
            user_data: The user's connection data.
            message: The stroke start message.
        """
        canvas_id = user_data["canvas_id"]
        user_id = user_data.get("user_id")

        if not user_id:
            await self._send_error(socket, "not_joined", "Must join canvas first")
            return

        stroke_id = message.get("stroke_id")
        point = message.get("point")
        style = message.get("style", {})

        if not stroke_id or not point:
            await self._send_error(socket, "invalid_stroke_start", "Missing stroke_id or point")
            return

        # Store temporary stroke data
        self._temp_strokes[stroke_id] = {
            "canvas_id": canvas_id,
            "user_id": user_id,
            "points": [point],
            "style": style,
        }

        # Broadcast to other users
        start_msg = StrokeStartMessage(
            canvas_id=canvas_id,
            user_id=user_id,
            stroke_id=stroke_id,
            point=point,
            style=style,
        )
        broadcast_data = start_msg.to_dict()
        broadcast_data["type"] = MessageType.STROKE_STARTED.value

        await self._manager.broadcast(canvas_id, broadcast_data, exclude_user=user_id)

        logger.debug(
            "Stroke started",
            stroke_id=stroke_id,
            canvas_id=str(canvas_id),
            user_id=user_id,
        )

    async def _handle_stroke_continue(
        self,
        socket: WebSocket,
        user_data: dict[str, Any],
        message: dict[str, Any],
    ) -> None:
        """Handle stroke continue event.

        Args:
            socket: The WebSocket connection.
            user_data: The user's connection data.
            message: The stroke continue message.
        """
        canvas_id = user_data["canvas_id"]
        user_id = user_data.get("user_id")

        if not user_id:
            return  # Silently ignore if not joined

        stroke_id = message.get("stroke_id")
        points = message.get("points", [])

        if not stroke_id or not points:
            return  # Silently ignore invalid data during drawing

        # Update temporary stroke data
        if stroke_id in self._temp_strokes:
            self._temp_strokes[stroke_id]["points"].extend(points)

        # Broadcast to other users
        continue_msg = StrokeContinueMessage(
            canvas_id=canvas_id,
            user_id=user_id,
            stroke_id=stroke_id,
            points=points,
        )
        broadcast_data = continue_msg.to_dict()
        broadcast_data["type"] = MessageType.STROKE_CONTINUED.value

        await self._manager.broadcast(canvas_id, broadcast_data, exclude_user=user_id)

    async def _handle_stroke_end(
        self,
        socket: WebSocket,
        user_data: dict[str, Any],
        message: dict[str, Any],
    ) -> None:
        """Handle stroke end event.

        Args:
            socket: The WebSocket connection.
            user_data: The user's connection data.
            message: The stroke end message.
        """
        canvas_id = user_data["canvas_id"]
        user_id = user_data.get("user_id")

        if not user_id:
            await self._send_error(socket, "not_joined", "Must join canvas first")
            return

        stroke_id = message.get("stroke_id")

        if not stroke_id:
            await self._send_error(socket, "invalid_stroke_end", "Missing stroke_id")
            return

        # Get temporary stroke data
        stroke_data = self._temp_strokes.pop(stroke_id, None)

        if not stroke_data or len(stroke_data.get("points", [])) < 2:
            # Not enough points for a valid stroke
            return

        # Create the final stroke element
        try:
            points = [
                Point(
                    x=p.get("x", 0),
                    y=p.get("y", 0),
                    pressure=p.get("pressure", 1.0),
                )
                for p in stroke_data["points"]
            ]

            style_data = stroke_data.get("style", {})
            style = ElementStyle(
                stroke_color=style_data.get("stroke_color", "#000000"),
                fill_color=style_data.get("fill_color"),
                stroke_width=style_data.get("stroke_width", 2.0),
                opacity=style_data.get("opacity", 1.0),
            )

            element = await self._service.add_stroke(
                canvas_id,
                points=points,
                style=style,
                smoothing=0.5,
            )

            # Broadcast stroke end with final element data
            end_msg = StrokeEndMessage(
                canvas_id=canvas_id,
                user_id=user_id,
                stroke_id=stroke_id,
            )
            broadcast_data = end_msg.to_dict()
            broadcast_data["type"] = MessageType.STROKE_ENDED.value
            broadcast_data["element_data"] = self._element_to_dict(element)

            await self._manager.broadcast(canvas_id, broadcast_data)

            logger.debug(
                "Stroke ended",
                stroke_id=stroke_id,
                element_id=str(element.id),
                canvas_id=str(canvas_id),
                user_id=user_id,
            )
        except Exception:
            logger.exception(
                "Error creating stroke element",
                stroke_id=stroke_id,
                canvas_id=str(canvas_id),
            )
            await self._send_error(socket, "stroke_creation_failed", "Failed to create stroke")

    async def _handle_get_elements(
        self,
        socket: WebSocket,
        user_data: dict[str, Any],
        message: dict[str, Any],
    ) -> None:
        """Handle request for elements list.

        Args:
            socket: The WebSocket connection.
            user_data: The user's connection data.
            message: The message (unused).
        """
        canvas_id = user_data["canvas_id"]

        elements = await self._service.list_elements(canvas_id)

        await socket.send_json({
            "type": "elements_list",
            "elements": [self._element_to_dict(e) for e in elements],
        })

    async def _handle_layer_action(
        self,
        socket: WebSocket,
        user_data: dict[str, Any],
        message: dict[str, Any],
    ) -> None:
        """Handle layer management actions.

        Args:
            socket: The WebSocket connection.
            user_data: The user's connection data.
            message: The layer action message.
        """
        canvas_id = user_data["canvas_id"]
        user_id = user_data.get("user_id", "system")

        action = message.get("action")
        element_id_str = message.get("element_id")

        if not element_id_str:
            await self._send_error(socket, "missing_element_id", "Element ID required")
            return

        try:
            element_id = UUID(element_id_str)
        except ValueError:
            await self._send_error(socket, "invalid_element_id", "Invalid element ID format")
            return

        try:
            if action == "toggle_visibility":
                element = await self._service.toggle_visibility(canvas_id, element_id, user_id)
                updates = {"visible": element.visible}

            elif action == "toggle_lock":
                element = await self._service.toggle_lock(canvas_id, element_id, user_id)
                updates = {"locked": element.locked}

            elif action == "bring_to_front":
                element = await self._service.bring_to_front(canvas_id, element_id, user_id)
                updates = {"z_index": element.z_index}

            elif action == "send_to_back":
                element = await self._service.send_to_back(canvas_id, element_id, user_id)
                updates = {"z_index": element.z_index}

            elif action == "move_forward":
                element = await self._service.move_forward(canvas_id, element_id, user_id)
                updates = {"z_index": element.z_index}

            elif action == "move_backward":
                element = await self._service.move_backward(canvas_id, element_id, user_id)
                updates = {"z_index": element.z_index}

            elif action == "delete":
                deleted = await self._service.delete_element(canvas_id, element_id, user_id)
                if deleted:
                    await self._manager.broadcast(canvas_id, {
                        "type": "element_deleted",
                        "element_id": str(element_id),
                    })
                    logger.debug(
                        "Layer deleted",
                        element_id=str(element_id),
                        canvas_id=str(canvas_id),
                    )
                return

            else:
                await self._send_error(socket, "unknown_action", f"Unknown layer action: {action}")
                return

            # Broadcast the update to all clients
            await self._manager.broadcast(canvas_id, {
                "type": "element_updated",
                "element_id": str(element_id),
                "updates": updates,
            })

            logger.debug(
                "Layer action completed",
                action=action,
                element_id=str(element_id),
                canvas_id=str(canvas_id),
            )

        except Exception:
            logger.exception(
                "Error handling layer action",
                action=action,
                element_id=str(element_id),
                canvas_id=str(canvas_id),
            )
            await self._send_error(socket, "layer_action_failed", f"Failed to execute layer action: {action}")

    async def _send_error(
        self,
        socket: WebSocket,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Send an error message to the client.

        Args:
            socket: The WebSocket connection.
            code: Error code.
            message: Error message.
            details: Additional error details.
        """
        error_msg = ErrorMessage(code=code, message=message, details=details)
        await socket.send_json(error_msg.to_dict())


def create_websocket_handler(
    path: str,
    connection_manager: ConnectionManager,
    canvas_service: CanvasService,
) -> Router:
    """Create a WebSocket router for canvas real-time collaboration.

    Args:
        path: Base path for WebSocket routes.
        connection_manager: The connection manager instance.
        canvas_service: The canvas service instance.

    Returns:
        A Litestar Router with WebSocket handlers.
    """
    handler = CanvasWebSocketHandler(connection_manager, canvas_service)

    @websocket(path="/canvas/{canvas_id:uuid}")
    async def canvas_websocket(socket: WebSocket, canvas_id: UUID) -> None:
        """WebSocket endpoint for canvas real-time collaboration.

        Args:
            socket: The WebSocket connection.
            canvas_id: The canvas ID from the URL.
        """
        await handler.handle_connection(socket, canvas_id)

    return Router(path=path, route_handlers=[canvas_websocket], tags=["WebSocket"])
