"""roi valuation metrics

Revision ID: 20260319_000012
Revises: 20260319_000011
Create Date: 2026-03-19 22:45:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260319_000012"
down_revision: Union[str, None] = "20260319_000011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("project_roi_scenarios", sa.Column("risk_free_rate", sa.Float(), nullable=False, server_default="4.25"))
    op.add_column("project_roi_scenarios", sa.Column("equity_risk_premium", sa.Float(), nullable=False, server_default="5.5"))
    op.add_column("project_roi_scenarios", sa.Column("beta", sa.Float(), nullable=False, server_default="1.1"))
    op.add_column("project_roi_scenarios", sa.Column("debt_spread", sa.Float(), nullable=False, server_default="2.0"))
    op.add_column("project_roi_scenarios", sa.Column("tax_rate", sa.Float(), nullable=False, server_default="25.0"))
    op.add_column("project_roi_scenarios", sa.Column("cost_of_equity", sa.Float(), nullable=True))
    op.add_column("project_roi_scenarios", sa.Column("pre_tax_cost_of_debt", sa.Float(), nullable=True))
    op.add_column("project_roi_scenarios", sa.Column("after_tax_cost_of_debt", sa.Float(), nullable=True))
    op.add_column("project_roi_scenarios", sa.Column("weighted_average_cost_of_capital", sa.Float(), nullable=True))
    op.add_column("project_roi_scenarios", sa.Column("average_annual_fcff", sa.Float(), nullable=True))
    op.add_column("project_roi_scenarios", sa.Column("average_annual_fcfe", sa.Float(), nullable=True))
    op.alter_column("project_roi_scenarios", "risk_free_rate", server_default=None)
    op.alter_column("project_roi_scenarios", "equity_risk_premium", server_default=None)
    op.alter_column("project_roi_scenarios", "beta", server_default=None)
    op.alter_column("project_roi_scenarios", "debt_spread", server_default=None)
    op.alter_column("project_roi_scenarios", "tax_rate", server_default=None)


def downgrade() -> None:
    op.drop_column("project_roi_scenarios", "average_annual_fcfe")
    op.drop_column("project_roi_scenarios", "average_annual_fcff")
    op.drop_column("project_roi_scenarios", "weighted_average_cost_of_capital")
    op.drop_column("project_roi_scenarios", "after_tax_cost_of_debt")
    op.drop_column("project_roi_scenarios", "pre_tax_cost_of_debt")
    op.drop_column("project_roi_scenarios", "cost_of_equity")
    op.drop_column("project_roi_scenarios", "tax_rate")
    op.drop_column("project_roi_scenarios", "debt_spread")
    op.drop_column("project_roi_scenarios", "beta")
    op.drop_column("project_roi_scenarios", "equity_risk_premium")
    op.drop_column("project_roi_scenarios", "risk_free_rate")
