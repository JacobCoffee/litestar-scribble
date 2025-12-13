"""Tests for WebSocket real-time functionality."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from scribbl_py.realtime.manager import ConnectedUser, ConnectionManager
from scribbl_py.realtime.messages import (
    CursorMoveMessage,
    ElementAddMessage,
    ElementDeleteMessage,
    ErrorMessage,
    JoinMessage,
    LeaveMessage,
    MessageType,
    SyncMessage,
)

if TYPE_CHECKING:
    pass


class TestMessageTypes:
    """Tests for WebSocket message types."""

    def test_message_type_values(self) -> None:
        """Test that message types have expected string values."""
        assert MessageType.JOIN.value == "join"
        assert MessageType.LEAVE.value == "leave"
        assert MessageType.ELEMENT_ADD.value == "element_add"
        assert MessageType.ELEMENT_UPDATE.value == "element_update"
        assert MessageType.ELEMENT_DELETE.value == "element_delete"
        assert MessageType.CURSOR_MOVE.value == "cursor_move"
        assert MessageType.UNDO.value == "undo"
        assert MessageType.REDO.value == "redo"
        assert MessageType.SYNC.value == "sync"
        assert MessageType.USER_JOINED.value == "user_joined"
        assert MessageType.USER_LEFT.value == "user_left"
        assert MessageType.ELEMENT_ADDED.value == "element_added"
        assert MessageType.ELEMENT_UPDATED.value == "element_updated"
        assert MessageType.ELEMENT_DELETED.value == "element_deleted"
        assert MessageType.CURSOR_MOVED.value == "cursor_moved"
        assert MessageType.UNDO_RESULT.value == "undo_result"
        assert MessageType.REDO_RESULT.value == "redo_result"
        assert MessageType.ERROR.value == "error"

    def test_join_message_to_dict(self) -> None:
        """Test JoinMessage serialization."""
        canvas_id = uuid4()
        msg = JoinMessage(
            canvas_id=canvas_id,
            user_id="user123",
            user_name="Test User",
        )
        data = msg.to_dict()

        assert data["type"] == "join"
        assert data["canvas_id"] == str(canvas_id)
        assert data["user_id"] == "user123"
        assert data["user_name"] == "Test User"
        assert "timestamp" in data

    def test_leave_message_to_dict(self) -> None:
        """Test LeaveMessage serialization."""
        canvas_id = uuid4()
        msg = LeaveMessage(canvas_id=canvas_id, user_id="user123")
        data = msg.to_dict()

        assert data["type"] == "leave"
        assert data["canvas_id"] == str(canvas_id)
        assert data["user_id"] == "user123"

    def test_sync_message_to_dict(self) -> None:
        """Test SyncMessage serialization."""
        canvas_id = uuid4()
        msg = SyncMessage(
            canvas_id=canvas_id,
            canvas_data={"name": "Test Canvas"},
            connected_users=[{"user_id": "user1", "user_name": "User 1"}],
        )
        data = msg.to_dict()

        assert data["type"] == "sync"
        assert data["canvas_id"] == str(canvas_id)
        assert data["canvas"]["name"] == "Test Canvas"
        assert len(data["connected_users"]) == 1

    def test_element_add_message_to_dict(self) -> None:
        """Test ElementAddMessage serialization."""
        canvas_id = uuid4()
        msg = ElementAddMessage(
            canvas_id=canvas_id,
            user_id="user123",
            element_type="stroke",
            element_data={"points": [{"x": 0, "y": 0}]},
        )
        data = msg.to_dict()

        assert data["type"] == "element_add"
        assert data["element_type"] == "stroke"
        assert "element_data" in data

    def test_element_delete_message_to_dict(self) -> None:
        """Test ElementDeleteMessage serialization."""
        canvas_id = uuid4()
        element_id = uuid4()
        msg = ElementDeleteMessage(
            canvas_id=canvas_id,
            user_id="user123",
            element_id=element_id,
        )
        data = msg.to_dict()

        assert data["type"] == "element_delete"
        assert data["element_id"] == str(element_id)

    def test_cursor_move_message_to_dict(self) -> None:
        """Test CursorMoveMessage serialization."""
        canvas_id = uuid4()
        msg = CursorMoveMessage(
            canvas_id=canvas_id,
            user_id="user123",
            user_name="Test User",
            x=100.5,
            y=200.5,
        )
        data = msg.to_dict()

        assert data["type"] == "cursor_move"
        assert data["x"] == 100.5
        assert data["y"] == 200.5
        assert data["user_name"] == "Test User"

    def test_error_message_to_dict(self) -> None:
        """Test ErrorMessage serialization."""
        msg = ErrorMessage(
            code="invalid_request",
            message="Something went wrong",
            details={"field": "canvas_id"},
        )
        data = msg.to_dict()

        assert data["type"] == "error"
        assert data["code"] == "invalid_request"
        assert data["message"] == "Something went wrong"
        assert data["details"]["field"] == "canvas_id"

    def test_error_message_without_details(self) -> None:
        """Test ErrorMessage without details."""
        msg = ErrorMessage(code="error", message="Error")
        data = msg.to_dict()

        assert "details" not in data


class TestConnectionManager:
    """Tests for the ConnectionManager class."""

    @pytest.fixture
    def manager(self) -> ConnectionManager:
        """Create a connection manager for testing."""
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self) -> MagicMock:
        """Create a mock WebSocket."""
        ws = MagicMock()
        ws.send_json = AsyncMock()
        ws.send_text = AsyncMock()
        return ws

    async def test_connect_registers_user(self, manager: ConnectionManager, mock_websocket: MagicMock) -> None:
        """Test that connect registers a user."""
        canvas_id = uuid4()
        user = await manager.connect(mock_websocket, canvas_id, "user1", "User One")

        assert user.user_id == "user1"
        assert user.user_name == "User One"
        assert user.canvas_id == canvas_id
        assert manager.total_connections == 1
        assert manager.active_canvases == 1

    async def test_connect_multiple_users_same_canvas(self, manager: ConnectionManager) -> None:
        """Test multiple users connecting to same canvas."""
        canvas_id = uuid4()
        ws1 = MagicMock()
        ws2 = MagicMock()

        await manager.connect(ws1, canvas_id, "user1", "User 1")
        await manager.connect(ws2, canvas_id, "user2", "User 2")

        assert manager.total_connections == 2
        assert manager.active_canvases == 1

        users = await manager.get_connected_users(canvas_id)
        assert len(users) == 2

    async def test_connect_users_different_canvases(self, manager: ConnectionManager) -> None:
        """Test users connecting to different canvases."""
        canvas1 = uuid4()
        canvas2 = uuid4()
        ws1 = MagicMock()
        ws2 = MagicMock()

        await manager.connect(ws1, canvas1, "user1", "User 1")
        await manager.connect(ws2, canvas2, "user2", "User 2")

        assert manager.total_connections == 2
        assert manager.active_canvases == 2

    async def test_disconnect_removes_user(self, manager: ConnectionManager, mock_websocket: MagicMock) -> None:
        """Test that disconnect removes a user."""
        canvas_id = uuid4()
        await manager.connect(mock_websocket, canvas_id, "user1", "User 1")
        await manager.disconnect(canvas_id, "user1")

        assert manager.total_connections == 0
        assert manager.active_canvases == 0

    async def test_disconnect_cleans_up_empty_canvas(self, manager: ConnectionManager) -> None:
        """Test that empty canvas sessions are cleaned up."""
        canvas_id = uuid4()
        ws1 = MagicMock()
        ws2 = MagicMock()

        await manager.connect(ws1, canvas_id, "user1", "User 1")
        await manager.connect(ws2, canvas_id, "user2", "User 2")

        await manager.disconnect(canvas_id, "user1")
        assert manager.active_canvases == 1

        await manager.disconnect(canvas_id, "user2")
        assert manager.active_canvases == 0

    async def test_get_connected_users_empty_canvas(self, manager: ConnectionManager) -> None:
        """Test getting users from non-existent canvas."""
        users = await manager.get_connected_users(uuid4())
        assert users == []

    async def test_get_user(self, manager: ConnectionManager, mock_websocket: MagicMock) -> None:
        """Test getting a specific user."""
        canvas_id = uuid4()
        await manager.connect(mock_websocket, canvas_id, "user1", "User 1")

        user = await manager.get_user(canvas_id, "user1")
        assert user is not None
        assert user.user_id == "user1"

        user = await manager.get_user(canvas_id, "nonexistent")
        assert user is None

    async def test_update_cursor(self, manager: ConnectionManager, mock_websocket: MagicMock) -> None:
        """Test updating cursor position."""
        canvas_id = uuid4()
        await manager.connect(mock_websocket, canvas_id, "user1", "User 1")

        await manager.update_cursor(canvas_id, "user1", 100.0, 200.0)

        user = await manager.get_user(canvas_id, "user1")
        assert user is not None
        assert user.cursor_x == 100.0
        assert user.cursor_y == 200.0

    async def test_broadcast_sends_to_all_users(self, manager: ConnectionManager) -> None:
        """Test broadcasting to all users."""
        canvas_id = uuid4()
        ws1 = MagicMock()
        ws1.send_text = AsyncMock()
        ws2 = MagicMock()
        ws2.send_text = AsyncMock()

        await manager.connect(ws1, canvas_id, "user1", "User 1")
        await manager.connect(ws2, canvas_id, "user2", "User 2")

        message = {"type": "test", "data": "hello"}
        await manager.broadcast(canvas_id, message)

        ws1.send_text.assert_called_once()
        ws2.send_text.assert_called_once()

        # Verify message content
        sent_msg = json.loads(ws1.send_text.call_args[0][0])
        assert sent_msg["type"] == "test"

    async def test_broadcast_excludes_user(self, manager: ConnectionManager) -> None:
        """Test broadcasting with user exclusion."""
        canvas_id = uuid4()
        ws1 = MagicMock()
        ws1.send_text = AsyncMock()
        ws2 = MagicMock()
        ws2.send_text = AsyncMock()

        await manager.connect(ws1, canvas_id, "user1", "User 1")
        await manager.connect(ws2, canvas_id, "user2", "User 2")

        message = {"type": "test"}
        await manager.broadcast(canvas_id, message, exclude_user="user1")

        ws1.send_text.assert_not_called()
        ws2.send_text.assert_called_once()

    async def test_send_to_user(self, manager: ConnectionManager, mock_websocket: MagicMock) -> None:
        """Test sending to a specific user."""
        canvas_id = uuid4()
        await manager.connect(mock_websocket, canvas_id, "user1", "User 1")

        result = await manager.send_to_user(canvas_id, "user1", {"type": "test"})
        assert result is True
        mock_websocket.send_json.assert_called_once()

    async def test_send_to_nonexistent_user(self, manager: ConnectionManager) -> None:
        """Test sending to non-existent user."""
        result = await manager.send_to_user(uuid4(), "nonexistent", {"type": "test"})
        assert result is False


class TestConnectedUser:
    """Tests for the ConnectedUser dataclass."""

    def test_to_dict(self) -> None:
        """Test ConnectedUser serialization."""
        canvas_id = uuid4()
        ws = MagicMock()
        user = ConnectedUser(
            user_id="user123",
            user_name="Test User",
            websocket=ws,
            canvas_id=canvas_id,
            cursor_x=50.0,
            cursor_y=75.0,
        )
        data = user.to_dict()

        assert data["user_id"] == "user123"
        assert data["user_name"] == "Test User"
        assert data["cursor_x"] == 50.0
        assert data["cursor_y"] == 75.0
        assert "connected_at" in data


class TestWebSocketIntegration:
    """Integration tests for WebSocket functionality with Litestar."""

    @pytest.fixture
    def canvas_service(self) -> AsyncMock:
        """Create a mock canvas service."""
        from scribbl_py.core.models import Canvas

        service = AsyncMock()
        canvas = Canvas(name="Test Canvas")
        service.get_canvas.return_value = canvas
        service.list_elements.return_value = []
        return service

    @pytest.fixture
    def connection_manager(self) -> ConnectionManager:
        """Create a connection manager."""
        return ConnectionManager()

    async def test_websocket_handler_creation(
        self,
        connection_manager: ConnectionManager,
        canvas_service: AsyncMock,
    ) -> None:
        """Test that WebSocket handler can be created."""
        from scribbl_py.realtime.handler import (
            CanvasWebSocketHandler,
            create_websocket_handler,
        )

        handler = CanvasWebSocketHandler(connection_manager, canvas_service)
        assert handler is not None

        router = create_websocket_handler("/ws", connection_manager, canvas_service)
        assert router is not None
