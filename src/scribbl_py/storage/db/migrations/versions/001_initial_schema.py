"""Initial schema for canvases and elements.

Revision ID: 001_initial
Revises:
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
revision: str = "001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create canvases and elements tables."""
    # Create canvases table
    op.create_table(
        "canvases",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False, server_default="Untitled Canvas"),
        sa.Column("width", sa.Integer(), nullable=False, server_default="1920"),
        sa.Column("height", sa.Integer(), nullable=False, server_default="1080"),
        sa.Column("background_color", sa.String(7), nullable=False, server_default="#ffffff"),
        sa.Column("sa_orm_sentinel", sa.Integer(), nullable=True),
        sa.Column("created_at", DateTimeUTC(), nullable=False),
        sa.Column("updated_at", DateTimeUTC(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create elements table
    op.create_table(
        "elements",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("canvas_id", GUID(), nullable=False),
        sa.Column("element_type", sa.String(20), nullable=False),
        sa.Column("position_x", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("position_y", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("position_pressure", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("style_data", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("element_data", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("sa_orm_sentinel", sa.Integer(), nullable=True),
        sa.Column("created_at", DateTimeUTC(), nullable=False),
        sa.Column("updated_at", DateTimeUTC(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["canvas_id"], ["canvases.id"], ondelete="CASCADE"),
    )

    # Create indexes
    op.create_index("ix_elements_canvas_id", "elements", ["canvas_id"])
    op.create_index("ix_elements_element_type", "elements", ["element_type"])


def downgrade() -> None:
    """Drop canvases and elements tables."""
    op.drop_index("ix_elements_element_type", "elements")
    op.drop_index("ix_elements_canvas_id", "elements")
    op.drop_table("elements")
    op.drop_table("canvases")
