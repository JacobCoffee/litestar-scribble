"""Database setup and configuration for SQLite/PostgreSQL."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine


def get_database_url() -> str:
    """Get database URL from environment or default to SQLite.

    Environment variable: DATABASE_URL

    Examples:
        - sqlite+aiosqlite:///./data/scribbl.db (SQLite)
        - postgresql+asyncpg://user:pass@localhost/scribbl (PostgreSQL)

    Returns:
        Database URL string.
    """
    url = os.environ.get("DATABASE_URL", "")

    if not url:
        # Default to SQLite in data directory
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        return f"sqlite+aiosqlite:///{data_dir}/scribbl.db"

    # Handle SQLite URLs
    if url.startswith("sqlite:///"):
        # Convert to async SQLite
        return url.replace("sqlite:///", "sqlite+aiosqlite:///")

    # Handle PostgreSQL URLs
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://")
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://")

    return url


def create_database_engine(url: str | None = None) -> AsyncEngine:
    """Create async database engine.

    Args:
        url: Database URL. If None, uses get_database_url().

    Returns:
        Configured AsyncEngine.
    """
    database_url = url or get_database_url()

    # SQLite-specific settings
    connect_args = {}
    if "sqlite" in database_url:
        connect_args["check_same_thread"] = False

    engine = create_async_engine(
        database_url,
        echo=os.environ.get("DATABASE_ECHO", "").lower() == "true",
        connect_args=connect_args,
    )

    # Enable foreign keys for SQLite
    if "sqlite" in database_url:

        @event.listens_for(engine.sync_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


async def create_tables(engine: AsyncEngine) -> None:
    """Create all database tables.

    Args:
        engine: The database engine.
    """
    from advanced_alchemy.base import UUIDAuditBase

    # Import all models to register them
    from scribbl_py.storage.db.auth_models import SessionModel, UserModel, UserStatsModel  # noqa: F401
    from scribbl_py.storage.db.models import CanvasModel, ElementModel  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(UUIDAuditBase.metadata.create_all)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create async session factory.

    Args:
        engine: The database engine.

    Returns:
        Session factory for creating database sessions.
    """
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


class DatabaseManager:
    """Manages database connections and sessions.

    Usage:
        db = DatabaseManager()
        await db.init()

        async with db.session() as session:
            # use session

        await db.close()
    """

    def __init__(self, url: str | None = None) -> None:
        """Initialize database manager.

        Args:
            url: Database URL. If None, uses environment variable or SQLite default.
        """
        self._url = url
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    async def init(self) -> None:
        """Initialize the database engine and create tables."""
        self._engine = create_database_engine(self._url)
        self._session_factory = create_session_factory(self._engine)
        await create_tables(self._engine)

    async def close(self) -> None:
        """Close database connections."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None

    @property
    def engine(self) -> AsyncEngine:
        """Get the database engine."""
        if self._engine is None:
            msg = "Database not initialized. Call init() first."
            raise RuntimeError(msg)
        return self._engine

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session context manager.

        Yields:
            AsyncSession for database operations.

        Raises:
            RuntimeError: If database not initialized.
        """
        if self._session_factory is None:
            msg = "Database not initialized. Call init() first."
            raise RuntimeError(msg)

        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise


# Global database manager instance
_db_manager: DatabaseManager | None = None


async def get_db_manager() -> DatabaseManager:
    """Get or create the global database manager.

    Returns:
        Initialized DatabaseManager instance.
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
        await _db_manager.init()
    return _db_manager


async def close_db_manager() -> None:
    """Close the global database manager."""
    global _db_manager
    if _db_manager is not None:
        await _db_manager.close()
        _db_manager = None
