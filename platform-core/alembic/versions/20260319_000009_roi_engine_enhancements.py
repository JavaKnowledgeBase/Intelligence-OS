"""roi engine enhancements

Revision ID: 20260319_000009
Revises: 20260319_000008
Create Date: 2026-03-19 21:55:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260319_000009"
down_revision: Union[str, None] = "20260319_000008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("project_roi_scenarios", sa.Column("vacancy_rate", sa.Float(), nullable=False, server_default="0"))
    op.add_column("project_roi_scenarios", sa.Column("annual_capex_reserve", sa.Float(), nullable=False, server_default="0"))
    op.add_column("project_roi_scenarios", sa.Column("interest_only_years", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("project_roi_scenarios", sa.Column("amortization_period_years", sa.Integer(), nullable=True))
    op.add_column("project_roi_scenarios", sa.Column("debt_amount", sa.Float(), nullable=True))
    op.add_column("project_roi_scenarios", sa.Column("ending_loan_balance", sa.Float(), nullable=True))
    op.add_column("project_roi_scenarios", sa.Column("sale_proceeds_after_debt", sa.Float(), nullable=True))
    op.add_column("project_roi_scenarios", sa.Column("equity_multiple", sa.Float(), nullable=True))
    op.add_column("project_roi_scenarios", sa.Column("average_cash_on_cash_return", sa.Float(), nullable=True))
    op.add_column("project_roi_scenarios", sa.Column("first_year_cash_on_cash_return", sa.Float(), nullable=True))
    op.add_column("project_roi_scenarios", sa.Column("cap_rate_on_cost", sa.Float(), nullable=True))
    op.add_column("project_roi_scenarios", sa.Column("average_dscr", sa.Float(), nullable=True))
    op.add_column("project_roi_scenarios", sa.Column("minimum_dscr", sa.Float(), nullable=True))
    op.execute("UPDATE project_roi_scenarios SET debt_amount = purchase_price * (leverage_ratio / 100.0) WHERE debt_amount IS NULL")
    op.execute("UPDATE project_roi_scenarios SET equity_multiple = cash_on_cash_multiple WHERE equity_multiple IS NULL")
    op.execute(
        """
        UPDATE project_roi_scenarios
        SET amortization_period_years = CASE
            WHEN leverage_ratio > 0 THEN 30
            ELSE hold_period_years
        END
        WHERE amortization_period_years IS NULL
        """
    )
    op.execute(
        """
        UPDATE project_roi_scenarios
        SET ending_loan_balance = 0,
            sale_proceeds_after_debt = terminal_value * (1 - (exit_cost_rate / 100.0)),
            average_cash_on_cash_return = NULL,
            first_year_cash_on_cash_return = NULL,
            cap_rate_on_cost = CASE
                WHEN purchase_price + upfront_capex > 0 THEN (net_operating_income / (purchase_price + upfront_capex)) * 100.0
                ELSE NULL
            END,
            average_dscr = NULL,
            minimum_dscr = NULL
        WHERE ending_loan_balance IS NULL
        """
    )
    op.alter_column("project_roi_scenarios", "vacancy_rate", server_default=None)
    op.alter_column("project_roi_scenarios", "annual_capex_reserve", server_default=None)
    op.alter_column("project_roi_scenarios", "interest_only_years", server_default=None)


def downgrade() -> None:
    op.drop_column("project_roi_scenarios", "minimum_dscr")
    op.drop_column("project_roi_scenarios", "average_dscr")
    op.drop_column("project_roi_scenarios", "cap_rate_on_cost")
    op.drop_column("project_roi_scenarios", "first_year_cash_on_cash_return")
    op.drop_column("project_roi_scenarios", "average_cash_on_cash_return")
    op.drop_column("project_roi_scenarios", "equity_multiple")
    op.drop_column("project_roi_scenarios", "sale_proceeds_after_debt")
    op.drop_column("project_roi_scenarios", "ending_loan_balance")
    op.drop_column("project_roi_scenarios", "debt_amount")
    op.drop_column("project_roi_scenarios", "amortization_period_years")
    op.drop_column("project_roi_scenarios", "interest_only_years")
    op.drop_column("project_roi_scenarios", "annual_capex_reserve")
    op.drop_column("project_roi_scenarios", "vacancy_rate")
