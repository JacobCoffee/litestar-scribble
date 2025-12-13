"""Stats API controller for telemetry and analytics."""

from __future__ import annotations

from typing import Any, ClassVar

from litestar import Controller, get

from scribbl_py.services.telemetry import get_telemetry


class StatsController(Controller):
    """Controller for stats and telemetry endpoints."""

    path = "/stats"
    tags: ClassVar[list[str]] = ["Stats"]

    @get("/")
    async def get_stats(self) -> dict[str, Any]:
        """Get current server statistics.

        Returns:
            Current telemetry statistics including active connections,
            games, players, and cumulative counts.
        """
        telemetry = get_telemetry()
        return telemetry.get_stats_dict()
