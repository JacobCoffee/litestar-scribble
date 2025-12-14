"""Add visible and locked columns to elements table.

Revision ID: 004_layer_state
Revises: 003_auth
Create Date: 2025-01-01 00:00:00.000000

"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "004_layer_state"
down_revision: str | None = "003_auth"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add visible and locked columns to elements table."""
    # SQLite requires batch mode for ALTER TABLE operations
    with op.batch_alter_table("elements", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("visible", sa.Boolean(), nullable=False, server_default="1")
        )
        batch_op.add_column(
            sa.Column("locked", sa.Boolean(), nullable=False, server_default="0")
        )


def downgrade() -> None:
    """Remove visible and locked columns from elements table."""
    with op.batch_alter_table("elements", schema=None) as batch_op:
        batch_op.drop_column("locked")
        batch_op.drop_column("visible")
