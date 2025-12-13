"""SQLAlchemy models for authentication and user data."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from advanced_alchemy.base import UUIDAuditBase
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from scribbl_py.auth.models import Session, User, UserStats


class UserModel(UUIDAuditBase):
    """SQLAlchemy model for User entities."""

    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(100), default="Anonymous")
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    oauth_provider: Mapped[str | None] = mapped_column(String(20), nullable=True)
    oauth_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    stats: Mapped[UserStatsModel | None] = relationship(
        "UserStatsModel",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    sessions: Mapped[list[SessionModel]] = relationship(
        "SessionModel",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class UserStatsModel(UUIDAuditBase):
    """SQLAlchemy model for UserStats entities."""

    __tablename__ = "user_stats"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    games_played: Mapped[int] = mapped_column(Integer, default=0)
    games_won: Mapped[int] = mapped_column(Integer, default=0)
    total_score: Mapped[int] = mapped_column(BigInteger, default=0)
    correct_guesses: Mapped[int] = mapped_column(Integer, default=0)
    total_guesses: Mapped[int] = mapped_column(Integer, default=0)
    total_guess_time_ms: Mapped[int] = mapped_column(BigInteger, default=0)
    fastest_guess_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    drawings_completed: Mapped[int] = mapped_column(Integer, default=0)
    drawings_guessed: Mapped[int] = mapped_column(Integer, default=0)
    best_game_score: Mapped[int] = mapped_column(Integer, default=0)
    current_win_streak: Mapped[int] = mapped_column(Integer, default=0)
    best_win_streak: Mapped[int] = mapped_column(Integer, default=0)

    # Relationship
    user: Mapped[UserModel] = relationship("UserModel", back_populates="stats")


class SessionModel(UUIDAuditBase):
    """SQLAlchemy model for Session entities.

    Note: Uses string ID (token) as the primary lookup, but still has UUID for consistency.
    """

    __tablename__ = "sessions"

    session_token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    guest_name: Mapped[str] = mapped_column(String(100), default="Anonymous")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)  # IPv6 max length
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationship
    user: Mapped[UserModel | None] = relationship("UserModel", back_populates="sessions")


# Conversion functions
def user_to_model(user: User) -> UserModel:
    """Convert domain User to UserModel."""
    return UserModel(
        id=user.id,
        username=user.username,
        email=user.email,
        avatar_url=user.avatar_url,
        oauth_provider=user.oauth_provider.value if user.oauth_provider else None,
        oauth_id=user.oauth_id,
        is_active=user.is_active,
        is_admin=user.is_admin,
        created_at=user.created_at,
        last_login=user.last_login,
    )


def user_from_model(model: UserModel) -> User:
    """Convert UserModel to domain User."""
    from scribbl_py.auth.models import OAuthProvider, User

    return User(
        id=model.id,
        username=model.username,
        email=model.email,
        avatar_url=model.avatar_url,
        oauth_provider=OAuthProvider(model.oauth_provider) if model.oauth_provider else None,
        oauth_id=model.oauth_id,
        is_active=model.is_active,
        is_admin=model.is_admin,
        created_at=model.created_at,
        last_login=model.last_login,
    )


def stats_to_model(stats: UserStats) -> UserStatsModel:
    """Convert domain UserStats to UserStatsModel."""
    return UserStatsModel(
        user_id=stats.user_id,
        games_played=stats.games_played,
        games_won=stats.games_won,
        total_score=stats.total_score,
        correct_guesses=stats.correct_guesses,
        total_guesses=stats.total_guesses,
        total_guess_time_ms=stats.total_guess_time_ms,
        fastest_guess_ms=stats.fastest_guess_ms,
        drawings_completed=stats.drawings_completed,
        drawings_guessed=stats.drawings_guessed,
        best_game_score=stats.best_game_score,
        current_win_streak=stats.current_win_streak,
        best_win_streak=stats.best_win_streak,
        updated_at=stats.updated_at,
    )


def stats_from_model(model: UserStatsModel) -> UserStats:
    """Convert UserStatsModel to domain UserStats."""
    from scribbl_py.auth.models import UserStats

    return UserStats(
        user_id=model.user_id,
        games_played=model.games_played,
        games_won=model.games_won,
        total_score=model.total_score,
        correct_guesses=model.correct_guesses,
        total_guesses=model.total_guesses,
        total_guess_time_ms=model.total_guess_time_ms,
        fastest_guess_ms=model.fastest_guess_ms,
        drawings_completed=model.drawings_completed,
        drawings_guessed=model.drawings_guessed,
        best_game_score=model.best_game_score,
        current_win_streak=model.current_win_streak,
        best_win_streak=model.best_win_streak,
        updated_at=model.updated_at,
    )


def session_to_model(session: Session) -> SessionModel:
    """Convert domain Session to SessionModel."""
    return SessionModel(
        session_token=session.id,
        user_id=session.user_id,
        guest_name=session.guest_name,
        created_at=session.created_at,
        expires_at=session.expires_at,
        ip_address=session.ip_address,
        user_agent=session.user_agent,
    )


def session_from_model(model: SessionModel) -> Session:
    """Convert SessionModel to domain Session."""
    from scribbl_py.auth.models import Session

    return Session(
        id=model.session_token,
        user_id=model.user_id,
        guest_name=model.guest_name,
        created_at=model.created_at,
        expires_at=model.expires_at,
        ip_address=model.ip_address,
        user_agent=model.user_agent,
    )
