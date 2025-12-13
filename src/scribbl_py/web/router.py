"""Router configuration for the scribbl-py API."""

from __future__ import annotations

from litestar import Router

from scribbl_py.web.controllers import CanvasController, ElementController


def create_router(path: str = "/api") -> Router:
    """Create the scribbl-py API router.

    This function creates a Litestar Router with all the API controllers
    registered under the specified base path.

    Args:
        path: The base path for all API routes. Defaults to "/api".

    Returns:
        A configured Litestar Router instance.

    Example:
        >>> router = create_router("/api/v1")
        >>> # Use the router in your Litestar app configuration
    """
    return Router(
        path=path,
        route_handlers=[CanvasController, ElementController],
    )
