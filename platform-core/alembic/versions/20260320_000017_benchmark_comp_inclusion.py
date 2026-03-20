"""benchmark comp inclusion flag

Revision ID: 20260320_000017
Revises: 20260320_000016
Create Date: 2026-03-20 18:20:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260320_000017"
down_revision: Union[str, None] = "20260320_000016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "benchmark_comps",
        sa.Column("included", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("benchmark_comps", "included")
