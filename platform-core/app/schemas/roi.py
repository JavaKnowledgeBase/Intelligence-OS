from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


ScenarioKind = Literal["base", "upside", "downside", "custom"]


class RoiLeaseAssumption(BaseModel):
    """Lease-level revenue assumption used to build a rent-roll schedule."""

    tenant_name: str = Field(min_length=2, max_length=120)
    monthly_rent: float = Field(ge=0)
    leased_square_feet: float | None = Field(default=None, ge=0)
    start_month: int = Field(default=1, ge=1, le=600)
    end_month: int = Field(ge=1, le=600)
    annual_rent_growth_rate: float = Field(default=0, ge=-100, le=100)
    reimbursement_monthly: float = Field(default=0, ge=0)
    downtime_months_after_expiry: int = Field(default=0, ge=0, le=60)
    renewal_monthly_rent: float | None = Field(default=None, ge=0)
    renewal_rent_change_rate: float = Field(default=0, ge=-100, le=200)


class RoiScenarioInput(BaseModel):
    """Shared ROI scenario assumptions used for preview and persistence."""

    name: str = Field(min_length=2, max_length=80)
    scenario_type: ScenarioKind = "custom"
    listing_id: str | None = None
    lease_assumptions: list[RoiLeaseAssumption] = Field(default_factory=list)
    purchase_price: float = Field(ge=0)
    upfront_capex: float = Field(default=0, ge=0)
    annual_revenue: float = Field(ge=0)
    vacancy_rate: float = Field(default=0, ge=0, le=100)
    annual_operating_expenses: float = Field(ge=0)
    annual_capex_reserve: float = Field(default=0, ge=0)
    initial_working_capital: float = Field(default=0, ge=0)
    working_capital_percent_of_revenue: float = Field(default=0, ge=0, le=100)
    annual_depreciation: float = Field(default=0, ge=0)
    acquisition_fee_rate: float = Field(default=0, ge=0, le=25)
    loan_origination_fee_rate: float = Field(default=0, ge=0, le=10)
    annual_revenue_growth_rate: float = Field(default=0, ge=-100, le=100)
    annual_expense_growth_rate: float = Field(default=0, ge=-100, le=100)
    exit_cap_rate: float = Field(gt=0, le=100)
    exit_cost_rate: float = Field(default=2, ge=0, le=100)
    hold_period_years: int = Field(ge=1, le=20)
    discount_rate: float = Field(default=12, ge=0, le=100)
    risk_free_rate: float = Field(default=4.25, ge=0, le=25)
    equity_risk_premium: float = Field(default=5.5, ge=0, le=25)
    beta: float = Field(default=1.1, ge=0, le=5)
    debt_spread: float = Field(default=2.0, ge=0, le=20)
    tax_rate: float = Field(default=25.0, ge=0, le=60)
    leverage_ratio: float = Field(default=0, ge=0, le=90)
    interest_rate: float = Field(default=0, ge=0, le=100)
    interest_only_years: int = Field(default=0, ge=0, le=10)
    amortization_period_years: int | None = Field(default=None, ge=1, le=40)


class RoiScenarioCreate(RoiScenarioInput):
    """Payload for creating a saved ROI scenario."""


class RoiScenarioUpdate(RoiScenarioInput):
    """Payload for updating a saved ROI scenario."""


class RoiScenarioSummary(RoiScenarioInput):
    """Persisted ROI scenario with calculated outputs."""

    id: str
    project_id: str
    tenant_id: str
    net_operating_income: float
    terminal_value: float
    total_profit: float
    equity_invested: float
    debt_amount: float | None = None
    ending_loan_balance: float | None = None
    sale_proceeds_after_debt: float | None = None
    average_annual_cash_flow: float
    projected_irr: float | None = None
    projected_npv: float
    cost_of_equity: float | None = None
    pre_tax_cost_of_debt: float | None = None
    after_tax_cost_of_debt: float | None = None
    weighted_average_cost_of_capital: float | None = None
    unlevered_irr: float | None = None
    unlevered_npv: float | None = None
    total_tax_shield: float | None = None
    average_working_capital_balance: float | None = None
    cash_on_cash_multiple: float
    equity_multiple: float | None = None
    unlevered_equity_multiple: float | None = None
    average_annual_fcff: float | None = None
    average_annual_fcfe: float | None = None
    average_cash_on_cash_return: float | None = None
    first_year_cash_on_cash_return: float | None = None
    cap_rate_on_cost: float | None = None
    average_dscr: float | None = None
    minimum_dscr: float | None = None
    payback_period_years: float | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class RoiYearlyCashFlow(BaseModel):
    """Annual cash flow detail used for ROI review and auditability."""

    year: int
    effective_revenue: float
    operating_expenses: float
    net_operating_income: float
    income_tax_expense: float
    depreciation: float
    change_in_working_capital: float
    tax_shield: float
    capex_reserve: float
    interest_expense: float
    principal_paydown: float
    debt_service: float
    fcff: float
    fcfe: float
    cash_flow_before_sale: float
    net_sale_proceeds: float
    total_cash_flow: float
    discounted_cash_flow: float
    ending_loan_balance: float
    dscr: float | None = None


class RoiMonthlyCashFlow(BaseModel):
    """Monthly cash flow detail for institutional underwriting review."""

    month: int
    year: int
    effective_revenue: float
    operating_expenses: float
    net_operating_income: float
    income_tax_expense: float
    depreciation: float
    change_in_working_capital: float
    tax_shield: float
    capex_reserve: float
    interest_expense: float
    principal_paydown: float
    debt_service: float
    fcff: float
    fcfe: float
    unlevered_cash_flow: float
    levered_cash_flow: float
    net_sale_proceeds: float
    total_cash_flow: float
    discounted_cash_flow: float
    ending_loan_balance: float
    dscr: float | None = None


class RoiSensitivityPoint(BaseModel):
    """Single point in a sensitivity matrix."""

    exit_cap_rate: float
    annual_revenue_growth_rate: float
    projected_irr: float | None = None
    projected_npv: float | None = None
    equity_multiple: float | None = None


class RoiSensitivityResponse(BaseModel):
    """Sensitivity matrix for key underwriting drivers."""

    base_exit_cap_rate: float
    base_annual_revenue_growth_rate: float
    points: list[RoiSensitivityPoint]


class RoiScenarioCalculationResponse(BaseModel):
    """Ephemeral calculation preview for ROI inputs."""

    scenario: RoiScenarioSummary
    annual_cash_flows: list[RoiYearlyCashFlow]
    monthly_cash_flows: list[RoiMonthlyCashFlow]


class RoiPortfolioSnapshot(BaseModel):
    """Project-level summary across saved ROI scenarios."""

    scenario_count: int
    base_case_irr: float | None = None
    upside_case_irr: float | None = None
    downside_case_irr: float | None = None
    best_case_irr: float | None = None
    average_npv: float | None = None
    best_equity_multiple: float | None = None
    average_dscr: float | None = None
