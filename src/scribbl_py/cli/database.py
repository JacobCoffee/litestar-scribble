"""Custom database CLI commands for scribbl-py.

Adds query helpers for inspecting users, games, stats, and leaderboards.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import TYPE_CHECKING

import rich_click as click
from litestar.plugins import CLIPluginProtocol
from rich.console import Console
from rich.table import Table
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import Session, joinedload, sessionmaker

if TYPE_CHECKING:
    from collections.abc import Generator

console = Console()


def get_database_url() -> str:
    """Get the database URL from environment or default to SQLite."""
    url = os.environ.get("DATABASE_URL", "sqlite:///./scribbl.db")
    # Convert async URL to sync for CLI
    if "+aiosqlite" in url:
        url = url.replace("+aiosqlite", "")
    if "+asyncpg" in url:
        url = url.replace("+asyncpg", "+psycopg2")
    return url


@contextmanager
def get_sync_session() -> Generator[Session, None, None]:
    """Get a sync database session for CLI operations."""
    url = get_database_url()
    engine = create_engine(url)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@click.group(name="query", help="Query database tables for debugging and inspection.")
def query_group() -> None:
    """Query database tables for debugging and inspection."""


@query_group.command(name="users", help="List users in the database.")
@click.option("--limit", "-l", default=20, help="Number of users to show")
@click.option("--search", "-s", default=None, help="Search by username or email")
def query_users(limit: int, search: str | None) -> None:
    """List users in the database."""
    from scribbl_py.storage.db.auth_models import UserModel

    with get_sync_session() as session:
        stmt = select(UserModel).limit(limit)
        if search:
            stmt = stmt.where(UserModel.username.ilike(f"%{search}%") | UserModel.email.ilike(f"%{search}%"))
        result = session.execute(stmt)
        users = result.scalars().all()

        table = Table(title=f"Users (showing {len(users)})")
        table.add_column("ID", style="dim")
        table.add_column("Username", style="cyan")
        table.add_column("Email", style="green")
        table.add_column("Provider", style="yellow")
        table.add_column("Created", style="magenta")

        for user in users:
            table.add_row(
                str(user.id)[:8] + "...",
                user.username,
                user.email or "-",
                user.oauth_provider or "local",
                user.created_at.strftime("%Y-%m-%d %H:%M") if user.created_at else "-",
            )

        console.print(table)


@query_group.command(name="stats", help="Show user statistics (games played, wins, etc.).")
@click.option("--limit", "-l", default=10, help="Number of stats to show")
def query_stats(limit: int) -> None:
    """Show user statistics (games played, wins, etc.)."""
    from scribbl_py.storage.db.auth_models import UserStatsModel

    with get_sync_session() as session:
        stmt = (
            select(UserStatsModel)
            .options(joinedload(UserStatsModel.user))
            .order_by(UserStatsModel.games_won.desc())
            .limit(limit)
        )
        result = session.execute(stmt)
        stats_list = result.scalars().unique().all()

        table = Table(title=f"User Stats (top {len(stats_list)} by wins)")
        table.add_column("Username", style="cyan")
        table.add_column("Games", style="green", justify="right")
        table.add_column("Wins", style="yellow", justify="right")
        table.add_column("Win %", style="magenta", justify="right")
        table.add_column("Guesses", style="blue", justify="right")
        table.add_column("Correct", style="green", justify="right")
        table.add_column("Accuracy", style="cyan", justify="right")

        for stats in stats_list:
            win_rate = f"{(stats.games_won / stats.games_played * 100):.1f}%" if stats.games_played > 0 else "-"
            accuracy = f"{(stats.correct_guesses / stats.total_guesses * 100):.1f}%" if stats.total_guesses > 0 else "-"
            username = stats.user.username if stats.user else "Unknown"

            table.add_row(
                username,
                str(stats.games_played),
                str(stats.games_won),
                win_rate,
                str(stats.total_guesses),
                str(stats.correct_guesses),
                accuracy,
            )

        console.print(table)


@query_group.command(name="sessions", help="List user sessions.")
@click.option("--limit", "-l", default=20, help="Number of sessions to show")
@click.option("--active", "-a", is_flag=True, help="Show only active (non-expired) sessions")
def query_sessions(limit: int, active: bool) -> None:
    """List user sessions."""
    from datetime import UTC, datetime

    from scribbl_py.storage.db.auth_models import SessionModel

    with get_sync_session() as session:
        stmt = (
            select(SessionModel)
            .options(joinedload(SessionModel.user))
            .order_by(SessionModel.created_at.desc())
            .limit(limit)
        )
        if active:
            stmt = stmt.where(SessionModel.expires_at > datetime.now(UTC))

        result = session.execute(stmt)
        sessions = result.scalars().unique().all()

        table = Table(title=f"Sessions (showing {len(sessions)})")
        table.add_column("Token", style="dim")
        table.add_column("User", style="cyan")
        table.add_column("Created", style="green")
        table.add_column("Expires", style="yellow")
        table.add_column("Status", style="magenta")

        now = datetime.now(UTC)
        for sess in sessions:
            is_expired = sess.expires_at < now if sess.expires_at else True
            status = "[red]Expired[/red]" if is_expired else "[green]Active[/green]"
            username = sess.user.username if sess.user else "Guest"

            table.add_row(
                sess.session_token[:12] + "...",
                username,
                sess.created_at.strftime("%Y-%m-%d %H:%M") if sess.created_at else "-",
                sess.expires_at.strftime("%Y-%m-%d %H:%M") if sess.expires_at else "-",
                status,
            )

        console.print(table)


@query_group.command(name="leaderboard", help="Show the leaderboard.")
@click.option("--by", "-b", type=click.Choice(["wins", "games", "accuracy"]), default="wins", help="Sort by field")
@click.option("--limit", "-l", default=10, help="Number of entries to show")
def query_leaderboard(by: str, limit: int) -> None:
    """Show the leaderboard."""
    from scribbl_py.storage.db.auth_models import UserStatsModel

    with get_sync_session() as session:
        stmt = select(UserStatsModel).options(joinedload(UserStatsModel.user))

        if by == "wins":
            stmt = stmt.order_by(UserStatsModel.games_won.desc())
        elif by == "games":
            stmt = stmt.order_by(UserStatsModel.games_played.desc())

        stmt = stmt.limit(limit * 2 if by == "accuracy" else limit)
        result = session.execute(stmt)
        stats_list = list(result.scalars().unique().all())

        if by == "accuracy":

            def get_accuracy(s):
                if s.total_guesses == 0:
                    return 0
                return s.correct_guesses / s.total_guesses

            stats_list.sort(key=get_accuracy, reverse=True)
            stats_list = stats_list[:limit]

        title_map = {
            "wins": "Leaderboard (by Wins)",
            "games": "Leaderboard (by Games Played)",
            "accuracy": "Leaderboard (by Guess Accuracy)",
        }
        table = Table(title=title_map[by])
        table.add_column("#", style="dim", justify="right")
        table.add_column("Username", style="cyan")
        table.add_column("Games", style="green", justify="right")
        table.add_column("Wins", style="yellow", justify="right")
        table.add_column("Accuracy", style="magenta", justify="right")
        table.add_column("Avg Time", style="blue", justify="right")

        for i, stats in enumerate(stats_list, 1):
            accuracy = f"{(stats.correct_guesses / stats.total_guesses * 100):.1f}%" if stats.total_guesses > 0 else "-"
            avg_time = (
                f"{stats.total_guess_time_ms / stats.correct_guesses / 1000:.1f}s"
                if stats.correct_guesses > 0 and stats.total_guess_time_ms
                else "-"
            )
            username = stats.user.username if stats.user else "Unknown"
            rank_style = "bold yellow" if i == 1 else "bold white" if i <= 3 else ""

            table.add_row(
                f"[{rank_style}]{i}[/{rank_style}]" if rank_style else str(i),
                f"[{rank_style}]{username}[/{rank_style}]" if rank_style else username,
                str(stats.games_played),
                str(stats.games_won),
                accuracy,
                avg_time,
            )

        console.print(table)


@query_group.command(name="tables", help="List all database tables and row counts.")
def query_tables() -> None:
    """List all database tables and row counts."""
    url = get_database_url()
    engine = create_engine(url)

    inspector = inspect(engine)
    tables_list = inspector.get_table_names()

    table = Table(title="Database Tables")
    table.add_column("Table", style="cyan")
    table.add_column("Rows", style="green", justify="right")

    with engine.connect() as conn:
        for table_name in sorted(tables_list):
            try:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                count = result.scalar()
            except Exception:
                count = "?"

            table.add_row(table_name, str(count))

    console.print(table)


@query_group.command(name="sql", help="Execute raw SQL query (SELECT only).")
@click.argument("query")
@click.option("--limit", "-l", default=50, help="Limit results")
def query_sql(query: str, limit: int) -> None:
    """Execute raw SQL query (SELECT only)."""
    # Security: only allow SELECT queries
    if not query.strip().upper().startswith("SELECT"):
        console.print("[red]Error: Only SELECT queries are allowed[/red]")
        return

    url = get_database_url()
    engine = create_engine(url)

    with engine.connect() as conn:
        try:
            # Add LIMIT if not present
            if "LIMIT" not in query.upper():
                full_query = f"{query} LIMIT {limit}"
            else:
                full_query = query

            result = conn.execute(text(full_query))
            rows = result.fetchall()
            columns = result.keys()

            table = Table(title=f"Query Results ({len(rows)} rows)")
            for col in columns:
                table.add_column(str(col), style="cyan")

            for row in rows:
                table.add_row(*[str(v) if v is not None else "-" for v in row])

            console.print(table)

        except Exception as e:
            console.print(f"[red]Query error: {e}[/red]")


# ============================================================================
# Task Queue CLI Commands
# ============================================================================


@click.group(name="tasks", help="Manage background task queue (Huey).")
def tasks_group() -> None:
    """Manage background task queue (Huey)."""


@tasks_group.command(name="run", help="Start the Huey task consumer.")
@click.option("--workers", "-w", default=2, help="Number of worker threads")
@click.option("--periodic/--no-periodic", default=True, help="Enable periodic tasks")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def tasks_run(workers: int, periodic: bool, verbose: bool) -> None:
    """Start the Huey task consumer to process background tasks."""
    try:
        from huey.consumer import Consumer

        from scribbl_py.core.tasks import get_huey, register_tasks

        huey = get_huey()

        # Register periodic tasks
        if periodic:
            register_tasks()
            console.print("[green]Registered periodic tasks[/green]")

        console.print(f"[cyan]Starting Huey consumer with {workers} workers...[/cyan]")
        console.print("[dim]Press Ctrl+C to stop[/dim]\n")

        consumer = Consumer(
            huey,
            workers=workers,
            periodic=periodic,
            verbose=verbose,
        )
        consumer.run()

    except ImportError:
        console.print("[red]Error: Huey is not installed.[/red]")
        console.print("Install with: [cyan]uv add scribbl-py[tasks][/cyan]")
    except KeyboardInterrupt:
        console.print("\n[yellow]Consumer stopped[/yellow]")


@tasks_group.command(name="status", help="Show task queue status.")
def tasks_status() -> None:
    """Show task queue status and pending tasks."""
    try:
        from scribbl_py.core.tasks import TaskQueueSettings, get_huey

        settings = TaskQueueSettings.from_env()

        table = Table(title="Task Queue Status")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Enabled", "[green]Yes[/green]" if settings.enabled else "[red]No[/red]")
        table.add_row("Database", settings.db_path)
        table.add_row("Immediate Mode", "[yellow]Yes[/yellow]" if settings.immediate else "No")

        console.print(table)

        if settings.enabled:
            try:
                huey = get_huey(settings)
                pending = huey.pending_count()
                scheduled = huey.scheduled_count()

                queue_table = Table(title="Queue Stats")
                queue_table.add_column("Metric", style="cyan")
                queue_table.add_column("Count", style="green", justify="right")

                queue_table.add_row("Pending Tasks", str(pending))
                queue_table.add_row("Scheduled Tasks", str(scheduled))

                console.print(queue_table)
            except Exception as e:
                console.print(f"[yellow]Could not get queue stats: {e}[/yellow]")

    except ImportError:
        console.print("[red]Error: Huey is not installed.[/red]")
        console.print("Install with: [cyan]uv add scribbl-py[tasks][/cyan]")


@tasks_group.command(name="cleanup-sessions", help="Run session cleanup task now.")
def tasks_cleanup_sessions() -> None:
    """Manually run the session cleanup task."""
    try:
        from scribbl_py.core.tasks import _run_cleanup_expired_sessions

        console.print("[cyan]Running session cleanup...[/cyan]")
        result = _run_cleanup_expired_sessions()
        console.print(f"[green]Cleanup complete:[/green] Deleted {result['deleted']} expired sessions")

    except ImportError:
        console.print("[red]Error: Huey is not installed.[/red]")
        console.print("Install with: [cyan]uv add scribbl-py[tasks][/cyan]")
    except Exception as e:
        console.print(f"[red]Cleanup failed: {e}[/red]")


@tasks_group.command(name="cleanup-canvases", help="Run canvas cleanup task now.")
@click.option("--retention-days", "-d", default=None, type=int, help="Override retention days")
def tasks_cleanup_canvases(retention_days: int | None) -> None:
    """Manually run the canvas cleanup task."""
    try:
        if retention_days is not None:
            os.environ["CANVAS_RETENTION_DAYS"] = str(retention_days)

        from scribbl_py.core.tasks import _run_cleanup_old_canvases

        console.print("[cyan]Running canvas cleanup...[/cyan]")
        result = _run_cleanup_old_canvases()
        console.print(
            f"[green]Cleanup complete:[/green] Deleted {result['deleted']} canvases "
            f"(retention: {result['retention_days']} days)"
        )

    except ImportError:
        console.print("[red]Error: Huey is not installed.[/red]")
        console.print("Install with: [cyan]uv add scribbl-py[tasks][/cyan]")
    except Exception as e:
        console.print(f"[red]Cleanup failed: {e}[/red]")


@tasks_group.command(name="reset-weekly", help="Run weekly stats reset task now.")
def tasks_reset_weekly() -> None:
    """Manually run the weekly stats reset task."""
    try:
        from scribbl_py.core.tasks import _run_reset_weekly_stats

        if not click.confirm("This will reset all win streaks. Continue?"):
            console.print("[yellow]Cancelled[/yellow]")
            return

        console.print("[cyan]Running weekly stats reset...[/cyan]")
        result = _run_reset_weekly_stats()
        console.print(f"[green]Reset complete:[/green] Reset {result['users_reset']} users")

    except ImportError:
        console.print("[red]Error: Huey is not installed.[/red]")
        console.print("Install with: [cyan]uv add scribbl-py[tasks][/cyan]")
    except Exception as e:
        console.print(f"[red]Reset failed: {e}[/red]")


@tasks_group.command(name="list", help="List registered periodic tasks.")
def tasks_list() -> None:
    """List all registered periodic tasks."""
    table = Table(title="Scheduled Tasks")
    table.add_column("Task", style="cyan")
    table.add_column("Schedule", style="green")
    table.add_column("Description", style="dim")

    # Static list of configured tasks
    tasks_info = [
        ("cleanup_expired_sessions", "Daily @ 3:00 AM", "Remove expired user sessions"),
        ("reset_weekly_stats", "Monday @ 00:00", "Reset weekly win streaks"),
        ("cleanup_old_canvases", "Daily @ 4:00 AM", "Remove abandoned canvases"),
        ("aggregate_telemetry", "Hourly", "Aggregate telemetry data"),
    ]

    for name, schedule, desc in tasks_info:
        table.add_row(name, schedule, desc)

    console.print(table)
    console.print("\n[dim]Run 'litestar tasks run' to start the task consumer[/dim]")


class ScribblCLIPlugin(CLIPluginProtocol):
    """CLI plugin that adds custom database query and task queue commands.

    Adds the `query` command group with subcommands:
    - users: List users in the database
    - stats: Show user statistics
    - sessions: List user sessions
    - leaderboard: Show the leaderboard
    - tables: List all database tables and row counts
    - sql: Execute raw SQL query (SELECT only)

    Adds the `tasks` command group with subcommands:
    - run: Start the Huey task consumer
    - status: Show task queue status
    - list: List registered periodic tasks
    - cleanup-sessions: Run session cleanup task now
    - cleanup-canvases: Run canvas cleanup task now
    - reset-weekly: Run weekly stats reset task now
    """

    def on_cli_init(self, cli: click.Group) -> None:
        """Register the query and tasks command groups."""
        cli.add_command(query_group)
        cli.add_command(tasks_group)
