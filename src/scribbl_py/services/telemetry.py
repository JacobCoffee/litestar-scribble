"""Telemetry and analytics service for scribbl-py.

Tracks active visitors, players, games, and game statistics.
Can optionally integrate with external services like Sentry, PostHog, or Grafana.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID

import structlog

if TYPE_CHECKING:
    from collections.abc import Callable

logger = structlog.get_logger(__name__)


@dataclass
class TelemetryStats:
    """Current telemetry statistics snapshot."""

    # Active counts
    active_websocket_connections: int = 0
    active_game_rooms: int = 0
    active_players_in_games: int = 0
    spectators: int = 0

    # Cumulative counts (since server start)
    total_games_played: int = 0
    total_rounds_played: int = 0
    total_guesses: int = 0
    total_correct_guesses: int = 0
    total_drawings: int = 0

    # Recent activity (last 5 minutes)
    recent_games_started: int = 0
    recent_guesses: int = 0

    # Server info
    uptime_seconds: float = 0.0
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class TelemetryService:
    """Service for tracking and reporting telemetry data.

    Usage:
        telemetry = TelemetryService()

        # Track events
        telemetry.track_connection_opened()
        telemetry.track_game_started(room_id)
        telemetry.track_guess(room_id, player_id, correct=True, time_ms=1500)
        telemetry.track_game_ended(room_id, winner_id, final_scores)

        # Get stats
        stats = telemetry.get_stats()
    """

    def __init__(self) -> None:
        """Initialize the telemetry service."""
        self._started_at = datetime.now(UTC)
        self._stats = TelemetryStats(started_at=self._started_at)

        # Track recent events for rate calculations
        self._recent_events: list[tuple[datetime, str, dict[str, Any]]] = []
        self._recent_window = timedelta(minutes=5)

        # External integrations
        self._sentry_enabled = False
        self._posthog_enabled = False
        self._callbacks: list[Callable[[str, dict[str, Any]], None]] = []

        self._init_integrations()

    def _init_integrations(self) -> None:
        """Initialize external service integrations."""
        # Sentry integration
        sentry_dsn = os.environ.get("SENTRY_DSN")
        if sentry_dsn:
            try:
                import sentry_sdk

                sentry_sdk.init(
                    dsn=sentry_dsn,
                    traces_sample_rate=float(os.environ.get("SENTRY_TRACES_RATE", "0.1")),
                    profiles_sample_rate=float(os.environ.get("SENTRY_PROFILES_RATE", "0.1")),
                    environment=os.environ.get("ENVIRONMENT", "development"),
                )
                self._sentry_enabled = True
                logger.info("Sentry integration enabled")
            except ImportError:
                logger.debug("Sentry SDK not installed, skipping integration")

        # PostHog integration
        posthog_key = os.environ.get("POSTHOG_API_KEY")
        posthog_host = os.environ.get("POSTHOG_HOST", "https://app.posthog.com")
        if posthog_key:
            try:
                import posthog

                posthog.project_api_key = posthog_key
                posthog.host = posthog_host
                self._posthog_enabled = True
                logger.info("PostHog integration enabled")
            except ImportError:
                logger.debug("PostHog SDK not installed, skipping integration")

    def add_callback(self, callback: Callable[[str, dict[str, Any]], None]) -> None:
        """Add a callback for telemetry events.

        Args:
            callback: Function called with (event_name, event_data) for each event.
        """
        self._callbacks.append(callback)

    def _emit_event(self, event: str, data: dict[str, Any]) -> None:
        """Emit an event to all integrations and callbacks.

        Args:
            event: Event name.
            data: Event data.
        """
        now = datetime.now(UTC)

        # Track recent events
        self._recent_events.append((now, event, data))
        self._cleanup_recent_events()

        # Log the event
        logger.debug("Telemetry event", telemetry_event=event, **data)

        # Send to PostHog if enabled
        if self._posthog_enabled:
            try:
                import posthog

                distinct_id = data.get("user_id") or data.get("player_id") or "anonymous"
                posthog.capture(distinct_id, event, data)
            except Exception as e:
                logger.debug("PostHog capture failed", error=str(e))

        # Call registered callbacks
        for callback in self._callbacks:
            try:
                callback(event, data)
            except Exception as e:
                logger.debug("Telemetry callback failed", error=str(e))

    def _cleanup_recent_events(self) -> None:
        """Remove events older than the recent window."""
        cutoff = datetime.now(UTC) - self._recent_window
        self._recent_events = [(ts, ev, data) for ts, ev, data in self._recent_events if ts > cutoff]

    # === Connection Tracking ===

    def track_connection_opened(self, connection_type: str = "websocket") -> None:
        """Track a new connection opened.

        Args:
            connection_type: Type of connection (websocket, http).
        """
        if connection_type == "websocket":
            self._stats.active_websocket_connections += 1
        self._emit_event("connection_opened", {"type": connection_type})

    def track_connection_closed(self, connection_type: str = "websocket") -> None:
        """Track a connection closed.

        Args:
            connection_type: Type of connection.
        """
        if connection_type == "websocket":
            self._stats.active_websocket_connections = max(0, self._stats.active_websocket_connections - 1)
        self._emit_event("connection_closed", {"type": connection_type})

    # === Game Room Tracking ===

    def track_room_created(self, room_id: UUID, is_public: bool = False) -> None:
        """Track a new game room created.

        Args:
            room_id: Room identifier.
            is_public: Whether the room is public.
        """
        self._stats.active_game_rooms += 1
        self._emit_event("room_created", {"room_id": str(room_id), "is_public": is_public})

    def track_room_closed(self, room_id: UUID) -> None:
        """Track a game room closed.

        Args:
            room_id: Room identifier.
        """
        self._stats.active_game_rooms = max(0, self._stats.active_game_rooms - 1)
        self._emit_event("room_closed", {"room_id": str(room_id)})

    def track_player_joined(self, room_id: UUID, player_id: UUID, is_spectator: bool = False) -> None:
        """Track a player joining a room.

        Args:
            room_id: Room identifier.
            player_id: Player identifier.
            is_spectator: Whether joining as spectator.
        """
        if is_spectator:
            self._stats.spectators += 1
        else:
            self._stats.active_players_in_games += 1
        self._emit_event(
            "player_joined",
            {"room_id": str(room_id), "player_id": str(player_id), "is_spectator": is_spectator},
        )

    def track_player_left(self, room_id: UUID, player_id: UUID, is_spectator: bool = False) -> None:
        """Track a player leaving a room.

        Args:
            room_id: Room identifier.
            player_id: Player identifier.
            is_spectator: Whether was a spectator.
        """
        if is_spectator:
            self._stats.spectators = max(0, self._stats.spectators - 1)
        else:
            self._stats.active_players_in_games = max(0, self._stats.active_players_in_games - 1)
        self._emit_event(
            "player_left",
            {"room_id": str(room_id), "player_id": str(player_id), "is_spectator": is_spectator},
        )

    # === Game Event Tracking ===

    def track_game_started(self, room_id: UUID, player_count: int) -> None:
        """Track a game starting.

        Args:
            room_id: Room identifier.
            player_count: Number of players.
        """
        self._stats.recent_games_started += 1
        self._emit_event("game_started", {"room_id": str(room_id), "player_count": player_count})

    def track_round_started(self, room_id: UUID, round_number: int, drawer_id: UUID) -> None:
        """Track a round starting.

        Args:
            room_id: Room identifier.
            round_number: Current round number.
            drawer_id: Drawer player ID.
        """
        self._stats.total_rounds_played += 1
        self._emit_event(
            "round_started",
            {"room_id": str(room_id), "round_number": round_number, "drawer_id": str(drawer_id)},
        )

    def track_guess(
        self,
        room_id: UUID,
        player_id: UUID,
        correct: bool,
        time_ms: int | None = None,
    ) -> None:
        """Track a guess made.

        Args:
            room_id: Room identifier.
            player_id: Player who guessed.
            correct: Whether the guess was correct.
            time_ms: Time taken to guess in milliseconds.
        """
        self._stats.total_guesses += 1
        self._stats.recent_guesses += 1
        if correct:
            self._stats.total_correct_guesses += 1
        self._emit_event(
            "guess_made",
            {
                "room_id": str(room_id),
                "player_id": str(player_id),
                "correct": correct,
                "time_ms": time_ms,
            },
        )

    def track_drawing_completed(self, room_id: UUID, drawer_id: UUID, was_guessed: bool) -> None:
        """Track a drawing round completed.

        Args:
            room_id: Room identifier.
            drawer_id: Drawer player ID.
            was_guessed: Whether the drawing was guessed correctly by anyone.
        """
        self._stats.total_drawings += 1
        self._emit_event(
            "drawing_completed",
            {"room_id": str(room_id), "drawer_id": str(drawer_id), "was_guessed": was_guessed},
        )

    def track_game_ended(
        self,
        room_id: UUID,
        winner_id: UUID | None,
        player_count: int,
        rounds_played: int,
    ) -> None:
        """Track a game ending.

        Args:
            room_id: Room identifier.
            winner_id: Winner player ID (highest score).
            player_count: Number of players.
            rounds_played: Number of rounds played.
        """
        self._stats.total_games_played += 1
        self._emit_event(
            "game_ended",
            {
                "room_id": str(room_id),
                "winner_id": str(winner_id) if winner_id else None,
                "player_count": player_count,
                "rounds_played": rounds_played,
            },
        )

    # === Stats API ===

    def get_stats(self) -> TelemetryStats:
        """Get current telemetry statistics.

        Returns:
            Current stats snapshot.
        """
        self._cleanup_recent_events()

        # Update recent counts
        now = datetime.now(UTC)
        cutoff = now - self._recent_window
        self._stats.recent_games_started = sum(
            1 for ts, ev, _ in self._recent_events if ev == "game_started" and ts > cutoff
        )
        self._stats.recent_guesses = sum(1 for ts, ev, _ in self._recent_events if ev == "guess_made" and ts > cutoff)

        # Update uptime
        self._stats.uptime_seconds = (now - self._started_at).total_seconds()

        return self._stats

    def get_stats_dict(self) -> dict[str, Any]:
        """Get stats as a dictionary for JSON serialization.

        Returns:
            Stats as dict.
        """
        stats = self.get_stats()
        return {
            "active_websocket_connections": stats.active_websocket_connections,
            "active_game_rooms": stats.active_game_rooms,
            "active_players_in_games": stats.active_players_in_games,
            "spectators": stats.spectators,
            "total_games_played": stats.total_games_played,
            "total_rounds_played": stats.total_rounds_played,
            "total_guesses": stats.total_guesses,
            "total_correct_guesses": stats.total_correct_guesses,
            "total_drawings": stats.total_drawings,
            "recent_games_started": stats.recent_games_started,
            "recent_guesses": stats.recent_guesses,
            "uptime_seconds": stats.uptime_seconds,
            "started_at": stats.started_at.isoformat(),
        }


# Global telemetry service instance
_telemetry: TelemetryService | None = None


def get_telemetry() -> TelemetryService:
    """Get or create the global telemetry service.

    Returns:
        TelemetryService instance.
    """
    global _telemetry
    if _telemetry is None:
        _telemetry = TelemetryService()
    return _telemetry
