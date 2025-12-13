"""Real-time WebSocket module for scribbl-py.

This module provides WebSocket functionality for real-time canvas collaboration,
including connection management, element broadcasting, and cursor synchronization.
"""

from __future__ import annotations

from scribbl_py.realtime.handler import CanvasWebSocketHandler, create_websocket_handler
from scribbl_py.realtime.manager import ConnectedUser, ConnectionManager
from scribbl_py.realtime.messages import (
    CursorMoveMessage,
    ElementAddMessage,
    ElementDeleteMessage,
    ElementUpdateMessage,
    ErrorMessage,
    JoinMessage,
    LeaveMessage,
    MessageType,
    SyncMessage,
    WebSocketMessage,
)

__all__ = [
    "CanvasWebSocketHandler",
    "ConnectedUser",
    "ConnectionManager",
    "CursorMoveMessage",
    "ElementAddMessage",
    "ElementDeleteMessage",
    "ElementUpdateMessage",
    "ErrorMessage",
    "JoinMessage",
    "LeaveMessage",
    "MessageType",
    "SyncMessage",
    "WebSocketMessage",
    "create_websocket_handler",
]
