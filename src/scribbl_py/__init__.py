"""Scribbl-py: A Litestar-based API for drawing and whiteboard applications.

This package provides a complete solution for building collaborative drawing
and whiteboard applications using Litestar. It includes domain models, storage
backends, business logic services, REST API controllers, WebSocket real-time
support, and a Litestar plugin for seamless integration.

Key Components:
    - Core Models: Canvas, Element, Stroke, Shape, Text, Point
    - Storage: InMemoryStorage, StorageProtocol (for custom backends)
    - Services: CanvasService (business logic layer)
    - Web: REST API controllers and routers
    - Realtime: WebSocket handlers for real-time collaboration
    - Plugin: ScribblPlugin for Litestar integration

Quick Start:
    >>> from litestar import Litestar
    >>> from scribbl_py import ScribblPlugin, ScribblConfig
    >>>
    >>> app = Litestar(
    ...     plugins=[ScribblPlugin(ScribblConfig())],
    ... )

Advanced Usage:
    >>> from scribbl_py import (
    ...     ScribblPlugin,
    ...     ScribblConfig,
    ...     InMemoryStorage,
    ...     CanvasService,
    ... )
    >>>
    >>> # Custom configuration
    >>> config = ScribblConfig(
    ...     storage=InMemoryStorage(),
    ...     api_path="/api/v1",
    ...     enable_websocket=True,
    ... )
    >>> app = Litestar(plugins=[ScribblPlugin(config)])
"""

from __future__ import annotations

from scribbl_py.auth import (
    AuthController,
    AuthService,
    OAuthConfig,
    OAuthProvider,
    Session,
    User,
    UserStats,
)
from scribbl_py.core import (
    Canvas,
    Element,
    ElementStyle,
    ElementType,
    Point,
    Shape,
    ShapeType,
    Stroke,
    Text,
)
from scribbl_py.exceptions import (
    CanvasNotFoundError,
    ElementNotFoundError,
    InvalidElementError,
    ScribblError,
)
from scribbl_py.plugin import ScribblConfig, ScribblPlugin
from scribbl_py.realtime import (
    CanvasWebSocketHandler,
    ConnectedUser,
    ConnectionManager,
    MessageType,
    create_websocket_handler,
)
from scribbl_py.services import CanvasService
from scribbl_py.storage import InMemoryStorage, StorageProtocol
from scribbl_py.web import CanvasController, ElementController, create_router

__all__ = [
    "AuthController",
    "AuthService",
    "Canvas",
    "CanvasController",
    "CanvasNotFoundError",
    "CanvasService",
    "CanvasWebSocketHandler",
    "ConnectedUser",
    "ConnectionManager",
    "Element",
    "ElementController",
    "ElementNotFoundError",
    "ElementStyle",
    "ElementType",
    "InMemoryStorage",
    "InvalidElementError",
    "MessageType",
    "OAuthConfig",
    "OAuthProvider",
    "Point",
    "ScribblConfig",
    "ScribblError",
    "ScribblPlugin",
    "Session",
    "Shape",
    "ShapeType",
    "StorageProtocol",
    "Stroke",
    "Text",
    "User",
    "UserStats",
    "create_router",
    "create_websocket_handler",
]

__version__ = "0.1.0"
