"""Task queue configuration and scheduled tasks using Huey.

Provides background task processing and scheduled jobs for:
- Session cleanup (expired sessions)
- Leaderboard resets (weekly/monthly)
- Canvas cleanup (abandoned canvases)
- Telemetry aggregation
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from huey import SqliteHuey

# Lazy Huey instance - only created when tasks extra is installed
_huey_instance: SqliteHuey | None = None


@dataclass
class TaskQueueSettings:
    """Task queue configuration settings.

    Attributes:
        enabled: Whether task queue is enabled.
        db_path: Path to Huey's SQLite database for task storage.
        immediate: Run tasks immediately (for testing).
        utc: Use UTC timezone for scheduling.
    """

    enabled: bool = True
    db_path: str = "./huey_tasks.db"
    immediate: bool = False
    utc: bool = True

    @classmethod
    def from_env(cls) -> TaskQueueSettings:
        """Create settings from environment variables.

        Environment variables:
            TASK_QUEUE_ENABLED: Set to "false" to disable task queue.
            TASK_QUEUE_DB_PATH: Path to Huey SQLite database.
            TASK_QUEUE_IMMEDIATE: Set to "true" for immediate execution (testing).

        Returns:
            TaskQueueSettings configured from environment.
        """
        return cls(
            enabled=os.environ.get("TASK_QUEUE_ENABLED", "true").lower() != "false",
            db_path=os.environ.get("TASK_QUEUE_DB_PATH", "./huey_tasks.db"),
            immediate=os.environ.get("TASK_QUEUE_IMMEDIATE", "false").lower() == "true",
        )


def get_huey(settings: TaskQueueSettings | None = None) -> SqliteHuey:
    """Get or create the Huey task queue instance.

    Args:
        settings: Task queue settings. If None, loads from environment.

    Returns:
        Configured SqliteHuey instance.

    Raises:
        ImportError: If huey is not installed (tasks extra not installed).
    """
    global _huey_instance  # noqa: PLW0603

    if _huey_instance is not None:
        return _huey_instance

    try:
        from huey import SqliteHuey
    except ImportError as e:
        msg = "Huey is not installed. Install with: uv add scribbl-py[tasks]"
        raise ImportError(msg) from e

    if settings is None:
        settings = TaskQueueSettings.from_env()

    # Ensure directory exists for database
    db_path = Path(settings.db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    _huey_instance = SqliteHuey(
        name="scribbl",
        filename=str(db_path),
        immediate=settings.immediate,
        utc=settings.utc,
    )

    return _huey_instance


# Create module-level huey for task decorators
# This is lazy - actual instance created on first access
def _get_lazy_huey() -> SqliteHuey:
    """Get Huey instance lazily."""
    return get_huey()


# ============================================================================
# Scheduled Tasks
# ============================================================================


def register_tasks() -> None:
    """Register all scheduled tasks with Huey.

    This must be called after Huey is configured to register the periodic tasks.
    """
    huey = get_huey()

    # Import crontab here to avoid import errors when huey not installed
    from huey import crontab

    # Register cleanup_expired_sessions - runs daily at 3 AM
    @huey.periodic_task(crontab(minute="0", hour="3"))
    def cleanup_expired_sessions_task() -> dict:
        """Clean up expired sessions from the database."""
        return _run_cleanup_expired_sessions()

    # Register reset_weekly_stats - runs every Monday at midnight
    @huey.periodic_task(crontab(minute="0", hour="0", day_of_week="1"))
    def reset_weekly_stats_task() -> dict:
        """Reset weekly leaderboard statistics."""
        return _run_reset_weekly_stats()

    # Register cleanup_old_canvases - runs daily at 4 AM
    @huey.periodic_task(crontab(minute="0", hour="4"))
    def cleanup_old_canvases_task() -> dict:
        """Clean up abandoned canvases older than retention period."""
        return _run_cleanup_old_canvases()

    # Register aggregate_telemetry - runs hourly
    @huey.periodic_task(crontab(minute="0"))
    def aggregate_telemetry_task() -> dict:
        """Aggregate telemetry data for reporting."""
        return _run_aggregate_telemetry()


# ============================================================================
# Task Implementations
# ============================================================================


def _run_cleanup_expired_sessions() -> dict:
    """Clean up expired sessions.

    Returns:
        Dict with cleanup results.
    """
    import asyncio

    import structlog

    logger = structlog.get_logger(__name__)

    async def _cleanup() -> int:
        try:
            from scribbl_py.storage.db.setup import DatabaseManager

            db = DatabaseManager()
            await db.init()

            async with db.session() as session:
                from scribbl_py.storage.db.auth_storage import AuthDatabaseStorage

                storage = AuthDatabaseStorage(session)
                deleted = await storage.delete_expired_sessions()
                await session.commit()
                return deleted
        except ImportError:
            logger.warning("Database not configured, skipping session cleanup")
            return 0
        except Exception as e:
            logger.error("Session cleanup failed", error=str(e))
            return 0

    deleted = asyncio.run(_cleanup())
    logger.info("Session cleanup completed", deleted_sessions=deleted)

    return {
        "task": "cleanup_expired_sessions",
        "deleted": deleted,
        "timestamp": datetime.now(UTC).isoformat(),
    }


def _run_reset_weekly_stats() -> dict:
    """Reset weekly leaderboard statistics.

    This resets current_win_streak for all users while preserving best_win_streak.

    Returns:
        Dict with reset results.
    """
    import asyncio

    import structlog

    logger = structlog.get_logger(__name__)

    async def _reset() -> int:
        try:
            from sqlalchemy import update

            from scribbl_py.storage.db.auth_models import UserStatsModel
            from scribbl_py.storage.db.setup import DatabaseManager

            db = DatabaseManager()
            await db.init()

            async with db.session() as session:
                # Reset current win streaks (weekly reset)
                stmt = update(UserStatsModel).values(current_win_streak=0)
                result = await session.execute(stmt)
                await session.commit()
                return result.rowcount
        except ImportError:
            logger.warning("Database not configured, skipping weekly reset")
            return 0
        except Exception as e:
            logger.error("Weekly stats reset failed", error=str(e))
            return 0

    reset_count = asyncio.run(_reset())
    logger.info("Weekly stats reset completed", users_reset=reset_count)

    return {
        "task": "reset_weekly_stats",
        "users_reset": reset_count,
        "timestamp": datetime.now(UTC).isoformat(),
    }


def _run_cleanup_old_canvases() -> dict:
    """Clean up canvases that haven't been modified in the retention period.

    Default retention: 30 days for canvases without activity.

    Returns:
        Dict with cleanup results.
    """
    import asyncio

    import structlog

    logger = structlog.get_logger(__name__)

    retention_days = int(os.environ.get("CANVAS_RETENTION_DAYS", "30"))
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)

    async def _cleanup() -> int:
        try:
            from sqlalchemy import delete

            from scribbl_py.storage.db.models import CanvasModel
            from scribbl_py.storage.db.setup import DatabaseManager

            db = DatabaseManager()
            await db.init()

            async with db.session() as session:
                # Delete canvases not updated within retention period
                stmt = delete(CanvasModel).where(CanvasModel.updated_at < cutoff)
                result = await session.execute(stmt)
                await session.commit()
                return result.rowcount
        except ImportError:
            logger.warning("Database not configured, skipping canvas cleanup")
            return 0
        except Exception as e:
            logger.error("Canvas cleanup failed", error=str(e))
            return 0

    deleted = asyncio.run(_cleanup())
    logger.info(
        "Canvas cleanup completed",
        deleted_canvases=deleted,
        retention_days=retention_days,
    )

    return {
        "task": "cleanup_old_canvases",
        "deleted": deleted,
        "retention_days": retention_days,
        "timestamp": datetime.now(UTC).isoformat(),
    }


def _run_aggregate_telemetry() -> dict:
    """Aggregate telemetry data for reporting.

    This collects current telemetry stats and can be extended to persist
    historical data for analytics.

    Returns:
        Dict with current telemetry snapshot.
    """
    import structlog

    logger = structlog.get_logger(__name__)

    try:
        from scribbl_py.services.telemetry import get_telemetry

        telemetry = get_telemetry()
        stats = telemetry.get_stats_dict()

        logger.info(
            "Telemetry aggregated",
            active_connections=stats.get("active_connections", 0),
            active_games=stats.get("active_games", 0),
        )

        return {
            "task": "aggregate_telemetry",
            "stats": stats,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except ImportError:
        logger.warning("Telemetry service not available")
        return {
            "task": "aggregate_telemetry",
            "stats": {},
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        logger.error("Telemetry aggregation failed", error=str(e))
        return {
            "task": "aggregate_telemetry",
            "error": str(e),
            "timestamp": datetime.now(UTC).isoformat(),
        }


# ============================================================================
# On-Demand Tasks (can be called directly or queued)
# ============================================================================


def enqueue_session_cleanup() -> None:
    """Enqueue a session cleanup task for immediate execution."""
    huey = get_huey()

    @huey.task()
    def _cleanup_now() -> dict:
        return _run_cleanup_expired_sessions()

    _cleanup_now()


def enqueue_canvas_cleanup() -> None:
    """Enqueue a canvas cleanup task for immediate execution."""
    huey = get_huey()

    @huey.task()
    def _cleanup_now() -> dict:
        return _run_cleanup_old_canvases()

    _cleanup_now()
