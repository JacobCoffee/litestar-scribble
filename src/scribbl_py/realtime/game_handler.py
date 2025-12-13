"""WebSocket handler for CanvasClash game mode real-time communication."""

from __future__ import annotations

import asyncio
import json
import random
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

import structlog

from scribbl_py.game.models import (
    GuessResult,
    Player,
    PlayerState,
    Round,
)
from scribbl_py.game.moderation import filter_message
from scribbl_py.realtime.manager import ConnectionManager
from scribbl_py.services.game import GameNotFoundError, GameStateError, PlayerNotFoundError
from scribbl_py.services.telemetry import get_telemetry

if TYPE_CHECKING:
    from litestar import Router, WebSocket

    from scribbl_py.game.models import GameRoom
    from scribbl_py.services.game import GameService

logger = structlog.get_logger(__name__)


@dataclass
class GameConnection:
    """Represents a player's WebSocket connection to a game."""

    socket: WebSocket
    room_id: UUID
    player_id: UUID
    user_id: str
    user_name: str
    connected_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class GameMessageType:
    """Message types for game WebSocket communication."""

    # Client -> Server
    JOIN = "join"
    LEAVE = "leave"
    START_GAME = "start_game"
    SELECT_WORD = "select_word"
    GUESS = "guess"
    CHAT = "chat"
    DRAW = "draw"
    DRAW_SHAPE = "draw_shape"
    FILL = "fill"
    CLEAR = "clear"
    KICK_PLAYER = "kick_player"
    BAN_PLAYER = "ban_player"
    TRANSFER_HOST = "transfer_host"

    # Server -> Client
    ROOM_STATE = "room_state"
    PLAYER_JOINED = "player_joined"
    PLAYER_LEFT = "player_left"
    PLAYER_KICKED = "player_kicked"
    PLAYER_BANNED = "player_banned"
    HOST_TRANSFERRED = "host_transferred"
    YOU_WERE_KICKED = "you_were_kicked"
    YOU_WERE_BANNED = "you_were_banned"
    GAME_STARTED = "game_started"
    ROUND_STARTED = "round_started"
    WORD_OPTIONS = "word_options"
    WORD_SELECTED = "word_selected"
    TIMER_UPDATE = "timer_update"
    GUESS_RESULT = "guess_result"
    CHAT_MESSAGE = "chat_message"
    CORRECT_GUESS = "correct_guess"
    HINT_UPDATE = "hint_update"
    SCORE_UPDATE = "score_update"
    ROUND_END = "round_end"
    GAME_OVER = "game_over"
    DRAW_STROKE = "draw_stroke"
    CLEAR_CANVAS = "clear_canvas"
    ERROR = "error"


