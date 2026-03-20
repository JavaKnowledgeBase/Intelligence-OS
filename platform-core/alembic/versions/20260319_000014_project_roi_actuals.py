"""project roi actuals

Revision ID: 20260319_000014
Revises: 20260319_000013
Create Date: 2026-03-19 23:55:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260319_000014"
down_revision: Union[str, None] = "20260319_000013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_roi_actuals",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("project_id", sa.String(length=64), nullable=False),
        sa.Column("scenario_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("effective_revenue", sa.Float(), nullable=False),
        sa.Column("operating_expenses", sa.Float(), nullable=False),
        sa.Column("capex", sa.Float(), nullable=False, server_default="0"),
        sa.Column("debt_service", sa.Float(), nullable=False, server_default="0"),
        sa.Column("occupancy_rate", sa.Float(), nullable=True),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scenario_id"], ["project_roi_scenarios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_project_roi_actuals_project_id"), "project_roi_actuals", ["project_id"], unique=False)
    op.create_index(op.f("ix_project_roi_actuals_scenario_id"), "project_roi_actuals", ["scenario_id"], unique=False)
    op.create_index(op.f("ix_project_roi_actuals_tenant_id"), "project_roi_actuals", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_project_roi_actuals_tenant_id"), table_name="project_roi_actuals")
    op.drop_index(op.f("ix_project_roi_actuals_scenario_id"), table_name="project_roi_actuals")
    op.drop_index(op.f("ix_project_roi_actuals_project_id"), table_name="project_roi_actuals")
    op.drop_table("project_roi_actuals")
