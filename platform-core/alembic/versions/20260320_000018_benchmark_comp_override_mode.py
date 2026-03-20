"""benchmark comp override mode

Revision ID: 20260320_000018
Revises: 20260320_000017
Create Date: 2026-03-20 18:45:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260320_000018"
down_revision: Union[str, None] = "20260320_000017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "benchmark_comps",
        sa.Column("override_mode", sa.String(length=40), nullable=False, server_default="normal"),
    )


def downgrade() -> None:
    op.drop_column("benchmark_comps", "override_mode")
