"""roi lease assumptions

Revision ID: 20260319_000011
Revises: 20260319_000010
Create Date: 2026-03-19 22:25:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260319_000011"
down_revision: Union[str, None] = "20260319_000010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "project_roi_scenarios",
        sa.Column("lease_assumptions", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.alter_column("project_roi_scenarios", "lease_assumptions", server_default=None)


def downgrade() -> None:
    op.drop_column("project_roi_scenarios", "lease_assumptions")
