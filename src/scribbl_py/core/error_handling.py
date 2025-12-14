"""Error handling and exception handlers for scribbl-py.

Provides structured error responses with correlation IDs and proper HTTP status codes.
For UI routes, redirects to error pages with toast notifications.
"""

from __future__ import annotations

import urllib.parse
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import structlog
from litestar import Response
from litestar.response import Redirect
from litestar.status_codes import (
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

if TYPE_CHECKING:
    from litestar import Request
    from litestar.exceptions import HTTPException, ValidationException

logger = structlog.get_logger(__name__)

# Paths that should return JSON responses (API endpoints)
API_PATH_PREFIXES = ("/api/", "/health", "/ready", "/stats", "/ws/")


def is_api_request(request: Request) -> bool:
    """Check if the request is for an API endpoint.

    Returns True for:
    - Paths starting with API prefixes
    - Requests with Accept: application/json header
    - HTMX requests (they expect HTML fragments, but we handle separately)
    """
    path = request.url.path

    # Check path prefixes
    if any(path.startswith(prefix) for prefix in API_PATH_PREFIXES):
        return True

    # Check Accept header for explicit JSON request
    accept = request.headers.get("accept", "")
    if "application/json" in accept and "text/html" not in accept:
        return True

    return False


def create_error_redirect(
    request: Request,
    message: str,
    error_type: str = "error",
    redirect_to: str | None = None,
) -> Redirect:
    """Create a redirect response with error toast for UI requests.

    Args:
        request: The request object.
        message: Error message to display.
        error_type: Toast type (error, warning, info).
        redirect_to: URL to redirect to. Defaults to referrer or home.

    Returns:
        Redirect response with error query params.
    """
    # If already showing an error (URL has error param), redirect to home to break loop
    if request.query_params.get("error"):
        return Redirect(path="/ui/")

    # Determine redirect target
    if redirect_to is None:
        # Try referrer first, then fall back to canvas-clash home or main UI
        referrer = request.headers.get("referer", "")
        if referrer and "/canvas-clash/" in referrer:
            redirect_to = "/canvas-clash/"
        elif referrer and "/ui/" in referrer:
            redirect_to = "/ui/"
        elif request.url.path.startswith("/canvas-clash/"):
            redirect_to = "/canvas-clash/"
        else:
            redirect_to = "/ui/"

    # Add error message as query parameter
    params = urllib.parse.urlencode({"error": message, "error_type": error_type})
    redirect_url = f"{redirect_to}?{params}"

    return Redirect(path=redirect_url)


@dataclass
class ErrorDetail:
    """Details about a specific error."""

    field: str | None = None
    message: str = ""
    code: str = "error"


@dataclass
class ErrorResponse:
    """Structured error response format."""

    status: str = "error"
    message: str = ""
    code: str = "internal_error"
    correlation_id: str | None = None
    details: list[ErrorDetail] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON response."""
        result: dict[str, Any] = {
            "status": self.status,
            "message": self.message,
            "code": self.code,
        }
        if self.correlation_id:
            result["correlation_id"] = self.correlation_id
        if self.details:
            result["details"] = [{"field": d.field, "message": d.message, "code": d.code} for d in self.details]
        return result


def get_correlation_id(request: Request) -> str | None:
    """Extract correlation ID from request state or headers."""
    # Try request state first (set by middleware)
    if hasattr(request, "state") and hasattr(request.state, "correlation_id"):
        return request.state.correlation_id
    # Fall back to header
    return request.headers.get("X-Correlation-ID") or request.headers.get("X-Request-ID")


def validation_exception_handler(request: Request, exc: ValidationException) -> Response[dict[str, Any]]:
    """Handle Pydantic/msgspec validation errors with detailed field information.

    Returns a structured response with per-field error details.
    """
    correlation_id = get_correlation_id(request)

    details: list[ErrorDetail] = []

    # Parse validation errors from the exception
    if hasattr(exc, "extra") and exc.extra:
        for error in exc.extra:
            if isinstance(error, dict):
                # Extract field location and message
                loc = error.get("loc", [])
                field_path = ".".join(str(p) for p in loc) if loc else None
                msg = error.get("msg", error.get("message", str(error)))
                error_type = error.get("type", "validation_error")
                details.append(ErrorDetail(field=field_path, message=msg, code=error_type))
            else:
                details.append(ErrorDetail(message=str(error), code="validation_error"))

    # If no structured errors, use the exception message
    if not details:
        details.append(ErrorDetail(message=str(exc.detail), code="validation_error"))

    error_response = ErrorResponse(
        message="Validation failed",
        code="validation_error",
        correlation_id=correlation_id,
        details=details,
    )

    logger.warning(
        "Validation error",
        correlation_id=correlation_id,
        path=request.url.path,
        method=request.method,
        error_count=len(details),
    )

    return Response(
        content=error_response.to_dict(),
        status_code=HTTP_422_UNPROCESSABLE_ENTITY,
        media_type="application/json",
    )


def http_exception_handler(request: Request, exc: HTTPException) -> Response[dict[str, Any]] | Redirect:
    """Handle HTTP exceptions with structured responses or redirects for UI."""
    correlation_id = get_correlation_id(request)

    # Map status codes to error codes
    code_map = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        405: "method_not_allowed",
        409: "conflict",
        422: "validation_error",
        429: "rate_limited",
        500: "internal_error",
        502: "bad_gateway",
        503: "service_unavailable",
    }

    # Map status codes to user-friendly messages
    friendly_messages = {
        400: "Bad request. Please check your input.",
        401: "Please log in to continue.",
        403: "You don't have permission to access this.",
        404: "Page not found. The resource you're looking for doesn't exist.",
        405: "This action is not allowed.",
        409: "There was a conflict with the current state.",
        422: "Invalid data provided.",
        429: "Too many requests. Please slow down.",
        500: "Something went wrong. Please try again.",
        502: "Server error. Please try again later.",
        503: "Service temporarily unavailable.",
    }

    error_code = code_map.get(exc.status_code, "error")
    message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)

    log_level = "warning" if exc.status_code < 500 else "error"
    getattr(logger, log_level)(
        "HTTP exception",
        correlation_id=correlation_id,
        path=request.url.path,
        method=request.method,
        status_code=exc.status_code,
        error_code=error_code,
    )

    # For UI requests, redirect with error toast
    if not is_api_request(request):
        friendly_message = friendly_messages.get(exc.status_code, message)
        return create_error_redirect(request, friendly_message, "error")

    # For API requests, return JSON
    error_response = ErrorResponse(
        message=message,
        code=error_code,
        correlation_id=correlation_id,
    )

    return Response(
        content=error_response.to_dict(),
        status_code=exc.status_code,
        media_type="application/json",
    )


def canvas_not_found_handler(request: Request, exc: Exception) -> Response[dict[str, Any]] | Redirect:
    """Handle CanvasNotFoundError exceptions."""
    correlation_id = get_correlation_id(request)

    canvas_id = getattr(exc, "canvas_id", "unknown")

    logger.warning(
        "Canvas not found",
        correlation_id=correlation_id,
        canvas_id=str(canvas_id),
        path=request.url.path,
    )

    # For UI requests, redirect with error toast
    if not is_api_request(request):
        return create_error_redirect(request, "Canvas not found.", "error")

    error_response = ErrorResponse(
        message=f"Canvas not found: {canvas_id}",
        code="canvas_not_found",
        correlation_id=correlation_id,
        details=[ErrorDetail(field="canvas_id", message=str(exc), code="not_found")],
    )

    return Response(
        content=error_response.to_dict(),
        status_code=HTTP_404_NOT_FOUND,
        media_type="application/json",
    )


def element_not_found_handler(request: Request, exc: Exception) -> Response[dict[str, Any]] | Redirect:
    """Handle ElementNotFoundError exceptions."""
    correlation_id = get_correlation_id(request)

    element_id = getattr(exc, "element_id", "unknown")

    logger.warning(
        "Element not found",
        correlation_id=correlation_id,
        element_id=str(element_id),
        path=request.url.path,
    )

    # For UI requests, redirect with error toast
    if not is_api_request(request):
        return create_error_redirect(request, "Element not found.", "error")

    error_response = ErrorResponse(
        message=f"Element not found: {element_id}",
        code="element_not_found",
        correlation_id=correlation_id,
        details=[ErrorDetail(field="element_id", message=str(exc), code="not_found")],
    )

    return Response(
        content=error_response.to_dict(),
        status_code=HTTP_404_NOT_FOUND,
        media_type="application/json",
    )


def game_error_handler(request: Request, exc: Exception) -> Response[dict[str, Any]] | Redirect:
    """Handle GameError exceptions."""
    correlation_id = get_correlation_id(request)

    logger.warning(
        "Game error",
        correlation_id=correlation_id,
        error=str(exc),
        path=request.url.path,
    )

    # For UI requests, redirect with error toast
    if not is_api_request(request):
        return create_error_redirect(request, str(exc), "warning")

    error_response = ErrorResponse(
        message=str(exc),
        code="game_error",
        correlation_id=correlation_id,
    )

    return Response(
        content=error_response.to_dict(),
        status_code=HTTP_400_BAD_REQUEST,
        media_type="application/json",
    )


def generic_exception_handler(request: Request, exc: Exception) -> Response[dict[str, Any]] | Redirect:
    """Handle unexpected exceptions with a generic error response.

    Logs the full exception but returns a safe message to the client.
    """
    correlation_id = get_correlation_id(request)

    logger.exception(
        "Unhandled exception",
        correlation_id=correlation_id,
        path=request.url.path,
        method=request.method,
        exc_info=exc,
    )

    # For UI requests, redirect with error toast
    if not is_api_request(request):
        return create_error_redirect(request, "Something went wrong. Please try again.", "error")

    error_response = ErrorResponse(
        message="An unexpected error occurred. Please try again later.",
        code="internal_error",
        correlation_id=correlation_id,
    )

    return Response(
        content=error_response.to_dict(),
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        media_type="application/json",
    )


def get_exception_handlers() -> dict:
    """Get all exception handlers for the application.

    Returns:
        Dictionary mapping exception types to handler functions.

    Note:
        Uses deferred imports to avoid circular dependencies.
    """
    from litestar.exceptions import HTTPException, ValidationException

    from scribbl_py.exceptions import CanvasNotFoundError, ElementNotFoundError
    from scribbl_py.game.exceptions import GameError

    return {
        ValidationException: validation_exception_handler,
        HTTPException: http_exception_handler,
        CanvasNotFoundError: canvas_not_found_handler,
        ElementNotFoundError: element_not_found_handler,
        GameError: game_error_handler,
        Exception: generic_exception_handler,
    }
