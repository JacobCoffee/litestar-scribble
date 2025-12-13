"""Add z_index and group_id to elements.

Revision ID: 002_z_index_group
Revises: 001_initial
Create Date: 2025-01-01 00:00:00.000000

"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from advanced_alchemy.types import GUID
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "002_z_index_group"
down_revision: str | None = "001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add z_index and group_id columns to elements table.

    Uses batch mode for SQLite compatibility since SQLite doesn't support
    ALTER for adding constraints directly.
    """
    with op.batch_alter_table("elements", schema=None) as batch_op:
        # Add z_index column
        batch_op.add_column(
            sa.Column("z_index", sa.Integer(), nullable=False, server_default="0"),
        )
        # Add group_id column with self-referencing foreign key
        batch_op.add_column(
            sa.Column("group_id", GUID(), nullable=True),
        )
        batch_op.create_index("ix_elements_z_index", ["z_index"])
        batch_op.create_foreign_key(
            "fk_elements_group_id",
            "elements",
            ["group_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    """Remove z_index and group_id columns from elements table."""
    with op.batch_alter_table("elements", schema=None) as batch_op:
        batch_op.drop_constraint("fk_elements_group_id", type_="foreignkey")
        batch_op.drop_index("ix_elements_z_index")
        batch_op.drop_column("group_id")
        batch_op.drop_column("z_index")
