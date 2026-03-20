"""roi working capital, depreciation, and fee metrics

Revision ID: 20260319_000013
Revises: 20260319_000012
Create Date: 2026-03-19 23:20:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260319_000013"
down_revision: Union[str, None] = "20260319_000012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "project_roi_scenarios",
        sa.Column("initial_working_capital", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "project_roi_scenarios",
        sa.Column("working_capital_percent_of_revenue", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "project_roi_scenarios",
        sa.Column("annual_depreciation", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "project_roi_scenarios",
        sa.Column("acquisition_fee_rate", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "project_roi_scenarios",
        sa.Column("loan_origination_fee_rate", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column("project_roi_scenarios", sa.Column("total_tax_shield", sa.Float(), nullable=True))
    op.add_column("project_roi_scenarios", sa.Column("average_working_capital_balance", sa.Float(), nullable=True))
    op.alter_column("project_roi_scenarios", "initial_working_capital", server_default=None)
    op.alter_column("project_roi_scenarios", "working_capital_percent_of_revenue", server_default=None)
    op.alter_column("project_roi_scenarios", "annual_depreciation", server_default=None)
    op.alter_column("project_roi_scenarios", "acquisition_fee_rate", server_default=None)
    op.alter_column("project_roi_scenarios", "loan_origination_fee_rate", server_default=None)


def downgrade() -> None:
    op.drop_column("project_roi_scenarios", "average_working_capital_balance")
    op.drop_column("project_roi_scenarios", "total_tax_shield")
    op.drop_column("project_roi_scenarios", "loan_origination_fee_rate")
    op.drop_column("project_roi_scenarios", "acquisition_fee_rate")
    op.drop_column("project_roi_scenarios", "annual_depreciation")
    op.drop_column("project_roi_scenarios", "working_capital_percent_of_revenue")
    op.drop_column("project_roi_scenarios", "initial_working_capital")