class GameWebSocketHandler:
    """Handler for game WebSocket connections.

    Manages WebSocket connections for CanvasClash game sessions,
    handling player communications, game flow, and drawing sync.
    """

    def __init__(
        self,
        game_service: GameService,
        connection_manager: ConnectionManager | None = None,
    ) -> None:
        """Initialize the game WebSocket handler.

        Args:
            game_service: The game service instance.
            connection_manager: Optional connection manager for advanced tracking.
        """
        self._service = game_service
        self._manager = connection_manager or ConnectionManager()
        self._connections: dict[int, GameConnection] = {}  # socket_id -> connection
        self._room_sockets: dict[UUID, set[int]] = {}  # room_id -> socket_ids
        self._timer_tasks: dict[UUID, asyncio.Task] = {}  # room_id -> timer task
        self._lobby_browsers: dict[int, WebSocket] = {}  # socket_id -> socket for lobby browsers

    async def handle_lobby_connection(self, socket: WebSocket, room_id: UUID) -> None:
        """Handle WebSocket connection to game lobby.

        Args:
            socket: The WebSocket connection.
            room_id: The room ID from URL.
        """
        await self._handle_connection(socket, room_id, is_game=False)

    async def handle_game_connection(self, socket: WebSocket, room_id: UUID) -> None:
        """Handle WebSocket connection to active game.

        Args:
            socket: The WebSocket connection.
            room_id: The room ID from URL.
        """
        await self._handle_connection(socket, room_id, is_game=True)

    async def handle_lobbies_connection(self, socket: WebSocket) -> None:
        """Handle WebSocket connection for browsing open lobbies.

        Clients receive live updates when rooms are created, updated, or start games.

        Args:
            socket: The WebSocket connection.
        """
        await socket.accept()
        socket_id = id(socket)
        self._lobby_browsers[socket_id] = socket

        logger.info("Lobby browser connected", socket_id=socket_id)

        try:
            # Send current list of open public lobbies
            from scribbl_py.game.models import GameState

            open_lobbies = [
                self._serialize_lobby(room)
                for room in self._service._rooms.values()
                if room.game_state == GameState.LOBBY and room.settings.is_public
            ]

            await self._send(
                socket,
                {
                    "type": "lobby_list",
                    "lobbies": open_lobbies,
                },
            )

            # Keep connection alive, listening for potential future messages
            while True:
                try:
                    # Just keep the connection open - we primarily broadcast to it
                    data = await socket.receive_json()
                    # Could handle ping/pong here if needed
                except Exception:
                    break

        except Exception as e:
            logger.error("Error in lobby browser connection", error=str(e))
        finally:
            self._lobby_browsers.pop(socket_id, None)
            logger.info("Lobby browser disconnected", socket_id=socket_id)

    async def _broadcast_to_lobby_browsers(self, message: dict[str, Any]) -> None:
        """Broadcast a message to all lobby browser connections.

        Args:
            message: The message to broadcast.
        """
        disconnected = []
        for socket_id, socket in self._lobby_browsers.items():
            try:
                await self._send(socket, message)
            except Exception:
                disconnected.append(socket_id)

        # Clean up disconnected sockets
        for socket_id in disconnected:
            self._lobby_browsers.pop(socket_id, None)

    def _serialize_lobby(self, room: Any) -> dict[str, Any]:
        """Serialize a room for lobby browser display.

        Args:
            room: The game room.

        Returns:
            Serialized lobby data.
        """
        return {
            "id": str(room.id),
            "name": room.name,
            "code": room.room_code,
            "player_count": len(room.active_players()),
            "max_players": room.settings.max_players,
            "is_public": room.settings.is_public,
        }

    async def _handle_connection(
        self,
        socket: WebSocket,
        room_id: UUID,
        *,
        is_game: bool,
    ) -> None:
        """Handle a WebSocket connection.

        Args:
            socket: The WebSocket connection.
            room_id: The room ID.
            is_game: Whether this is a game (vs lobby) connection.
        """
        # Verify room exists
        try:
            self._service.get_room(room_id)
        except GameNotFoundError:
            await socket.close(code=4004, reason="Room not found")
            return

        await socket.accept()
        socket_id = id(socket)

        logger.debug(
            "WebSocket connection accepted",
            room_id=str(room_id),
            socket_id=socket_id,
            is_game=is_game,
        )

        try:
            await self._receive_loop(socket, room_id)
        except Exception:
            logger.exception("WebSocket error", room_id=str(room_id))
        finally:
            await self._handle_disconnect(socket)

    async def _receive_loop(self, socket: WebSocket, room_id: UUID) -> None:
        """Main receive loop for WebSocket messages.

        Args:
            socket: The WebSocket connection.
            room_id: The room ID.
        """
        socket_id = id(socket)

        async for message in socket.iter_data():
            try:
                data = json.loads(message) if isinstance(message, str) else message
            except json.JSONDecodeError:
                await self._send_error(socket, "invalid_json", "Invalid JSON message")
                continue

            msg_type = data.get("type")
            if not msg_type:
                await self._send_error(socket, "missing_type", "Message type required")
                continue

            try:
                await self._handle_message(socket, socket_id, room_id, data)
            except Exception:
                logger.exception(
                    "Error handling message",
                    message_type=msg_type,
                    room_id=str(room_id),
                )
                await self._send_error(socket, "internal_error", "Internal server error")

    async def _handle_message(
        self,
        socket: WebSocket,
        socket_id: int,
        room_id: UUID,
        data: dict[str, Any],
    ) -> None:
        """Route message to appropriate handler.

        Args:
            socket: The WebSocket connection.
            socket_id: Socket identifier.
            room_id: The room ID.
            data: The message data.
        """
        msg_type = data.get("type")

        handlers = {
            GameMessageType.JOIN: self._handle_join,
            GameMessageType.LEAVE: self._handle_leave,
            GameMessageType.START_GAME: self._handle_start_game,
            GameMessageType.SELECT_WORD: self._handle_select_word,
            GameMessageType.GUESS: self._handle_guess,
            GameMessageType.CHAT: self._handle_chat,
            GameMessageType.DRAW: self._handle_draw,
            GameMessageType.DRAW_SHAPE: self._handle_draw_shape,
            GameMessageType.FILL: self._handle_fill,
            GameMessageType.CLEAR: self._handle_clear,
            GameMessageType.KICK_PLAYER: self._handle_kick_player,
            GameMessageType.BAN_PLAYER: self._handle_ban_player,
            GameMessageType.TRANSFER_HOST: self._handle_transfer_host,
        }

        handler = handlers.get(msg_type)
        if handler:
            await handler(socket, socket_id, room_id, data)
        else:
            await self._send_error(socket, "unknown_type", f"Unknown message type: {msg_type}")

    async def _handle_join(
        self,
        socket: WebSocket,
        socket_id: int,
        room_id: UUID,
        data: dict[str, Any],
    ) -> None:
        """Handle player join message.

        Args:
            socket: The WebSocket connection.
            socket_id: Socket identifier.
            room_id: The room ID.
            data: Message data with user_id and user_name.
        """
        user_id = data.get("user_id", "")
        user_name = data.get("user_name", "Anonymous")

        try:
            player = self._service.join_room(room_id, user_id, user_name)
        except (GameNotFoundError, GameStateError) as e:
            await self._send_error(socket, "join_failed", str(e))
            return

        # Store connection
        connection = GameConnection(
            socket=socket,
            room_id=room_id,
            player_id=player.id,
            user_id=user_id,
            user_name=user_name,
        )
        self._connections[socket_id] = connection

        # Track socket in room
        if room_id not in self._room_sockets:
            self._room_sockets[room_id] = set()
        self._room_sockets[room_id].add(socket_id)

        # Track telemetry
        telemetry = get_telemetry()
        telemetry.track_connection_opened("websocket")
        telemetry.track_player_joined(room_id, player.id, is_spectator=False)

        logger.info(
            "Player joined room via WebSocket",
            room_id=str(room_id),
            player_id=str(player.id),
            user_name=user_name,
            socket_id=socket_id,
            total_sockets=len(self._room_sockets[room_id]),
        )

        room = self._service.get_room(room_id)

        # Send room state to joining player
        await self._send(
            socket,
            {
                "type": GameMessageType.ROOM_STATE,
                "room": self._serialize_room(room),
                "player_id": str(player.id),
            },
        )

        # If game is in WORD_SELECTION and this player is the drawer, resend word options
        # This handles the case where drawer redirected from lobby to game page
        from scribbl_py.game.models import GameState

        if (
            room.game_state == GameState.WORD_SELECTION
            and room.current_round
            and room.current_round.drawer_id == player.id
            and room.current_round.word_options
        ):
            logger.info(
                "Resending word options to drawer after reconnect",
                room_id=str(room_id),
                player_id=str(player.id),
            )
            await self._send(
                socket,
                {
                    "type": GameMessageType.WORD_OPTIONS,
                    "options": room.current_round.word_options,
                },
            )

        # If game is in DRAWING state, send stroke history to rejoining player
        if room.game_state == GameState.DRAWING and room.current_round:
            logger.info(
                "Sending stroke history to rejoining player",
                room_id=str(room_id),
                player_id=str(player.id),
                stroke_count=len(room.current_round.strokes),
            )

            # Send word hint
            await self._send(
                socket,
                {
                    "type": GameMessageType.WORD_SELECTED,
                    "word_hint": room.current_round.word_hint,
                    "word_length": len(room.current_round.word),
                },
            )

            # Send all strokes for canvas replay
            for stroke in room.current_round.strokes:
                await self._send(socket, stroke)

        # Broadcast join to other players
        await self._broadcast_to_room(
            room_id,
            {
                "type": GameMessageType.PLAYER_JOINED,
                "player": self._serialize_player(player),
                "player_count": len(room.active_players()),
            },
            exclude_socket=socket_id,
        )

        # Notify lobby browsers about player count change (only for public lobby rooms)
        if room.game_state == GameState.LOBBY and room.settings.is_public:
            await self._broadcast_to_lobby_browsers(
                {
                    "type": "room_updated",
                    "room": self._serialize_lobby(room),
                }
            )

    async def _handle_leave(
        self,
        socket: WebSocket,
        socket_id: int,
        room_id: UUID,
        data: dict[str, Any],
    ) -> None:
        """Handle player leave message."""
        connection = self._connections.get(socket_id)
        if not connection:
            return

        player_id = connection.player_id
        user_name = connection.user_name

        self._service.leave_room(room_id, player_id)

        # Broadcast leave
        await self._broadcast_to_room(
            room_id,
            {
                "type": GameMessageType.PLAYER_LEFT,
                "player_id": str(player_id),
                "player_name": user_name,
            },
            exclude_socket=socket_id,
        )

    async def _handle_start_game(
        self,
        socket: WebSocket,
        socket_id: int,
        room_id: UUID,
        data: dict[str, Any],
    ) -> None:
        """Handle start game request from host."""
        connection = self._connections.get(socket_id)
        if not connection:
            await self._send_error(socket, "not_connected", "Not connected to room")
            return

        logger.info(
            "Start game requested",
            room_id=str(room_id),
            player_id=str(connection.player_id),
            sockets_in_room=len(self._room_sockets.get(room_id, set())),
        )

        try:
            first_round = self._service.start_game(room_id, connection.player_id)
        except GameStateError as e:
            logger.warning("Start game failed", error=str(e))
            await self._send_error(socket, "start_failed", str(e))
            return
        except Exception as e:
            # Handle InsufficientWordsError and other exceptions
            error_msg = str(e)
            if "words" in error_msg.lower() and "available" in error_msg.lower():
                error_msg = "Not enough words! Add at least 3 custom words when using 'Custom Words Only' mode."
            logger.warning("Start game failed", error=str(e))
            await self._send_error(socket, "start_failed", error_msg)
            return

        room = self._service.get_room(room_id)

        logger.info(
            "Broadcasting game_started",
            room_id=str(room_id),
            socket_ids=list(self._room_sockets.get(room_id, set())),
        )

        # Track telemetry
        telemetry = get_telemetry()
        telemetry.track_game_started(room_id, len(room.active_players()))

        # Broadcast game started
        await self._broadcast_to_room(
            room_id,
            {
                "type": GameMessageType.GAME_STARTED,
                "total_rounds": room.settings.rounds_per_game,
            },
        )

        # Notify lobby browsers that this room is no longer in lobby (only for public rooms)
        if room.settings.is_public:
            await self._broadcast_to_lobby_browsers(
                {
                    "type": "game_started",
                    "room_id": str(room_id),
                }
            )

        # Send round started
        await self._broadcast_round_started(room_id, first_round, room)

    async def _handle_select_word(
        self,
        socket: WebSocket,
        socket_id: int,
        room_id: UUID,
        data: dict[str, Any],
    ) -> None:
        """Handle word selection from drawer."""
        connection = self._connections.get(socket_id)
        if not connection:
            return

        word = data.get("word", "")
        if not word:
            await self._send_error(socket, "invalid_word", "Word is required")
            return

        try:
            current_round = self._service.select_word(room_id, connection.player_id, word)
        except (GameNotFoundError, GameStateError) as e:
            await self._send_error(socket, "select_failed", str(e))
            return

        # Broadcast word selected
        room = self._service.get_room(room_id)
        message = {
            "type": GameMessageType.WORD_SELECTED,
            "word_hint": current_round.word_hint,
            "word_length": len(current_round.word),
        }
        # Include actual word for debug mode
        if room.metadata.get("debug_mode"):
            message["debug_word"] = current_round.word

        await self._broadcast_to_room(room_id, message)

        # Start round timer
        await self._start_round_timer(room_id, current_round.duration_seconds)

        # Schedule bot auto-guesses if in debug mode
        if room.metadata.get("debug_mode"):
            asyncio.create_task(self._schedule_bot_guesses(room_id, current_round.word, current_round.drawer_id))

    async def _handle_guess(
        self,
        socket: WebSocket,
        socket_id: int,
        room_id: UUID,
        data: dict[str, Any],
    ) -> None:
        """Handle guess submission from player."""
        connection = self._connections.get(socket_id)
        if not connection:
            return

        guess_text = data.get("text", "").strip()
        if not guess_text:
            return

        # Filter guess for hate speech
        _, was_blocked = filter_message(guess_text)
        if was_blocked:
            logger.warning(
                "Guess blocked (hate speech)",
                room_id=str(room_id),
                player_id=str(connection.player_id),
            )
            await self._send(
                socket,
                {
                    "type": GameMessageType.CHAT_MESSAGE,
                    "player_id": "system",
                    "player_name": "System",
                    "message": "Your message was blocked - hate speech is not allowed.",
                    "is_system": True,
                },
            )
            return

        try:
            guess, _chat_msg = self._service.submit_guess(
                room_id,
                connection.player_id,
                guess_text,
            )
        except (GameNotFoundError, GameStateError, PlayerNotFoundError) as e:
            await self._send_error(socket, "guess_failed", str(e))
            return

        room = self._service.get_room(room_id)

        # Track telemetry
        telemetry = get_telemetry()
        telemetry.track_guess(
            room_id,
            connection.player_id,
            correct=guess.result == GuessResult.CORRECT,
            time_ms=guess.guess_time_ms,
        )

        # Handle different guess results
        if guess.result == GuessResult.CORRECT:
            # Broadcast correct guess
            await self._broadcast_to_room(
                room_id,
                {
                    "type": GameMessageType.CORRECT_GUESS,
                    "player_id": str(connection.player_id),
                    "player_name": connection.user_name,
                    "points": guess.points_awarded,
                },
            )

            # Update scores
            await self._broadcast_to_room(
                room_id,
                {
                    "type": GameMessageType.SCORE_UPDATE,
                    "scores": [{"player_id": str(p.id), "score": p.score} for p in room.active_players()],
                },
            )

            # Check if all have guessed
            active = room.active_players()
            guessers = [p for p in active if p.id != room.current_round.drawer_id]
            all_guessed = all(p.has_guessed for p in guessers)

            if all_guessed:
                await self._end_round(room_id)

        elif guess.result == GuessResult.CLOSE:
            # Broadcast the guess as chat to everyone (they just see it as a wrong guess)
            await self._broadcast_to_room(
                room_id,
                {
                    "type": GameMessageType.CHAT_MESSAGE,
                    "player_id": str(connection.player_id),
                    "player_name": connection.user_name,
                    "message": guess_text,
                    "is_correct": False,
                },
            )
            # Send close hint only to guesser (private feedback)
            await self._send(
                socket,
                {
                    "type": GameMessageType.GUESS_RESULT,
                    "result": "close",
                    "message": "You're close!",
                },
            )
        else:
            # Broadcast regular guess as chat
            await self._broadcast_to_room(
                room_id,
                {
                    "type": GameMessageType.CHAT_MESSAGE,
                    "player_id": str(connection.player_id),
                    "player_name": connection.user_name,
                    "message": guess_text,
                    "is_correct": False,
                },
            )

    async def _handle_chat(
        self,
        socket: WebSocket,
        socket_id: int,
        room_id: UUID,
        data: dict[str, Any],
    ) -> None:
        """Handle regular chat message (non-guess)."""
        connection = self._connections.get(socket_id)
        if not connection:
            return

        message = data.get("message", "").strip()
        if not message:
            return

        # Filter message for hate speech
        filtered_message, was_blocked = filter_message(message)
        if was_blocked:
            logger.warning(
                "Chat message blocked (hate speech)",
                room_id=str(room_id),
                player_id=str(connection.player_id),
            )
            # Send warning only to the sender
            await self._send(
                socket,
                {
                    "type": GameMessageType.CHAT_MESSAGE,
                    "player_id": "system",
                    "player_name": "System",
                    "message": "Your message was blocked - hate speech is not allowed.",
                    "is_system": True,
                },
            )
            return

        await self._broadcast_to_room(
            room_id,
            {
                "type": GameMessageType.CHAT_MESSAGE,
                "player_id": str(connection.player_id),
                "player_name": connection.user_name,
                "message": filtered_message,
                "is_system": False,
            },
        )

    async def _handle_draw(
        self,
        socket: WebSocket,
        socket_id: int,
        room_id: UUID,
        data: dict[str, Any],
    ) -> None:
        """Handle drawing stroke from drawer."""
        connection = self._connections.get(socket_id)
        if not connection:
            return

        room = self._service.get_room(room_id)

        # Only drawer can draw
        if not room.current_round or room.current_round.drawer_id != connection.player_id:
            return

        # Build stroke data
        stroke_data = {
            "type": GameMessageType.DRAW_STROKE,
            "color": data.get("color", "#000000"),
            "width": data.get("width", 4),
            "from_x": data.get("from_x", 0),
            "from_y": data.get("from_y", 0),
            "to_x": data.get("to_x", 0),
            "to_y": data.get("to_y", 0),
        }

        # Store stroke for replay when players rejoin
        room.current_round.add_stroke(stroke_data)

        # Broadcast stroke to other players
        await self._broadcast_to_room(
            room_id,
            stroke_data,
            exclude_socket=socket_id,
        )

    async def _handle_draw_shape(
        self,
        socket: WebSocket,
        socket_id: int,
        room_id: UUID,
        data: dict[str, Any],
    ) -> None:
        """Handle shape drawing from drawer."""
        connection = self._connections.get(socket_id)
        if not connection:
            return

        room = self._service.get_room(room_id)

        # Only drawer can draw
        if not room.current_round or room.current_round.drawer_id != connection.player_id:
            return

        # Build shape data
        shape_data = {
            "type": GameMessageType.DRAW_SHAPE,
            "shape": data.get("shape", "line"),
            "color": data.get("color", "#000000"),
            "width": data.get("width", 4),
            "from_x": data.get("from_x", 0),
            "from_y": data.get("from_y", 0),
            "to_x": data.get("to_x", 0),
            "to_y": data.get("to_y", 0),
        }

        # Store shape for replay when players rejoin
        room.current_round.add_stroke(shape_data)

        # Broadcast shape to other players
        await self._broadcast_to_room(
            room_id,
            shape_data,
            exclude_socket=socket_id,
        )

    async def _handle_fill(
        self,
        socket: WebSocket,
        socket_id: int,
        room_id: UUID,
        data: dict[str, Any],
    ) -> None:
        """Handle fill tool from drawer."""
        connection = self._connections.get(socket_id)
        if not connection:
            return

        room = self._service.get_room(room_id)

        # Only drawer can fill
        if not room.current_round or room.current_round.drawer_id != connection.player_id:
            return

        # Build fill data
        fill_data = {
            "type": GameMessageType.FILL,
            "color": data.get("color", "#000000"),
            "x": data.get("x", 0),
            "y": data.get("y", 0),
        }

        # Store fill for replay when players rejoin
        room.current_round.add_stroke(fill_data)

        # Broadcast fill to other players
        await self._broadcast_to_room(
            room_id,
            fill_data,
            exclude_socket=socket_id,
        )

    async def _handle_clear(
        self,
        socket: WebSocket,
        socket_id: int,
        room_id: UUID,
        data: dict[str, Any],
    ) -> None:
        """Handle canvas clear from drawer."""
        connection = self._connections.get(socket_id)
        if not connection:
            return

        room = self._service.get_room(room_id)

        # Only drawer can clear
        if not room.current_round or room.current_round.drawer_id != connection.player_id:
            return

        # Clear stored strokes
        room.current_round.clear_strokes()

        await self._broadcast_to_room(
            room_id,
            {"type": GameMessageType.CLEAR_CANVAS},
            exclude_socket=socket_id,
        )

    async def _handle_kick_player(
        self,
        socket: WebSocket,
        socket_id: int,
        room_id: UUID,
        data: dict[str, Any],
    ) -> None:
        """Handle kick player request (host only).

        Args:
            socket: The WebSocket connection.
            socket_id: Socket identifier.
            room_id: The room ID.
            data: Message data with target_player_id.
        """
        connection = self._connections.get(socket_id)
        if not connection:
            return

        target_player_id = data.get("target_player_id")
        if not target_player_id:
            await self._send_error(socket, "kick_failed", "No target player specified")
            return

        try:
            target_id = UUID(target_player_id)
            room = self._service.get_room(room_id)
            target = room.kick_player(connection.player_id, target_id)

            if target:
                # Notify the kicked player
                target_socket_id = self._find_socket_by_player(room_id, target_id)
                if target_socket_id:
                    target_conn = self._connections.get(target_socket_id)
                    if target_conn:
                        await target_conn.socket.send_json(
                            {
                                "type": GameMessageType.YOU_WERE_KICKED,
                                "message": "You have been kicked from the room",
                            }
                        )
                        # Close their connection
                        await target_conn.socket.close()

                # Broadcast to room
                await self._broadcast_to_room(
                    room_id,
                    {
                        "type": GameMessageType.PLAYER_KICKED,
                        "player_id": str(target_id),
                        "player_name": target.user_name,
                    },
                )

                logger.info(
                    "Player kicked",
                    room_id=str(room_id),
                    kicked_player=target.user_name,
                    kicked_by=connection.user_name,
                )
        except ValueError as e:
            await self._send_error(socket, "kick_failed", str(e))

    async def _handle_ban_player(
        self,
        socket: WebSocket,
        socket_id: int,
        room_id: UUID,
        data: dict[str, Any],
    ) -> None:
        """Handle ban player request (host only).

        Args:
            socket: The WebSocket connection.
            socket_id: Socket identifier.
            room_id: The room ID.
            data: Message data with target_player_id.
        """
        connection = self._connections.get(socket_id)
        if not connection:
            return

        target_player_id = data.get("target_player_id")
        if not target_player_id:
            await self._send_error(socket, "ban_failed", "No target player specified")
            return

        try:
            target_id = UUID(target_player_id)
            room = self._service.get_room(room_id)
            target = room.ban_player(connection.player_id, target_id)

            if target:
                # Notify the banned player
                target_socket_id = self._find_socket_by_player(room_id, target_id)
                if target_socket_id:
                    target_conn = self._connections.get(target_socket_id)
                    if target_conn:
                        await target_conn.socket.send_json(
                            {
                                "type": GameMessageType.YOU_WERE_BANNED,
                                "message": "You have been banned from this room",
                            }
                        )
                        # Close their connection
                        await target_conn.socket.close()

                # Broadcast to room
                await self._broadcast_to_room(
                    room_id,
                    {
                        "type": GameMessageType.PLAYER_BANNED,
                        "player_id": str(target_id),
                        "player_name": target.user_name,
                    },
                )

                logger.info(
                    "Player banned",
                    room_id=str(room_id),
                    banned_player=target.user_name,
                    banned_by=connection.user_name,
                )
        except ValueError as e:
            await self._send_error(socket, "ban_failed", str(e))

    async def _handle_transfer_host(
        self,
        socket: WebSocket,
        socket_id: int,
        room_id: UUID,
        data: dict[str, Any],
    ) -> None:
        """Handle transfer host request (host only).

        Args:
            socket: The WebSocket connection.
            socket_id: Socket identifier.
            room_id: The room ID.
            data: Message data with new_host_player_id.
        """
        connection = self._connections.get(socket_id)
        if not connection:
            return

        new_host_player_id = data.get("new_host_player_id")
        if not new_host_player_id:
            await self._send_error(socket, "transfer_failed", "No new host specified")
            return

        try:
            new_host_id = UUID(new_host_player_id)
            room = self._service.get_room(room_id)
            success = room.transfer_host(connection.player_id, new_host_id)

            if success:
                new_host = room.get_player(new_host_id)
                # Broadcast to room
                await self._broadcast_to_room(
                    room_id,
                    {
                        "type": GameMessageType.HOST_TRANSFERRED,
                        "new_host_id": str(new_host_id),
                        "new_host_name": new_host.user_name if new_host else "Unknown",
                    },
                )

                logger.info(
                    "Host transferred",
                    room_id=str(room_id),
                    new_host=new_host.user_name if new_host else "Unknown",
                    previous_host=connection.user_name,
                )
        except ValueError as e:
            await self._send_error(socket, "transfer_failed", str(e))

    def _find_socket_by_player(self, room_id: UUID, player_id: UUID) -> int | None:
        """Find socket ID for a player in a room.

        Args:
            room_id: The room ID.
            player_id: The player ID.

        Returns:
            Socket ID if found, None otherwise.
        """
        room_sockets = self._room_sockets.get(room_id, set())
        for socket_id in room_sockets:
            conn = self._connections.get(socket_id)
            if conn and conn.player_id == player_id:
                return socket_id
        return None

    async def _handle_disconnect(self, socket: WebSocket) -> None:
        """Handle WebSocket disconnection.

        Args:
            socket: The disconnected socket.
        """
        socket_id = id(socket)
        connection = self._connections.pop(socket_id, None)

        if connection:
            room_id = connection.room_id
            player_id = connection.player_id
            user_name = connection.user_name

            # Remove from room sockets
            if room_id in self._room_sockets:
                self._room_sockets[room_id].discard(socket_id)

            # Mark player as disconnected (don't remove immediately)
            try:
                room = self._service.get_room(room_id)
                player = room.get_player(player_id)
                if player:
                    player.connection_state = PlayerState.DISCONNECTED

                    # Broadcast disconnect
                    await self._broadcast_to_room(
                        room_id,
                        {
                            "type": GameMessageType.PLAYER_LEFT,
                            "player_id": str(player_id),
                            "player_name": user_name,
                            "disconnected": True,
                        },
                    )
            except Exception:
                pass

            # Track telemetry
            telemetry = get_telemetry()
            telemetry.track_connection_closed("websocket")
            is_spectator = player.is_spectator if player else False
            telemetry.track_player_left(room_id, player_id, is_spectator=is_spectator)

            logger.debug(
                "Player disconnected",
                room_id=str(room_id),
                player_id=str(player_id),
            )

    # Timer Management

    async def _start_round_timer(self, room_id: UUID, duration: int) -> None:
        """Start the round countdown timer.

        Args:
            room_id: The room ID.
            duration: Duration in seconds.
        """
        # Cancel existing timer
        if room_id in self._timer_tasks:
            self._timer_tasks[room_id].cancel()

        # Create new timer task
        task = asyncio.create_task(self._run_timer(room_id, duration))
        self._timer_tasks[room_id] = task

    async def _run_timer(self, room_id: UUID, duration: int) -> None:
        """Run the round timer, broadcasting updates.

        Args:
            room_id: The room ID.
            duration: Total duration.
        """
        remaining = duration
        hint_times = [20, 40, 60]  # Seconds when to reveal hints

        try:
            while remaining > 0:
                await asyncio.sleep(1)
                remaining -= 1

                # Broadcast timer update
                await self._broadcast_to_room(
                    room_id,
                    {
                        "type": GameMessageType.TIMER_UPDATE,
                        "time_left": remaining,
                    },
                )

                # Check for hint reveal
                elapsed = duration - remaining
                if elapsed in hint_times:
                    hint = self._service.reveal_hint(room_id)
                    if hint:
                        await self._broadcast_to_room(
                            room_id,
                            {
                                "type": GameMessageType.HINT_UPDATE,
                                "hint": hint,
                            },
                        )

            # Time's up - end round
            await self._end_round(room_id)

        except asyncio.CancelledError:
            pass

    async def _bot_select_word(
        self,
        room_id: UUID,
        drawer_id: UUID,
        word_options: list[str],
    ) -> None:
        """Auto-select a word for a bot drawer.

        Args:
            room_id: The room ID.
            drawer_id: The bot drawer's player ID.
            word_options: Available word options.
        """
        try:
            # Wait a short delay to simulate thinking
            await asyncio.sleep(1.0 + random.random())

            # Select a random word from options
            word = random.choice(word_options)

            # Select the word via service
            current_round = self._service.select_word(room_id, drawer_id, word)

            # Broadcast word selected (include debug_word for debug mode)
            room = self._service.get_room(room_id)
            message = {
                "type": GameMessageType.WORD_SELECTED,
                "word_hint": current_round.word_hint,
                "word_length": len(current_round.word),
            }
            if room.metadata.get("debug_mode"):
                message["debug_word"] = current_round.word

            await self._broadcast_to_room(room_id, message)

            # Start round timer
            await self._start_round_timer(room_id, current_round.duration_seconds)

            # Schedule bot guesses (excluding the drawer bot)
            room = self._service.get_room(room_id)
            if room.metadata.get("debug_mode"):
                asyncio.create_task(self._schedule_bot_guesses(room_id, current_round.word, drawer_id))

            logger.debug(
                "Bot drawer selected word",
                room_id=str(room_id),
                drawer_id=str(drawer_id),
                word=word,
            )
        except Exception as e:
            logger.debug("Bot word selection failed", error=str(e))

    async def _schedule_bot_guesses(self, room_id: UUID, word: str, drawer_id: UUID | None = None) -> None:
        """Schedule automatic guesses from bot players in debug mode.

        Bots will guess the correct word after random delays to simulate
        real player behavior. Also sends chat messages before guessing.

        Args:
            room_id: The room ID.
            word: The correct word to guess.
            drawer_id: The drawer's ID (to exclude from guessing).
        """
        try:
            room = self._service.get_room(room_id)
            debug_bots = room.metadata.get("debug_bots", [])

            if not debug_bots:
                return

            # Filter out the drawer from guessing bots
            guessing_bots = [bot_id for bot_id in debug_bots if drawer_id is None or bot_id != str(drawer_id)]

            # Schedule bot chat and guesses
            for i, bot_id_str in enumerate(guessing_bots):
                # Stagger bot guesses: first bot after 2-3s, second after 4-5s
                delay = 2 + i * 2 + random.random()
                asyncio.create_task(self._bot_guess_after_delay(room_id, UUID(bot_id_str), word, delay))
        except Exception as e:
            logger.debug("Error scheduling bot guesses", error=str(e))

    async def _bot_guess_after_delay(
        self,
        room_id: UUID,
        player_id: UUID,
        word: str,
        delay: float,
    ) -> None:
        """Make a bot player guess the word after a delay.

        Bots will send chat messages before guessing to simulate real players.

        Args:
            room_id: The room ID.
            player_id: The bot player's ID.
            word: The word to guess.
            delay: Seconds to wait before guessing.
        """
        # Chat messages bots might send before guessing
        thinking_messages = [
            "hmm...",
            "I think I know!",
            "is it a...",
            "wait...",
            "oh!",
            "let me think...",
            "🤔",
        ]

        wrong_guesses = [
            "banana",
            "house",
            "tree",
            "dog",
            "cat",
            "sun",
            "star",
        ]

        try:
            # Send a "thinking" chat message first
            await asyncio.sleep(delay * 0.3)

            room = self._service.get_room(room_id)
            if not room.current_round or not room.current_round.is_active:
                return

            player = room.get_player(player_id)
            if not player or player.has_guessed:
                return

            # Send thinking message
            thinking_msg = random.choice(thinking_messages)
            await self._broadcast_to_room(
                room_id,
                {
                    "type": GameMessageType.CHAT_MESSAGE,
                    "player_id": str(player_id),
                    "player_name": player.user_name,
                    "message": thinking_msg,
                    "is_guess": False,
                },
            )

            # Maybe send a wrong guess first
            if random.random() < 0.4:
                await asyncio.sleep(0.5 + random.random())
                wrong = random.choice(wrong_guesses)
                await self._broadcast_to_room(
                    room_id,
                    {
                        "type": GameMessageType.CHAT_MESSAGE,
                        "player_id": str(player_id),
                        "player_name": player.user_name,
                        "message": wrong,
                        "is_guess": True,
                    },
                )

            # Wait remaining time then guess correctly
            await asyncio.sleep(delay * 0.7)

            # Check if round is still active
            room = self._service.get_room(room_id)
            if not room.current_round or not room.current_round.is_active:
                return

            # Check if this player already guessed
            player = room.get_player(player_id)
            if not player or player.has_guessed:
                return

            # Submit the correct guess
            guess, _chat_msg = self._service.submit_guess(room_id, player_id, word)

            if guess.result == GuessResult.CORRECT:
                # Broadcast correct guess
                await self._broadcast_to_room(
                    room_id,
                    {
                        "type": GameMessageType.CORRECT_GUESS,
                        "player_id": str(player_id),
                        "player_name": player.user_name,
                        "points": guess.points_awarded,
                    },
                )

                # Update scores
                await self._broadcast_to_room(
                    room_id,
                    {
                        "type": GameMessageType.SCORE_UPDATE,
                        "scores": [
                            {"player_id": str(p.id), "name": p.user_name, "score": p.score}
                            for p in room.active_players()
                        ],
                    },
                )

                # Check if all guessed - end round early
                guessers = [p for p in room.active_players() if p.id != room.current_round.drawer_id]
                if all(p.has_guessed for p in guessers):
                    await self._end_round(room_id)

                logger.debug(
                    "Bot guessed correctly",
                    room_id=str(room_id),
                    player_id=str(player_id),
                    player_name=player.user_name,
                )
        except Exception as e:
            logger.debug("Bot guess failed", error=str(e))

    async def _end_round(self, room_id: UUID) -> None:
        """End the current round and broadcast results.

        Args:
            room_id: The room ID.
        """
        # Cancel timer
        if room_id in self._timer_tasks:
            self._timer_tasks[room_id].cancel()
            del self._timer_tasks[room_id]

        try:
            results = self._service.end_round(room_id)
        except Exception:
            return

        room = self._service.get_room(room_id)

        # Track telemetry - drawing completed
        telemetry = get_telemetry()
        was_guessed = any(p.has_guessed for p in room.active_players() if p.id != results["drawer_id"])
        telemetry.track_drawing_completed(room_id, results["drawer_id"], was_guessed)

        # Broadcast round end
        await self._broadcast_to_room(
            room_id,
            {
                "type": GameMessageType.ROUND_END,
                "word": results["word"],
                "round": results["round_number"],
                "drawer_id": str(results["drawer_id"]),
                "drawer_name": results["drawer_name"],
                "leaderboard": [
                    {"player_id": str(p.id), "name": p.user_name, "score": score} for p, score in results["leaderboard"]
                ],
            },
        )

        if results["is_game_over"]:
            # Track game ended telemetry
            winner_id = results["leaderboard"][0][0].id if results["leaderboard"] else None
            telemetry.track_game_ended(
                room_id,
                winner_id,
                len(room.active_players()),
                results["round_number"],
            )

            await self._broadcast_to_room(
                room_id,
                {
                    "type": GameMessageType.GAME_OVER,
                    "final_scores": [
                        {"player_id": str(p.id), "name": p.user_name, "score": score}
                        for p, score in results["leaderboard"]
                    ],
                },
            )
        else:
            # Start next round after delay
            await asyncio.sleep(5)
            try:
                next_round = self._service.next_round(room_id)
                room = self._service.get_room(room_id)
                await self._broadcast_round_started(room_id, next_round, room)
            except Exception:
                pass

    async def _broadcast_round_started(
        self,
        room_id: UUID,
        round_obj: Round,
        room: GameRoom,
    ) -> None:
        """Broadcast round started to all players.

        Args:
            room_id: The room ID.
            round_obj: The new round.
            room: The game room.
        """
        drawer = room.get_player(round_obj.drawer_id)
        drawer_name = drawer.user_name if drawer else "Unknown"

        # Track round started telemetry
        telemetry = get_telemetry()
        telemetry.track_round_started(room_id, round_obj.round_number, round_obj.drawer_id)

        # Broadcast round started
        await self._broadcast_to_room(
            room_id,
            {
                "type": GameMessageType.ROUND_STARTED,
                "round_number": round_obj.round_number,
                "total_rounds": room.settings.rounds_per_game,
                "drawer_id": str(round_obj.drawer_id),
                "drawer_name": drawer_name,
                "duration": round_obj.duration_seconds,
            },
        )

        # Check if drawer is a bot (debug mode)
        debug_bots = room.metadata.get("debug_bots", [])
        drawer_is_bot = str(round_obj.drawer_id) in debug_bots

        if drawer_is_bot and round_obj.word_options:
            # Auto-select word for bot drawer after a short delay
            asyncio.create_task(self._bot_select_word(room_id, round_obj.drawer_id, round_obj.word_options))
        else:
            # Send word options only to drawer (human player)
            for socket_id in self._room_sockets.get(room_id, set()):
                conn = self._connections.get(socket_id)
                if conn and conn.player_id == round_obj.drawer_id:
                    await self._send(
                        conn.socket,
                        {
                            "type": GameMessageType.WORD_OPTIONS,
                            "options": round_obj.word_options,
                        },
                    )
                    break

    # Utility Methods

    async def _send(self, socket: WebSocket, data: dict[str, Any]) -> None:
        """Send message to a socket.

        Args:
            socket: The WebSocket.
            data: Data to send.
        """
        try:
            await socket.send_json(data)
        except Exception:
            pass

    async def _send_error(
        self,
        socket: WebSocket,
        code: str,
        message: str,
    ) -> None:
        """Send error message to socket.

        Args:
            socket: The WebSocket.
            code: Error code.
            message: Error message.
        """
        await self._send(
            socket,
            {
                "type": GameMessageType.ERROR,
                "code": code,
                "message": message,
            },
        )

    async def _broadcast_to_room(
        self,
        room_id: UUID,
        data: dict[str, Any],
        exclude_socket: int | None = None,
    ) -> None:
        """Broadcast message to all sockets in a room.

        Args:
            room_id: The room ID.
            data: Data to broadcast.
            exclude_socket: Optional socket ID to exclude.
        """
        socket_ids = self._room_sockets.get(room_id, set())

        for socket_id in socket_ids:
            if socket_id == exclude_socket:
                continue

            conn = self._connections.get(socket_id)
            if conn:
                await self._send(conn.socket, data)

    def _serialize_room(self, room: GameRoom) -> dict[str, Any]:
        """Serialize room for WebSocket message.

        Args:
            room: The game room.

        Returns:
            Serialized room data.
        """
        return {
            "id": str(room.id),
            "code": room.room_code,
            "name": room.name,
            "state": room.game_state.value,
            "host_id": str(room.host_id) if room.host_id else None,
            "players": [self._serialize_player(p) for p in room.active_players()],
            "settings": {
                "round_duration": room.settings.round_duration_seconds,
                "rounds_per_game": room.settings.rounds_per_game,
                "max_players": room.settings.max_players,
            },
            "current_round": room.current_round_number,
            "total_rounds": room.settings.rounds_per_game,
        }

    def _serialize_player(self, player: Player) -> dict[str, Any]:
        """Serialize player for WebSocket message.

        Args:
            player: The player.

        Returns:
            Serialized player data.
        """
        return {
            "id": str(player.id),
            "user_id": player.user_id,
            "name": player.user_name,
            "score": player.score,
            "is_host": player.is_host,
            "has_guessed": player.has_guessed,
        }


