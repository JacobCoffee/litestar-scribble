"""Litestar plugin for scribbl-py integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from litestar.di import Provide
from litestar.plugins import InitPluginProtocol

from scribbl_py.auth.config import OAuthConfig
from scribbl_py.auth.service import AuthService
from scribbl_py.game.wordbank import WordBank
from scribbl_py.realtime.manager import ConnectionManager
from scribbl_py.services.canvas import CanvasService
from scribbl_py.services.export import ExportService
from scribbl_py.services.game import GameService
from scribbl_py.storage.memory import InMemoryStorage
from scribbl_py.web.router import create_router

if TYPE_CHECKING:
    from litestar.config.app import AppConfig

    from scribbl_py.storage.base import StorageProtocol


def _get_template_directory() -> Path:
    """Get the path to the templates directory.

    Returns:
        Path to the templates directory.
    """
    return Path(__file__).parent / "templates"


def _get_static_directory() -> Path:
    """Get the path to the static files directory (frontend/dist).

    Returns:
        Path to the static files directory.
    """
    # Look for frontend/dist relative to project root
    current = Path(__file__).parent
    while current != current.parent:
        frontend_dist = current / "frontend" / "dist"
        if frontend_dist.exists():
            return frontend_dist
        current = current.parent

    # Fallback to a path relative to the package
    return Path(__file__).parent.parent.parent.parent / "frontend" / "dist"


@dataclass
class ScribblConfig:
    """Configuration for the Scribbl plugin.

    This configuration class allows customization of the scribbl-py plugin
    behavior when integrated with a Litestar application.

    Attributes:
        storage: Storage backend to use for canvas persistence. If None,
            InMemoryStorage will be used by default.
        enable_api: Whether to mount the REST API routes. Defaults to True.
        enable_websocket: Whether to enable WebSocket real-time features.
            Defaults to True.
        api_path: Base path for mounting API routes. Defaults to "/api".
        ws_path: Base path for WebSocket routes. Defaults to "/ws".
        dependency_key: Dependency injection key for CanvasService. This key
            is used to access the service in route handlers via DI.
            Defaults to "service".
        connection_manager: Optional pre-configured ConnectionManager for
            WebSocket connections. If None, a new one will be created.

    Example:
        >>> from scribbl_py.storage.memory import InMemoryStorage
        >>> config = ScribblConfig(
        ...     storage=InMemoryStorage(), enable_api=True, api_path="/api/v1", dependency_key="canvas_service"
        ... )
    """

    storage: StorageProtocol | None = None
    enable_api: bool = True
    enable_websocket: bool = True
    enable_ui: bool = False
    api_path: str = "/api"
    ws_path: str = "/ws"
    ui_path: str = "/ui"
    static_path: str = "/static"
    dependency_key: str = "service"
    connection_manager: ConnectionManager | None = field(default=None)


class ScribblPlugin(InitPluginProtocol):
    """Litestar plugin for scribbl-py integration.

    This plugin provides seamless integration of scribbl-py with Litestar
    applications. It automatically configures dependency injection for the
    CanvasService and optionally mounts REST API routes and WebSocket handlers.

    Features:
        - Automatic dependency injection setup for CanvasService
        - Optional REST API routes mounting
        - Optional WebSocket real-time collaboration support
        - Configurable storage backend
        - Thread-safe initialization

    The plugin implements Litestar's InitPluginProtocol, which means it
    participates in the application initialization lifecycle through the
    on_app_init hook.

    Example:
        Basic usage with defaults:

        >>> from litestar import Litestar
        >>> from scribbl_py import ScribblPlugin, ScribblConfig
        >>>
        >>> app = Litestar(
        ...     plugins=[ScribblPlugin(ScribblConfig())],
        ... )

        Custom configuration:

        >>> from scribbl_py import ScribblPlugin, ScribblConfig
        >>> from scribbl_py.storage.memory import InMemoryStorage
        >>>
        >>> config = ScribblConfig(
        ...     storage=InMemoryStorage(), enable_api=True, api_path="/api/canvas", dependency_key="canvas_service"
        ... )
        >>> plugin = ScribblPlugin(config)

        Accessing the service in route handlers:

        >>> from litestar import get
        >>> from scribbl_py.services.canvas import CanvasService
        >>>
        >>> @get("/custom")
        ... async def custom_handler(service: CanvasService) -> dict:
        ...     canvases = await service.list_canvases()
        ...     return {"count": len(canvases)}

    Attributes:
        _config: The plugin configuration.
        _storage: The initialized storage backend (None until on_app_init).
        _service: The initialized CanvasService (None until on_app_init).
        _connection_manager: The WebSocket connection manager (None until on_app_init).
    """

    def __init__(self, config: ScribblConfig | None = None) -> None:
        """Initialize the plugin with optional configuration.

        Args:
            config: Plugin configuration. If None, ScribblConfig with default
                values will be used.
        """
        self._config = config or ScribblConfig()
        self._storage: StorageProtocol | None = None
        self._service: CanvasService | None = None
        self._export_service: ExportService | None = None
        self._game_service: GameService | None = None
        self._connection_manager: ConnectionManager | None = None
        self._game_ws_handler: Any = None
        self._auth_service: AuthService | None = None

    def on_app_init(self, app_config: AppConfig) -> AppConfig:  # noqa: C901, PLR0915
        """Initialize the plugin during application startup.

        This method is called by Litestar during app initialization. It sets up
        the storage backend, creates the CanvasService, registers it with the
        dependency injection system, and optionally mounts API routes and
        WebSocket handlers.

        Args:
            app_config: The Litestar application configuration object.

        Returns:
            The modified application configuration with scribbl-py integration.

        Note:
            This method is called automatically by Litestar and should not be
            invoked manually.
        """
        # Create storage backend (use InMemoryStorage if not provided)
        self._storage = self._config.storage or InMemoryStorage()

        # Create canvas service with the storage backend
        self._service = CanvasService(self._storage)

        # Create export service
        self._export_service = ExportService()

        # Create game service with word bank
        word_bank = WordBank()
        self._game_service = GameService(word_bank=word_bank)

        # Create connection manager for WebSocket
        self._connection_manager = self._config.connection_manager or ConnectionManager()

        # Create auth service
        self._auth_service = AuthService(OAuthConfig())

        # Register service as a dependency provider
        def provide_service() -> CanvasService:
            """Dependency provider for CanvasService.

            Returns:
                The initialized CanvasService instance.
            """
            if self._service is None:
                msg = "Service not initialized"
                raise RuntimeError(msg)
            return self._service

        def provide_connection_manager() -> ConnectionManager:
            """Dependency provider for ConnectionManager.

            Returns:
                The initialized ConnectionManager instance.
            """
            if self._connection_manager is None:
                msg = "Connection manager not initialized"
                raise RuntimeError(msg)
            return self._connection_manager

        def provide_export_service() -> ExportService:
            """Dependency provider for ExportService.

            Returns:
                The initialized ExportService instance.
            """
            if self._export_service is None:
                msg = "Export service not initialized"
                raise RuntimeError(msg)
            return self._export_service

        def provide_game_service() -> GameService:
            """Dependency provider for GameService.

            Returns:
                The initialized GameService instance.
            """
            if self._game_service is None:
                msg = "Game service not initialized"
                raise RuntimeError(msg)
            return self._game_service

        def provide_auth_service() -> AuthService:
            """Dependency provider for AuthService.

            Returns:
                The initialized AuthService instance.
            """
            if self._auth_service is None:
                msg = "Auth service not initialized"
                raise RuntimeError(msg)
            return self._auth_service

        app_config.dependencies[self._config.dependency_key] = Provide(
            provide_service,
            sync_to_thread=False,
        )
        app_config.dependencies["connection_manager"] = Provide(
            provide_connection_manager,
            sync_to_thread=False,
        )
        app_config.dependencies["export_service"] = Provide(
            provide_export_service,
            sync_to_thread=False,
        )
        app_config.dependencies["game_service"] = Provide(
            provide_game_service,
            sync_to_thread=False,
        )
        app_config.dependencies["auth_service"] = Provide(
            provide_auth_service,
            sync_to_thread=False,
        )

        # Mount API routes if enabled
        if self._config.enable_api:
            router = create_router(path=self._config.api_path)
            app_config.route_handlers.append(router)

            # Add game API routes
            from scribbl_py.web.game_controllers import GameRoomController

            app_config.route_handlers.append(GameRoomController)

            # Add auth routes
            from scribbl_py.auth.controller import AuthController

            app_config.route_handlers.append(AuthController)

            # Add stats/telemetry routes
            from scribbl_py.web.stats_controller import StatsController

            app_config.route_handlers.append(StatsController)

        # Mount WebSocket handler if enabled
        if self._config.enable_websocket:
            from scribbl_py.realtime.handler import create_websocket_handler

            ws_handler = create_websocket_handler(
                path=self._config.ws_path,
                connection_manager=self._connection_manager,
                canvas_service=self._service,
            )
            app_config.route_handlers.append(ws_handler)

            # Add game WebSocket handlers
            from scribbl_py.realtime.game_handler import create_game_websocket_handler

            game_ws_router, self._game_ws_handler = create_game_websocket_handler(
                path=f"{self._config.ws_path}/canvas-clash",
                game_service=self._game_service,
                connection_manager=self._connection_manager,
            )
            app_config.route_handlers.append(game_ws_router)

            # Register game WebSocket handler as a dependency
            def provide_game_ws_handler() -> Any:
                """Dependency provider for GameWebSocketHandler."""
                return self._game_ws_handler

            app_config.dependencies["game_ws_handler"] = Provide(
                provide_game_ws_handler,
                sync_to_thread=False,
            )

        # Mount UI routes if enabled
        if self._config.enable_ui:
            from litestar.contrib.jinja import JinjaTemplateEngine
            from litestar.static_files import create_static_files_router
            from litestar.template.config import TemplateConfig

            from scribbl_py.web.game_controllers import GameUIController
            from scribbl_py.web.ui import UIController

            # Configure templates
            template_dir = _get_template_directory()
            if app_config.template_config is None:
                app_config.template_config = TemplateConfig(
                    directory=template_dir,
                    engine=JinjaTemplateEngine,
                )

            # Add UI controllers
            app_config.route_handlers.append(UIController)
            app_config.route_handlers.append(GameUIController)

            # Configure static files
            static_dir = _get_static_directory()
            if static_dir.exists():
                static_router = create_static_files_router(
                    path=self._config.static_path,
                    directories=[static_dir],
                    name="static",
                )
                app_config.route_handlers.append(static_router)

        # Configure session middleware for OAuth state (if API is enabled)
        if self._config.enable_api:
            from litestar.middleware.session.server_side import (
                ServerSideSessionConfig,
            )

            # Use in-memory session storage for OAuth state
            if app_config.middleware is None:
                app_config.middleware = []
            app_config.middleware.append(
                ServerSideSessionConfig(
                    max_age=300,  # 5 minutes for OAuth state
                    session_id_bytes=32,
                ).middleware
            )

        return app_config

    @property
    def storage(self) -> StorageProtocol:
        """Get the initialized storage backend.

        Returns:
            The storage backend instance.

        Raises:
            RuntimeError: If the plugin has not been initialized yet
                (on_app_init not called).

        Example:
            >>> plugin = ScribblPlugin(ScribblConfig())
            >>> # After app initialization
            >>> storage = plugin.storage
        """
        if self._storage is None:
            msg = "Plugin not initialized. Call on_app_init first."
            raise RuntimeError(msg)
        return self._storage

    @property
    def service(self) -> CanvasService:
        """Get the initialized canvas service.

        Returns:
            The CanvasService instance.

        Raises:
            RuntimeError: If the plugin has not been initialized yet
                (on_app_init not called).

        Example:
            >>> plugin = ScribblPlugin(ScribblConfig())
            >>> # After app initialization
            >>> service = plugin.service
            >>> canvases = await service.list_canvases()
        """
        if self._service is None:
            msg = "Plugin not initialized. Call on_app_init first."
            raise RuntimeError(msg)
        return self._service

    @property
    def connection_manager(self) -> ConnectionManager:
        """Get the initialized connection manager.

        Returns:
            The ConnectionManager instance.

        Raises:
            RuntimeError: If the plugin has not been initialized yet
                (on_app_init not called).

        Example:
            >>> plugin = ScribblPlugin(ScribblConfig())
            >>> # After app initialization
            >>> manager = plugin.connection_manager
            >>> active = manager.active_canvases
        """
        if self._connection_manager is None:
            msg = "Plugin not initialized. Call on_app_init first."
            raise RuntimeError(msg)
        return self._connection_manager

    @property
    def auth_service(self) -> AuthService:
        """Get the initialized auth service.

        Returns:
            The AuthService instance.

        Raises:
            RuntimeError: If the plugin has not been initialized yet
                (on_app_init not called).

        Example:
            >>> plugin = ScribblPlugin(ScribblConfig())
            >>> # After app initialization
            >>> auth = plugin.auth_service
            >>> leaderboard = auth.get_leaderboard("wins")
        """
        if self._auth_service is None:
            msg = "Plugin not initialized. Call on_app_init first."
            raise RuntimeError(msg)
        return self._auth_service
