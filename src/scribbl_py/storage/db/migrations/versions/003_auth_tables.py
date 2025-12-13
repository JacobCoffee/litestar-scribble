"""Add auth tables: users, user_stats, sessions.

Revision ID: 003_auth
Revises: 002_z_index_group
Create Date: 2025-01-01 00:00:00.000000

"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from advanced_alchemy.types import GUID, DateTimeUTC
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "003_auth"
down_revision: str | None = "002_z_index_group"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create users, user_stats, and sessions tables."""
    # Create users table
    op.create_table(
        "users",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("username", sa.String(100), nullable=False, server_default="Anonymous"),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("oauth_provider", sa.String(20), nullable=True),
        sa.Column("oauth_id", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sa_orm_sentinel", sa.Integer(), nullable=True),
        sa.Column("created_at", DateTimeUTC(), nullable=False),
        sa.Column("updated_at", DateTimeUTC(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_oauth_id", "users", ["oauth_id"])

    # Create user_stats table
    op.create_table(
        "user_stats",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("user_id", GUID(), nullable=False),
        sa.Column("games_played", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("games_won", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_score", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("correct_guesses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_guesses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_guess_time_ms", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("fastest_guess_ms", sa.Integer(), nullable=True),
        sa.Column("drawings_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("drawings_guessed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("best_game_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_win_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("best_win_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sa_orm_sentinel", sa.Integer(), nullable=True),
        sa.Column("created_at", DateTimeUTC(), nullable=False),
        sa.Column("updated_at", DateTimeUTC(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_user_stats_user_id", "user_stats", ["user_id"])

    # Create sessions table
    op.create_table(
        "sessions",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("session_token", sa.String(64), nullable=False),
        sa.Column("user_id", GUID(), nullable=True),
        sa.Column("guest_name", sa.String(100), nullable=False, server_default="Anonymous"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("sa_orm_sentinel", sa.Integer(), nullable=True),
        sa.Column("created_at", DateTimeUTC(), nullable=False),
        sa.Column("updated_at", DateTimeUTC(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("session_token"),
    )
    op.create_index("ix_sessions_session_token", "sessions", ["session_token"])
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])


def downgrade() -> None:
    """Drop users, user_stats, and sessions tables."""
    op.drop_index("ix_sessions_user_id", "sessions")
    op.drop_index("ix_sessions_session_token", "sessions")
    op.drop_table("sessions")

    op.drop_index("ix_user_stats_user_id", "user_stats")
    op.drop_table("user_stats")

    op.drop_index("ix_users_oauth_id", "users")
    op.drop_index("ix_users_email", "users")
    op.drop_table("users")
