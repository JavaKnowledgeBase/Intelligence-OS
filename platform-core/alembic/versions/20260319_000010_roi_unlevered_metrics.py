"""roi unlevered metrics

Revision ID: 20260319_000010
Revises: 20260319_000009
Create Date: 2026-03-19 22:10:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260319_000010"
down_revision: Union[str, None] = "20260319_000009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("project_roi_scenarios", sa.Column("unlevered_irr", sa.Float(), nullable=True))
    op.add_column("project_roi_scenarios", sa.Column("unlevered_npv", sa.Float(), nullable=True))
    op.add_column("project_roi_scenarios", sa.Column("unlevered_equity_multiple", sa.Float(), nullable=True))
    op.execute("UPDATE project_roi_scenarios SET unlevered_npv = projected_npv WHERE unlevered_npv IS NULL")
    op.execute("UPDATE project_roi_scenarios SET unlevered_equity_multiple = equity_multiple WHERE unlevered_equity_multiple IS NULL")


def downgrade() -> None:
    op.drop_column("project_roi_scenarios", "unlevered_equity_multiple")
    op.drop_column("project_roi_scenarios", "unlevered_npv")
    op.drop_column("project_roi_scenarios", "unlevered_irr")
