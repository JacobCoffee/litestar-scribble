"""Connection manager for WebSocket sessions."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

import structlog

if TYPE_CHECKING:
    from litestar import WebSocket

logger = structlog.get_logger(__name__)


@dataclass
class ConnectedUser:
    """Represents a connected user in a canvas session."""

    user_id: str
    user_name: str
    websocket: WebSocket
    canvas_id: UUID
    cursor_x: float = 0.0
    cursor_y: float = 0.0
    connected_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "user_id": self.user_id,
            "user_name": self.user_name,
            "cursor_x": self.cursor_x,
            "cursor_y": self.cursor_y,
            "connected_at": self.connected_at.isoformat(),
        }


class ConnectionManager:
    """Manages WebSocket connections for canvas sessions.

    This class provides thread-safe connection management for real-time
    canvas collaboration. It tracks connections per canvas and provides
    methods for broadcasting messages to connected clients.
    """

    def __init__(self) -> None:
        """Initialize the connection manager."""
        self._connections: dict[UUID, dict[str, ConnectedUser]] = {}
        self._lock = asyncio.Lock()

    async def connect(
        self,
        websocket: WebSocket,
        canvas_id: UUID,
        user_id: str,
        user_name: str = "Anonymous",
    ) -> ConnectedUser:
        """Register a new WebSocket connection.

        Args:
            websocket: The WebSocket connection.
            canvas_id: The canvas being joined.
            user_id: Unique identifier for the user.
            user_name: Display name for the user.

        Returns:
            The ConnectedUser instance.
        """
        async with self._lock:
            if canvas_id not in self._connections:
                self._connections[canvas_id] = {}

            user = ConnectedUser(
                user_id=user_id,
                user_name=user_name,
                websocket=websocket,
                canvas_id=canvas_id,
            )
            self._connections[canvas_id][user_id] = user

            logger.info(
                "User connected",
                user_id=user_id,
                user_name=user_name,
                canvas_id=str(canvas_id),
                total_users=len(self._connections[canvas_id]),
            )

            return user

    async def disconnect(self, canvas_id: UUID, user_id: str) -> None:
        """Remove a WebSocket connection.

        Args:
            canvas_id: The canvas being left.
            user_id: The user's identifier.
        """
        async with self._lock:
            if canvas_id in self._connections:
                if user_id in self._connections[canvas_id]:
                    del self._connections[canvas_id][user_id]
                    logger.info(
                        "User disconnected",
                        user_id=user_id,
                        canvas_id=str(canvas_id),
                        remaining_users=len(self._connections[canvas_id]),
                    )

                # Clean up empty canvas sessions
                if not self._connections[canvas_id]:
                    del self._connections[canvas_id]
                    logger.info(
                        "Canvas session closed",
                        canvas_id=str(canvas_id),
                    )

    async def get_connected_users(self, canvas_id: UUID) -> list[ConnectedUser]:
        """Get all users connected to a canvas.

        Args:
            canvas_id: The canvas to query.

        Returns:
            List of connected users.
        """
        async with self._lock:
            if canvas_id not in self._connections:
                return []
            return list(self._connections[canvas_id].values())

    async def get_user(self, canvas_id: UUID, user_id: str) -> ConnectedUser | None:
        """Get a specific connected user.

        Args:
            canvas_id: The canvas to query.
            user_id: The user's identifier.

        Returns:
            The ConnectedUser or None if not found.
        """
        async with self._lock:
            if canvas_id not in self._connections:
                return None
            return self._connections[canvas_id].get(user_id)

    async def update_cursor(
        self,
        canvas_id: UUID,
        user_id: str,
        x: float,
        y: float,
    ) -> None:
        """Update a user's cursor position.

        Args:
            canvas_id: The canvas.
            user_id: The user's identifier.
            x: X coordinate.
            y: Y coordinate.
        """
        async with self._lock:
            if canvas_id in self._connections:
                user = self._connections[canvas_id].get(user_id)
                if user:
                    user.cursor_x = x
                    user.cursor_y = y

    async def broadcast(
        self,
        canvas_id: UUID,
        message: dict[str, Any],
        exclude_user: str | None = None,
    ) -> None:
        """Broadcast a message to all users on a canvas.

        Args:
            canvas_id: The canvas to broadcast to.
            message: The message to send.
            exclude_user: Optional user ID to exclude from broadcast.
        """
        users = await self.get_connected_users(canvas_id)
        json_message = json.dumps(message)

        tasks = []
        for user in users:
            if exclude_user and user.user_id == exclude_user:
                continue
            tasks.append(self._send_to_user(user, json_message))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def send_to_user(
        self,
        canvas_id: UUID,
        user_id: str,
        message: dict[str, Any],
    ) -> bool:
        """Send a message to a specific user.

        Args:
            canvas_id: The canvas.
            user_id: The target user.
            message: The message to send.

        Returns:
            True if sent successfully, False otherwise.
        """
        user = await self.get_user(canvas_id, user_id)
        if not user:
            return False

        try:
            await user.websocket.send_json(message)
            return True
        except Exception:
            logger.exception(
                "Failed to send message to user",
                user_id=user_id,
                canvas_id=str(canvas_id),
            )
            return False

    async def _send_to_user(self, user: ConnectedUser, message: str) -> None:
        """Internal method to send a message to a user.

        Args:
            user: The connected user.
            message: The JSON message string.
        """
        try:
            await user.websocket.send_text(message)
        except Exception:
            logger.exception(
                "Failed to send message",
                user_id=user.user_id,
                canvas_id=str(user.canvas_id),
            )

    @property
    def active_canvases(self) -> int:
        """Get the number of active canvas sessions."""
        return len(self._connections)

    @property
    def total_connections(self) -> int:
        """Get the total number of connected users."""
        return sum(len(users) for users in self._connections.values())
