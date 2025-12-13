"""Custom OpenAPI UI plugins with scribbl-py theming."""

from __future__ import annotations

from litestar.openapi.plugins import ScalarRenderPlugin, SwaggerRenderPlugin


def get_openapi_plugins() -> list[ScalarRenderPlugin | SwaggerRenderPlugin]:
    """Get the configured OpenAPI UI plugins.

    Returns:
        List of OpenAPI UI plugins with Scalar as primary and Swagger as secondary.

    Endpoints (relative to OpenAPIConfig.path which is /schema):
        - /schema/ or /schema/docs - Scalar UI (default)
        - /schema/swagger - Swagger UI
        - /schema/openapi.json - OpenAPI schema
    """
    return [
        ScalarRenderPlugin(
            path="/",
            css_url="/static/css/scalar-theme.css",
        ),
        SwaggerRenderPlugin(
            path="/swagger",
        ),
    ]
