"""Database storage for authentication data."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import delete, select

from scribbl_py.storage.db.auth_models import (
    SessionModel,
    UserModel,
    UserStatsModel,
    session_from_model,
    session_to_model,
    stats_from_model,
    stats_to_model,
    user_from_model,
    user_to_model,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from scribbl_py.auth.models import Session, User, UserStats


class AuthDatabaseStorage:
    """Database storage for auth entities (User, Session, UserStats)."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session.

        Args:
            session: SQLAlchemy async session.
        """
        self._session = session

    # === User Operations ===

    async def create_user(self, user: User) -> User:
        """Create a new user."""
        model = user_to_model(user)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return user_from_model(model)

    async def get_user(self, user_id: UUID) -> User | None:
        """Get user by ID."""
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return user_from_model(model) if model else None

    async def get_user_by_oauth(self, provider: str, oauth_id: str) -> User | None:
        """Get user by OAuth provider and ID."""
        stmt = select(UserModel).where(
            UserModel.oauth_provider == provider,
            UserModel.oauth_id == oauth_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return user_from_model(model) if model else None

    async def get_user_by_email(self, email: str) -> User | None:
        """Get user by email."""
        stmt = select(UserModel).where(UserModel.email == email)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return user_from_model(model) if model else None

    async def update_user(self, user: User) -> User:
        """Update user data."""
        stmt = select(UserModel).where(UserModel.id == user.id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            msg = f"User {user.id} not found"
            raise ValueError(msg)

        model.username = user.username
        model.email = user.email
        model.avatar_url = user.avatar_url
        model.is_active = user.is_active
        model.is_admin = user.is_admin
        model.last_login = user.last_login

        await self._session.flush()
        await self._session.refresh(model)
        return user_from_model(model)

    async def delete_user(self, user_id: UUID) -> bool:
        """Delete user by ID."""
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return False

        await self._session.delete(model)
        await self._session.flush()
        return True

    # === Session Operations ===

    async def create_session(self, session: Session) -> Session:
        """Create a new session."""
        model = session_to_model(session)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return session_from_model(model)

    async def get_session(self, session_token: str) -> Session | None:
        """Get session by token."""
        stmt = select(SessionModel).where(SessionModel.session_token == session_token)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return session_from_model(model) if model else None

    async def delete_session(self, session_token: str) -> bool:
        """Delete session by token."""
        stmt = select(SessionModel).where(SessionModel.session_token == session_token)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return False

        await self._session.delete(model)
        await self._session.flush()
        return True

    async def delete_expired_sessions(self) -> int:
        """Delete all expired sessions.

        Returns:
            Number of sessions deleted.
        """
        now = datetime.now(UTC)
        stmt = delete(SessionModel).where(SessionModel.expires_at < now)
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount

    async def get_user_sessions(self, user_id: UUID) -> list[Session]:
        """Get all sessions for a user."""
        stmt = select(SessionModel).where(SessionModel.user_id == user_id)
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [session_from_model(m) for m in models]

    # === Stats Operations ===

    async def create_stats(self, stats: UserStats) -> UserStats:
        """Create stats for a user."""
        model = stats_to_model(stats)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return stats_from_model(model)

    async def get_stats(self, user_id: UUID) -> UserStats | None:
        """Get stats for a user."""
        stmt = select(UserStatsModel).where(UserStatsModel.user_id == user_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return stats_from_model(model) if model else None

    async def update_stats(self, stats: UserStats) -> UserStats:
        """Update user stats."""
        stmt = select(UserStatsModel).where(UserStatsModel.user_id == stats.user_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            # Create if doesn't exist
            return await self.create_stats(stats)

        model.games_played = stats.games_played
        model.games_won = stats.games_won
        model.total_score = stats.total_score
        model.correct_guesses = stats.correct_guesses
        model.total_guesses = stats.total_guesses
        model.total_guess_time_ms = stats.total_guess_time_ms
        model.fastest_guess_ms = stats.fastest_guess_ms
        model.drawings_completed = stats.drawings_completed
        model.drawings_guessed = stats.drawings_guessed
        model.best_game_score = stats.best_game_score
        model.current_win_streak = stats.current_win_streak
        model.best_win_streak = stats.best_win_streak
        model.updated_at = datetime.now(UTC)

        await self._session.flush()
        await self._session.refresh(model)
        return stats_from_model(model)

    async def get_leaderboard(
        self,
        category: str = "wins",
        limit: int = 10,
    ) -> list[tuple[User, UserStats]]:
        """Get leaderboard entries.

        Args:
            category: Leaderboard category (wins, fastest, drawer, games).
            limit: Maximum entries to return.

        Returns:
            List of (User, UserStats) tuples sorted by category.
        """
        # Build order clause based on category
        if category == "wins":
            order_by = UserStatsModel.games_won.desc()
        elif category == "fastest":
            order_by = UserStatsModel.fastest_guess_ms.asc().nullslast()
        elif category == "drawer":
            # Calculate success rate - need to handle division
            order_by = (UserStatsModel.drawings_guessed * 100 / UserStatsModel.drawings_completed).desc().nullslast()
        elif category == "games":
            order_by = UserStatsModel.games_played.desc()
        else:
            order_by = UserStatsModel.games_won.desc()

        # Join users and stats
        stmt = (
            select(UserModel, UserStatsModel)
            .join(UserStatsModel, UserModel.id == UserStatsModel.user_id)
            .where(UserStatsModel.games_played > 0)  # Only include users who have played
            .order_by(order_by)
            .limit(limit)
        )

        result = await self._session.execute(stmt)
        rows = result.all()

        return [(user_from_model(user), stats_from_model(stats)) for user, stats in rows]
