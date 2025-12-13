"""Minimal example showing scribbl-py usage with Litestar.

This example demonstrates how to create a basic Litestar application with
scribbl-py integration using the plugin system.

The application will:
    - Automatically configure the CanvasService with InMemoryStorage
    - Mount REST API endpoints at /api
    - Enable dependency injection for CanvasService in route handlers

Running the Application:
    python examples/app.py

Then visit:
    - http://127.0.0.1:8000/schema - OpenAPI documentation
    - http://127.0.0.1:8000/api/canvases - Canvas endpoints

Example API Usage:
    # Create a new canvas
    curl -X POST http://127.0.0.1:8000/api/canvases \\
        -H "Content-Type: application/json" \\
        -d '{"name": "My Canvas", "width": 1920, "height": 1080}'

    # List all canvases
    curl http://127.0.0.1:8000/api/canvases

    # Get a specific canvas
    curl http://127.0.0.1:8000/api/canvases/{canvas_id}

For more advanced usage examples, see the other example files in this directory.
"""

from __future__ import annotations

from litestar import Litestar

from scribbl_py import ScribblConfig, ScribblPlugin

# Create the Litestar app with scribbl-py plugin
app = Litestar(
    plugins=[
        ScribblPlugin(
            ScribblConfig(
                # Use InMemoryStorage (default)
                storage=None,
                # Enable REST API endpoints
                enable_api=True,
                # Mount API routes at /api
                api_path="/api",
                # Use "service" as the dependency key
                dependency_key="service",
            )
        )
    ],
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
