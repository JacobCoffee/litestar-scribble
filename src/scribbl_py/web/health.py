"""Health check endpoints for scribbl-py.

Provides /health and /ready endpoints for container orchestration
and load balancer health checks.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, ClassVar

from litestar import Controller, get

if TYPE_CHECKING:
    from litestar import Request


class HealthStatus(str, Enum):
    """Health check status values."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    """Health status of an individual component."""

    name: str
    status: HealthStatus
    message: str | None = None
    latency_ms: float | None = None


@dataclass
class HealthResponse:
    """Health check response."""

    status: HealthStatus
    version: str = "0.1.0"
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    components: list[ComponentHealth] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "status": self.status.value,
            "version": self.version,
            "timestamp": self.timestamp,
            "components": [
                {
                    "name": c.name,
                    "status": c.status.value,
                    "message": c.message,
                    "latency_ms": c.latency_ms,
                }
                for c in self.components
            ],
        }


@dataclass
class ReadyResponse:
    """Readiness check response."""

    ready: bool
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    checks: dict[str, bool] = field(default_factory=dict)


class HealthController(Controller):
    """Health check controller.

    Provides endpoints for liveness and readiness probes used by
    container orchestration systems like Kubernetes.
    """

    path = ""
    include_in_schema: ClassVar[bool] = True
    tags: ClassVar[list[str]] = ["Health"]

    @get("/health")
    async def health(self, request: Request) -> dict:
        """Liveness probe endpoint.

        Returns the overall health status of the application.
        This endpoint should return quickly and indicate if the
        application is alive and able to handle requests.

        Returns:
            Health status with component details.
        """
        components: list[ComponentHealth] = []

        # Check application state
        components.append(
            ComponentHealth(
                name="application",
                status=HealthStatus.HEALTHY,
                message="Application is running",
            )
        )

        # Check database if available
        db_health = await self._check_database(request)
        if db_health:
            components.append(db_health)

        # Determine overall status
        statuses = [c.status for c in components]
        if HealthStatus.UNHEALTHY in statuses:
            overall_status = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY

        response = HealthResponse(
            status=overall_status,
            components=components,
        )

        return response.to_dict()

    @get("/ready")
    async def ready(self, request: Request) -> dict:
        """Readiness probe endpoint.

        Indicates if the application is ready to receive traffic.
        Unlike /health, this checks if all dependencies are available.

        Returns:
            Readiness status with individual check results.
        """
        checks: dict[str, bool] = {}

        # Check if application is initialized
        checks["application"] = True

        # Check database connection if available
        db_ready = await self._check_database_ready(request)
        if db_ready is not None:
            checks["database"] = db_ready

        all_ready = all(checks.values())

        response = ReadyResponse(
            ready=all_ready,
            checks=checks,
        )

        return {
            "ready": response.ready,
            "timestamp": response.timestamp,
            "checks": response.checks,
        }

    async def _check_database(self, request: Request) -> ComponentHealth | None:
        """Check database health."""
        try:
            if not hasattr(request.app.state, "db_manager"):
                return None

            db_manager = request.app.state.db_manager
            if db_manager is None:
                return None

            start = time.perf_counter()
            # Execute a simple query to check connectivity
            async with db_manager.session() as session:
                from sqlalchemy import text

                await session.execute(text("SELECT 1"))
            latency = (time.perf_counter() - start) * 1000

            return ComponentHealth(
                name="database",
                status=HealthStatus.HEALTHY,
                message="Database connection successful",
                latency_ms=round(latency, 2),
            )
        except Exception as e:  # noqa: BLE001
            return ComponentHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Database error: {e!s}",
            )

    async def _check_database_ready(self, request: Request) -> bool | None:
        """Check if database is ready."""
        try:
            if not hasattr(request.app.state, "db_manager"):
                return None

            db_manager = request.app.state.db_manager
            if db_manager is None:
                return None

            async with db_manager.session() as session:
                from sqlalchemy import text

                await session.execute(text("SELECT 1"))
            return True
        except Exception:  # noqa: BLE001
            return False
