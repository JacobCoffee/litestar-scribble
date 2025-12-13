"""Structured logging configuration with correlation IDs for scribbl-py.

Provides request/response logging middleware and structured logging setup.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from litestar.types import ASGIApp, Message, Receive, Scope, Send


def configure_logging(*, debug: bool = False, json_logs: bool = False) -> None:
    """Configure structured logging for the application.

    Args:
        debug: Enable debug level logging.
        json_logs: Output logs as JSON (for production).
    """
    processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if json_logs:
        # Production: JSON output
        processors.extend(
            [
                structlog.processors.format_exc_info,
                structlog.processors.JSONRenderer(),
            ]
        )
    else:
        # Development: colored console output
        processors.extend(
            [
                structlog.processors.ExceptionPrettyPrinter(),
                structlog.dev.ConsoleRenderer(colors=True),
            ]
        )

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG if debug else logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


class CorrelationIdMiddleware:
    """Middleware that adds correlation IDs to all requests.

    The correlation ID is:
    1. Read from X-Correlation-ID or X-Request-ID header if present
    2. Generated as a new UUID if not present
    3. Stored in request state for access by handlers
    4. Added to response headers
    5. Added to structlog context for all log messages
    """

    def __init__(self, app: ASGIApp) -> None:
        """Initialize the middleware.

        Args:
            app: The ASGI application.
        """
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process the request and add correlation ID."""
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        # Extract or generate correlation ID
        headers = dict(scope.get("headers", []))
        correlation_id = (
            headers.get(b"x-correlation-id", b"").decode()
            or headers.get(b"x-request-id", b"").decode()
            or str(uuid.uuid4())
        )

        # Store in scope state for later access
        if "state" not in scope:
            scope["state"] = {}
        scope["state"]["correlation_id"] = correlation_id

        # Bind to structlog context
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            correlation_id=correlation_id,
            path=scope.get("path", ""),
            method=scope.get("method", ""),
        )

        async def send_wrapper(message: Message) -> None:
            """Add correlation ID to response headers."""
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-correlation-id", correlation_id.encode()))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            structlog.contextvars.clear_contextvars()


class RequestLoggingMiddleware:
    """Middleware that logs request/response information.

    Logs:
    - Request method, path, and client info on request start
    - Response status code and duration on request end
    - Errors with full context
    """

    def __init__(self, app: ASGIApp, *, exclude_paths: set[str] | None = None) -> None:
        """Initialize the middleware.

        Args:
            app: The ASGI application.
            exclude_paths: Paths to exclude from logging (e.g., health checks).
        """
        self.app = app
        self.exclude_paths = exclude_paths or {"/health", "/ready", "/favicon.ico"}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process the request and log information."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        # Skip excluded paths
        if path in self.exclude_paths:
            await self.app(scope, receive, send)
            return

        logger = structlog.get_logger(__name__)
        start_time = time.perf_counter()
        status_code = 500  # Default in case of error

        # Extract client info
        client = scope.get("client")
        client_ip = client[0] if client else "unknown"

        async def send_wrapper(message: Message) -> None:
            """Capture response status code."""
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 500)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            logger.exception(
                "Request failed with exception",
                client_ip=client_ip,
            )
            raise
        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Log at appropriate level based on status
            if status_code >= 500:
                log_method = logger.error
            elif status_code >= 400:
                log_method = logger.warning
            else:
                log_method = logger.info

            log_method(
                "Request completed",
                status_code=status_code,
                duration_ms=round(duration_ms, 2),
                client_ip=client_ip,
            )


def get_middleware() -> list:
    """Get the logging middleware stack.

    Returns:
        List of middleware classes in the order they should be applied.
    """
    return [
        CorrelationIdMiddleware,
        RequestLoggingMiddleware,
    ]
