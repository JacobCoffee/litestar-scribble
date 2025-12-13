"""Main Litestar application for scribbl-py.

This module provides the main application factory and configured app instance
for running scribbl-py as a standalone application.
"""

from __future__ import annotations

import mimetypes
import os
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from advanced_alchemy.extensions.litestar import AlembicAsyncConfig, SQLAlchemyPlugin
from advanced_alchemy.extensions.litestar.plugins.init.config.asyncio import SQLAlchemyAsyncConfig
from litestar import Litestar, get
from litestar.openapi import OpenAPIConfig
from litestar.response import Redirect
from litestar_vite import ViteConfig, VitePlugin

from scribbl_py import ScribblConfig, ScribblPlugin
from scribbl_py.cli import ScribblCLIPlugin
from scribbl_py.core.error_handling import get_exception_handlers
from scribbl_py.core.logging import CorrelationIdMiddleware, RequestLoggingMiddleware, configure_logging
from scribbl_py.core.openapi import get_openapi_plugins
from scribbl_py.core.rate_limit import get_rate_limit_middleware
from scribbl_py.web.health import HealthController

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

# Register MIME types for static file serving (Docker slim images may have incomplete mimetypes)
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("image/svg+xml", ".svg")
mimetypes.add_type("application/json", ".json")


@asynccontextmanager
async def lifespan(app: Litestar) -> AsyncGenerator[None, None]:
    """Application lifespan handler for database setup/teardown.

    Initializes the database on startup and closes connections on shutdown.
    """
    db_manager = None

    # Try to initialize database if db extras are installed
    try:
        from scribbl_py.storage.db.setup import DatabaseManager

        db_manager = DatabaseManager()
        await db_manager.init()
        app.state.db_manager = db_manager

        import structlog

        logger = structlog.get_logger(__name__)
        logger.info("Database initialized", url=db_manager.engine.url.render_as_string(hide_password=True))
    except ImportError:
        # Database extras not installed, skip
        pass
    except Exception as e:  # noqa: BLE001
        import structlog

        logger = structlog.get_logger(__name__)
        logger.warning("Failed to initialize database, using in-memory storage", error=str(e))

    yield

    # Cleanup
    if db_manager is not None:
        await db_manager.close()


def get_database_url() -> str:
    """Get the database URL from environment or default to SQLite.

    Returns:
        Database connection URL.
    """
    return os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./scribbl.db")


def _get_frontend_directory() -> str:
    """Get the path to the frontend directory.

    Returns:
        Path to the frontend directory.
    """
    from pathlib import Path

    # Check environment variable first (for custom deployments)
    env_frontend = os.environ.get("SCRIBBL_FRONTEND_DIR")
    if env_frontend:
        return env_frontend

    # Check Docker standard location
    docker_path = Path("/app/frontend")
    if docker_path.exists():
        return str(docker_path)

    # Look for frontend relative to project root
    current = Path(__file__).parent
    while current != current.parent:
        frontend = current / "frontend"
        if frontend.exists():
            return str(frontend)
        current = current.parent

    # Fallback to relative path
    return str(Path(__file__).parent.parent.parent.parent / "frontend")


# SQLAlchemy configuration for database CLI commands
sqlalchemy_config = SQLAlchemyAsyncConfig(
    connection_string=get_database_url(),
    alembic_config=AlembicAsyncConfig(
        script_location="src/scribbl_py/storage/db/migrations",
        version_table_name="alembic_version",
    ),
)

sqlalchemy_plugin = SQLAlchemyPlugin(config=sqlalchemy_config)


def create_app(
    *,
    enable_ui: bool = True,
    enable_api: bool = True,
    enable_websocket: bool = True,
    debug: bool = False,
    json_logs: bool = False,
) -> Litestar:
    """Create and configure the Litestar application.

    Args:
        enable_ui: Whether to enable the frontend UI routes.
        enable_api: Whether to enable the REST API routes.
        enable_websocket: Whether to enable WebSocket real-time features.
        debug: Whether to enable debug mode.
        json_logs: Whether to output logs as JSON (for production).

    Returns:
        Configured Litestar application instance.
    """
    # Configure structured logging
    configure_logging(debug=debug, json_logs=json_logs)

    # Get frontend directory for Vite
    frontend_dir = _get_frontend_directory()

    # Configure Vite plugin
    vite_plugin = VitePlugin(
        config=ViteConfig(
            dev_mode=debug,
            bundle_dir=f"{frontend_dir}/dist",
            resource_dir=f"{frontend_dir}/src",
            public_dir=f"{frontend_dir}/public",
            manifest_name=".vite/manifest.json",
            hot_file="hot",
            asset_url="/static/",
        )
    )

    # Try to import HTMXPlugin if available
    plugins: list = [sqlalchemy_plugin, ScribblCLIPlugin(), vite_plugin]

    if enable_ui:
        try:
            from litestar_htmx import HTMXPlugin

            plugins.append(HTMXPlugin())
        except ImportError:
            pass

    # Add the main scribbl plugin
    plugins.append(
        ScribblPlugin(
            ScribblConfig(
                storage=None,  # Use InMemoryStorage by default
                enable_api=enable_api,
                enable_websocket=enable_websocket,
                enable_ui=enable_ui,
                api_path="/api",
                ws_path="/ws",
                ui_path="/ui",
                static_path="/static",
                dependency_key="service",
            )
        )
    )

    # Root redirect handler
    @get("/", include_in_schema=False)
    async def root_redirect() -> Redirect:
        """Redirect root to UI dashboard."""
        return Redirect(path="/ui/")

    # Favicon redirect
    @get("/favicon.ico", include_in_schema=False)
    async def favicon_redirect() -> Redirect:
        """Redirect favicon.ico to SVG favicon."""
        return Redirect(path="/static/favicon.svg")

    route_handlers = [root_redirect, favicon_redirect, HealthController] if enable_ui else [HealthController]

    # Configure templates if UI is enabled (must be before Litestar init for VitePlugin)
    template_config = None
    if enable_ui:
        from pathlib import Path

        from litestar.contrib.jinja import JinjaTemplateEngine
        from litestar.template.config import TemplateConfig

        template_dir = Path(__file__).parent / "templates"
        template_config = TemplateConfig(
            directory=template_dir,
            engine=JinjaTemplateEngine,
        )

    # Build middleware stack
    middleware: list = [CorrelationIdMiddleware, RequestLoggingMiddleware]

    # Add rate limiting if enabled
    rate_limit_config = get_rate_limit_middleware()
    if rate_limit_config:
        middleware.append(rate_limit_config.middleware)

    return Litestar(
        route_handlers=route_handlers,
        plugins=plugins,
        debug=debug,
        lifespan=[lifespan],
        middleware=middleware,
        exception_handlers=get_exception_handlers(),
        template_config=template_config,
        openapi_config=OpenAPIConfig(
            title="scribbl-py API",
            version="0.1.0",
            description="Real-time collaborative drawing and Pictionary-style game API",
            path="/schema",
            render_plugins=get_openapi_plugins(),
            use_handler_docstrings=True,
        ),
    )


# Default application instance for uvicorn
# Use SCRIBBL_DEBUG=true for dev mode, defaults to False (production)
_debug = os.environ.get("SCRIBBL_DEBUG", "").lower() in ("true", "1", "yes")
app = create_app(enable_ui=True, enable_api=True, enable_websocket=True, debug=_debug)
