"""project roi scenarios

Revision ID: 20260319_000008
Revises: 20260319_000007
Create Date: 2026-03-19 11:10:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260319_000008"
down_revision: Union[str, None] = "20260319_000007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_roi_scenarios",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("project_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("listing_id", sa.String(length=64), nullable=True),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("scenario_type", sa.String(length=20), nullable=False),
        sa.Column("purchase_price", sa.Float(), nullable=False),
        sa.Column("upfront_capex", sa.Float(), nullable=False),
        sa.Column("annual_revenue", sa.Float(), nullable=False),
        sa.Column("annual_operating_expenses", sa.Float(), nullable=False),
        sa.Column("annual_revenue_growth_rate", sa.Float(), nullable=False),
        sa.Column("annual_expense_growth_rate", sa.Float(), nullable=False),
        sa.Column("exit_cap_rate", sa.Float(), nullable=False),
        sa.Column("exit_cost_rate", sa.Float(), nullable=False),
        sa.Column("hold_period_years", sa.Integer(), nullable=False),
        sa.Column("discount_rate", sa.Float(), nullable=False),
        sa.Column("leverage_ratio", sa.Float(), nullable=False),
        sa.Column("interest_rate", sa.Float(), nullable=False),
        sa.Column("net_operating_income", sa.Float(), nullable=False),
        sa.Column("terminal_value", sa.Float(), nullable=False),
        sa.Column("total_profit", sa.Float(), nullable=False),
        sa.Column("equity_invested", sa.Float(), nullable=False),
        sa.Column("average_annual_cash_flow", sa.Float(), nullable=False),
        sa.Column("projected_irr", sa.Float(), nullable=True),
        sa.Column("projected_npv", sa.Float(), nullable=False),
        sa.Column("cash_on_cash_multiple", sa.Float(), nullable=False),
        sa.Column("payback_period_years", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_project_roi_scenarios_listing_id"), "project_roi_scenarios", ["listing_id"], unique=False)
    op.create_index(op.f("ix_project_roi_scenarios_project_id"), "project_roi_scenarios", ["project_id"], unique=False)
    op.create_index(op.f("ix_project_roi_scenarios_tenant_id"), "project_roi_scenarios", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_project_roi_scenarios_tenant_id"), table_name="project_roi_scenarios")
    op.drop_index(op.f("ix_project_roi_scenarios_project_id"), table_name="project_roi_scenarios")
    op.drop_index(op.f("ix_project_roi_scenarios_listing_id"), table_name="project_roi_scenarios")
    op.drop_table("project_roi_scenarios")
