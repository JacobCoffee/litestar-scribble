"""Example showing scribbl-py with frontend UI enabled.

This example demonstrates how to create a Litestar application with
scribbl-py integration including the full frontend UI.

The application will:
    - Automatically configure the CanvasService with InMemoryStorage
    - Mount REST API endpoints at /api
    - Mount WebSocket endpoints at /ws
    - Mount UI routes at /ui
    - Serve static files at /static
    - Enable dependency injection for CanvasService in route handlers

Running the Application:
    1. Build frontend assets: make frontend-build
    2. Run the app: make serve-ui

Then visit:
    - http://127.0.0.1:8000/ui/ - Frontend UI dashboard
    - http://127.0.0.1:8000/schema - OpenAPI documentation
    - http://127.0.0.1:8000/api/canvases - Canvas API endpoints
"""

from __future__ import annotations

from litestar import Litestar

from scribbl_py import ScribblConfig, ScribblPlugin

# Try to import HTMXPlugin if available
try:
    from litestar_htmx import HTMXPlugin

    htmx_plugin = HTMXPlugin()
except ImportError:
    htmx_plugin = None

# Create the Litestar app with scribbl-py plugin and UI enabled
plugins = [
    ScribblPlugin(
        ScribblConfig(
            # Use InMemoryStorage (default)
            storage=None,
            # Enable REST API endpoints
            enable_api=True,
            # Enable WebSocket real-time features
            enable_websocket=True,
            # Enable frontend UI
            enable_ui=True,
            # Mount API routes at /api
            api_path="/api",
            # Mount WebSocket routes at /ws
            ws_path="/ws",
            # Use "service" as the dependency key
            dependency_key="service",
        )
    )
]

if htmx_plugin:
    plugins.append(htmx_plugin)

app = Litestar(
    plugins=plugins,
    debug=True,
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="info",
    )
