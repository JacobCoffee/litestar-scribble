"""WebSocket message types and schemas for real-time communication."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID


class MessageType(str, Enum):
    """Types of WebSocket messages."""

    # Client -> Server
    JOIN = "join"
    LEAVE = "leave"
    ELEMENT_ADD = "element_add"
    ELEMENT_UPDATE = "element_update"
    ELEMENT_DELETE = "element_delete"
    CURSOR_MOVE = "cursor_move"
    UNDO = "undo"
    REDO = "redo"
    STROKE_START = "stroke_start"
    STROKE_CONTINUE = "stroke_continue"
    STROKE_END = "stroke_end"

    # Server -> Client
    SYNC = "sync"
    USER_JOINED = "user_joined"
    USER_LEFT = "user_left"
    ELEMENT_ADDED = "element_added"
    ELEMENT_UPDATED = "element_updated"
    ELEMENT_DELETED = "element_deleted"
    CURSOR_MOVED = "cursor_moved"
    UNDO_RESULT = "undo_result"
    REDO_RESULT = "redo_result"
    ERROR = "error"
    STROKE_STARTED = "stroke_started"
    STROKE_CONTINUED = "stroke_continued"
    STROKE_ENDED = "stroke_ended"


@dataclass
class WebSocketMessage:
    """Base class for all WebSocket messages."""

    type: MessageType
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Convert message to dictionary for JSON serialization."""
        return {
            "type": self.type.value,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class JoinMessage:
    """Message sent when a user joins a canvas session."""

    canvas_id: UUID
    user_id: str
    user_name: str = "Anonymous"
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": MessageType.JOIN.value,
            "timestamp": self.timestamp.isoformat(),
            "canvas_id": str(self.canvas_id),
            "user_id": self.user_id,
            "user_name": self.user_name,
        }


@dataclass
class LeaveMessage:
    """Message sent when a user leaves a canvas session."""

    canvas_id: UUID
    user_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": MessageType.LEAVE.value,
            "timestamp": self.timestamp.isoformat(),
            "canvas_id": str(self.canvas_id),
            "user_id": self.user_id,
        }


@dataclass
class SyncMessage:
    """Message sent to synchronize canvas state with a client."""

    canvas_id: UUID
    canvas_data: dict[str, Any]
    connected_users: list[dict[str, Any]]
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": MessageType.SYNC.value,
            "timestamp": self.timestamp.isoformat(),
            "canvas_id": str(self.canvas_id),
            "canvas": self.canvas_data,
            "connected_users": self.connected_users,
        }


@dataclass
class ElementAddMessage:
    """Message for adding an element to the canvas."""

    canvas_id: UUID
    user_id: str
    element_type: str
    element_data: dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": MessageType.ELEMENT_ADD.value,
            "timestamp": self.timestamp.isoformat(),
            "canvas_id": str(self.canvas_id),
            "user_id": self.user_id,
            "element_type": self.element_type,
            "element_data": self.element_data,
        }


@dataclass
class ElementUpdateMessage:
    """Message for updating an element on the canvas."""

    canvas_id: UUID
    user_id: str
    element_id: UUID
    updates: dict[str, Any]
    version: int = 1
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": MessageType.ELEMENT_UPDATE.value,
            "timestamp": self.timestamp.isoformat(),
            "canvas_id": str(self.canvas_id),
            "user_id": self.user_id,
            "element_id": str(self.element_id),
            "updates": self.updates,
            "version": self.version,
        }


@dataclass
class ElementDeleteMessage:
    """Message for deleting an element from the canvas."""

    canvas_id: UUID
    user_id: str
    element_id: UUID
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": MessageType.ELEMENT_DELETE.value,
            "timestamp": self.timestamp.isoformat(),
            "canvas_id": str(self.canvas_id),
            "user_id": self.user_id,
            "element_id": str(self.element_id),
        }


@dataclass
class CursorMoveMessage:
    """Message for cursor position updates."""

    canvas_id: UUID
    user_id: str
    x: float
    y: float
    user_name: str = "Anonymous"
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": MessageType.CURSOR_MOVE.value,
            "timestamp": self.timestamp.isoformat(),
            "canvas_id": str(self.canvas_id),
            "user_id": self.user_id,
            "user_name": self.user_name,
            "x": self.x,
            "y": self.y,
        }


@dataclass
class ErrorMessage:
    """Message for error responses."""

    code: str
    message: str
    details: dict[str, Any] | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "type": MessageType.ERROR.value,
            "timestamp": self.timestamp.isoformat(),
            "code": self.code,
            "message": self.message,
        }
        if self.details:
            result["details"] = self.details
        return result


@dataclass
class StrokeStartMessage:
    """Message sent when starting a stroke."""

    canvas_id: UUID
    user_id: str
    stroke_id: str
    point: dict[str, Any]
    style: dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": MessageType.STROKE_START.value,
            "timestamp": self.timestamp.isoformat(),
            "canvas_id": str(self.canvas_id),
            "user_id": self.user_id,
            "stroke_id": self.stroke_id,
            "point": self.point,
            "style": self.style,
        }


@dataclass
class StrokeContinueMessage:
    """Message sent when continuing a stroke."""

    canvas_id: UUID
    user_id: str
    stroke_id: str
    points: list[dict[str, Any]]
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": MessageType.STROKE_CONTINUE.value,
            "timestamp": self.timestamp.isoformat(),
            "canvas_id": str(self.canvas_id),
            "user_id": self.user_id,
            "stroke_id": self.stroke_id,
            "points": self.points,
        }


@dataclass
class StrokeEndMessage:
    """Message sent when ending a stroke."""

    canvas_id: UUID
    user_id: str
    stroke_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": MessageType.STROKE_END.value,
            "timestamp": self.timestamp.isoformat(),
            "canvas_id": str(self.canvas_id),
            "user_id": self.user_id,
            "stroke_id": self.stroke_id,
        }