def create_game_websocket_handler(
    path: str,
    game_service: GameService,
    connection_manager: ConnectionManager | None = None,
) -> tuple[Router, GameWebSocketHandler]:
    """Create a WebSocket router for game real-time communication.

    Args:
        path: Base path for WebSocket routes.
        game_service: The game service instance.
        connection_manager: Optional connection manager.

    Returns:
        A tuple of (Litestar Router, GameWebSocketHandler instance).
    """
    from litestar import Router, websocket

    handler = GameWebSocketHandler(game_service, connection_manager)

    @websocket(path="/lobby/{room_id:uuid}")
    async def lobby_websocket(socket: WebSocket, room_id: UUID) -> None:
        """WebSocket endpoint for game lobby.

        Args:
            socket: The WebSocket connection.
            room_id: The room ID from the URL.
        """
        await handler.handle_lobby_connection(socket, room_id)

    @websocket(path="/game/{room_id:uuid}")
    async def game_websocket(socket: WebSocket, room_id: UUID) -> None:
        """WebSocket endpoint for active game.

        Args:
            socket: The WebSocket connection.
            room_id: The room ID from the URL.
        """
        await handler.handle_game_connection(socket, room_id)

    @websocket(path="/lobbies")
    async def lobbies_websocket(socket: WebSocket) -> None:
        """WebSocket endpoint for browsing open lobbies.

        Args:
            socket: The WebSocket connection.
        """
        await handler.handle_lobbies_connection(socket)

    router = Router(
        path=path,
        route_handlers=[lobby_websocket, game_websocket, lobbies_websocket],
        tags=["Game WebSocket"],
    )
    return router, handler
