"""Rate limiting configuration for scribbl-py.

Provides configurable rate limiting using Litestar's built-in RateLimitMiddleware.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Literal

from litestar.middleware.rate_limit import RateLimitConfig

TimeUnit = Literal["second", "minute", "hour", "day"]


@dataclass
class RateLimitSettings:
    """Rate limiting configuration settings.

    Attributes:
        enabled: Whether rate limiting is enabled.
        requests_per_minute: Default rate limit (requests per minute).
        api_requests_per_minute: Rate limit for API endpoints.
        ws_connections_per_minute: Rate limit for WebSocket connections.
        auth_requests_per_minute: Rate limit for auth endpoints (lower to prevent brute force).
        exclude_paths: Paths to exclude from rate limiting.
    """

    enabled: bool = True
    requests_per_minute: int = 100
    api_requests_per_minute: int = 60
    ws_connections_per_minute: int = 10
    auth_requests_per_minute: int = 20
    exclude_paths: list[str] = field(
        default_factory=lambda: [
            "/health",
            "/ready",
            "/schema",
            "/schema/swagger",
            "/static",
            "/favicon.ico",
            "/auth/navbar",  # HTMX partial - exclude to prevent redirect loops
            "/auth/guest",  # Guest login - needs to work reliably
        ]
    )

    @classmethod
    def from_env(cls) -> RateLimitSettings:
        """Create settings from environment variables.

        Environment variables:
            RATE_LIMIT_ENABLED: Set to "false" to disable rate limiting.
            RATE_LIMIT_PER_MINUTE: Default requests per minute (default: 100).
            RATE_LIMIT_API_PER_MINUTE: API requests per minute (default: 60).
            RATE_LIMIT_AUTH_PER_MINUTE: Auth requests per minute (default: 20).

        Returns:
            RateLimitSettings configured from environment.
        """
        return cls(
            enabled=os.environ.get("RATE_LIMIT_ENABLED", "true").lower() != "false",
            requests_per_minute=int(os.environ.get("RATE_LIMIT_PER_MINUTE", "100")),
            api_requests_per_minute=int(os.environ.get("RATE_LIMIT_API_PER_MINUTE", "60")),
            auth_requests_per_minute=int(os.environ.get("RATE_LIMIT_AUTH_PER_MINUTE", "20")),
        )


def create_rate_limit_config(
    settings: RateLimitSettings | None = None,
) -> RateLimitConfig:
    """Create rate limit configuration.

    Args:
        settings: Rate limit settings. If None, loads from environment.

    Returns:
        Configured RateLimitConfig middleware.
    """
    if settings is None:
        settings = RateLimitSettings.from_env()

    return RateLimitConfig(
        rate_limit=("minute", settings.requests_per_minute),
        exclude=settings.exclude_paths,
        exclude_opt_key="exclude_from_rate_limit",
    )


def get_rate_limit_middleware(
    settings: RateLimitSettings | None = None,
) -> RateLimitConfig | None:
    """Get rate limit middleware if enabled.

    Args:
        settings: Rate limit settings. If None, loads from environment.

    Returns:
        RateLimitConfig if rate limiting is enabled, None otherwise.
    """
    if settings is None:
        settings = RateLimitSettings.from_env()

    if not settings.enabled:
        return None

    return create_rate_limit_config(settings)
