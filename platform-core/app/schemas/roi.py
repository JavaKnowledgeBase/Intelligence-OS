from datetime import date, datetime
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


class RoiRiskFlag(BaseModel):
    """Human-readable model warning highlighting a specific weakness or concentration."""

    severity: Literal["low", "medium", "high"]
    code: str
    title: str
    detail: str


class RoiStressTestResult(BaseModel):
    """Result for a standard downside or upside stress case."""

    scenario_name: str
    scenario_key: str
    projected_irr: float | None = None
    projected_npv: float | None = None
    equity_multiple: float | None = None
    average_dscr: float | None = None
    minimum_dscr: float | None = None


class RoiValueDriverSummary(BaseModel):
    """High-level attribution and concentration summary for the scenario."""

    operating_cash_flow_present_value: float
    terminal_value_present_value: float
    terminal_value_share_of_present_value: float | None = None
    sale_proceeds_share_of_total_cash_flow: float | None = None
    tax_shield_share_of_present_value: float | None = None
    leverage_ratio: float


class RoiReturnAttribution(BaseModel):
    """Breakdown of the major sources of modeled value creation or loss."""

    operating_cash_flow_contribution: float
    sale_proceeds_contribution: float
    tax_shield_contribution: float
    leverage_contribution: float
    fee_drag_contribution: float
    working_capital_drag_contribution: float


class RoiValuationSanityCheck(BaseModel):
    """Checks that catch valuation structures which are overly dependent on fragile assumptions."""

    terminal_value_dependency: Literal["healthy", "elevated", "critical"]
    entry_cap_rate: float | None = None
    spread_to_exit_cap_rate: float | None = None
    implied_value_creation_multiple: float | None = None
    notes: list[str]


class RoiQualityOfEarningsCheck(BaseModel):
    """Simple underwriting-forensics checks for revenue and earnings quality."""

    revenue_quality: Literal["strong", "moderate", "weak"]
    earnings_quality: Literal["strong", "moderate", "weak"]
    revenue_concentration_risk: Literal["low", "medium", "high"]
    notes: list[str]


class RoiExecutionRiskCheck(BaseModel):
    """Operational and integration-style fragility checks."""

    execution_risk: Literal["low", "medium", "high"]
    lease_rollover_risk: Literal["low", "medium", "high"]
    downside_case_reliance: Literal["low", "medium", "high"]
    notes: list[str]


class RoiGovernanceRiskCheck(BaseModel):
    """Business-model and governance-style fragility indicators inferred from the scenario structure."""

    governance_risk: Literal["low", "medium", "high"]
    model_complexity_risk: Literal["low", "medium", "high"]
    leverage_discipline: Literal["strong", "moderate", "weak"]
    notes: list[str]


class RoiBenchmarkMetricComparison(BaseModel):
    """Comparison of a modeled metric against a benchmark range."""

    metric: str
    actual: float | None = None
    benchmark_min: float | None = None
    benchmark_max: float | None = None
    status: Literal["below", "within", "above", "unavailable"]
    note: str


class RoiBenchmarkAssessment(BaseModel):
    """Sector-profile comparison using configurable benchmark ranges."""

    benchmark_profile: str
    overall_assessment: Literal["outperform", "mixed", "underperform"]
    confidence: Literal["low", "medium", "high"]
    metrics: list[RoiBenchmarkMetricComparison]
    notes: list[str]


class RoiBenchmarkCompCreate(BaseModel):
    """Manual or imported comparable transaction/performance record used for calibration."""

    asset_class: str
    location: str
    source_name: str = Field(min_length=2, max_length=120)
    closed_on: date | None = None
    sale_price: float = Field(ge=0)
    net_operating_income: float | None = Field(default=None, ge=0)
    cap_rate: float | None = Field(default=None, ge=0, le=100)
    projected_irr: float | None = Field(default=None, ge=0, le=100)
    equity_multiple: float | None = Field(default=None, ge=0)
    average_dscr: float | None = Field(default=None, ge=0)
    occupancy_rate: float | None = Field(default=None, ge=0, le=100)
    leverage_ratio: float | None = Field(default=None, ge=0, le=100)
    note: str = Field(default="", max_length=400)


class RoiBenchmarkCompSummary(RoiBenchmarkCompCreate):
    """Saved benchmark comparable used by calibration and benchmarking."""

    id: str
    tenant_id: str
    created_at: datetime | None = None


class RoiBenchmarkCalibrationResponse(BaseModel):
    """Calibrated benchmark ranges derived from available comparable records."""

    benchmark_profile: str
    comp_count: int
    source_mode: Literal["external_comps", "default_profile"]
    metrics: list[RoiBenchmarkMetricComparison]
    notes: list[str]


class RoiMonteCarloSummary(BaseModel):
    """Probabilistic return summary across simulated downside and upside paths."""

    simulation_count: int
    mean_projected_irr: float | None = None
    median_projected_irr: float | None = None
    downside_irr_5th_percentile: float | None = None
    upside_irr_95th_percentile: float | None = None
    mean_projected_npv: float | None = None
    downside_npv_5th_percentile: float | None = None
    upside_npv_95th_percentile: float | None = None
    mean_equity_multiple: float | None = None
    probability_negative_irr: float | None = None
    probability_negative_npv: float | None = None
    probability_dscr_below_one: float | None = None
    probability_equity_multiple_below_one: float | None = None
    expected_shortfall_npv: float | None = None
    stressed_regime_probability: float | None = None


class RoiScenarioAnalysis(BaseModel):
    """Analytical overlay used to explain quality and fragility of the modeled returns."""

    return_attribution: RoiReturnAttribution
    value_driver_summary: RoiValueDriverSummary
    valuation_sanity: RoiValuationSanityCheck
    quality_of_earnings: RoiQualityOfEarningsCheck
    execution_risk: RoiExecutionRiskCheck
    governance_risk: RoiGovernanceRiskCheck
    benchmark_assessment: RoiBenchmarkAssessment
    risk_flags: list[RoiRiskFlag]
    stress_tests: list[RoiStressTestResult]
    monte_carlo: RoiMonteCarloSummary
    risk_adjusted_score: float | None = None


class RoiRecommendationSummary(BaseModel):
    """Decision-oriented recommendation derived from the scenario analysis."""

    recommendation: Literal["invest", "watch", "reject"]
    conviction: Literal["low", "medium", "high"]
    score: float
    rationale: list[str]
    required_assumption_checks: list[str]
    action_items: list[str] = []


class RoiScenarioRankingItem(BaseModel):
    """Project-level ranking row for comparing saved ROI scenarios by risk-adjusted quality."""

    scenario_id: str
    scenario_name: str
    scenario_type: ScenarioKind
    projected_irr: float | None = None
    projected_npv: float | None = None
    equity_multiple: float | None = None
    risk_adjusted_score: float
    recommendation: Literal["invest", "watch", "reject"] | None = None
    probability_negative_npv: float | None = None
    probability_dscr_below_one: float | None = None


class RoiScenarioRecommendation(BaseModel):
    scenario_id: str
    project_id: str
    tenant_id: str
    created_by: str
    created_at: datetime
    recommendation: RoiRecommendationSummary


class RoiActualCreate(BaseModel):
    """Persisted realized monthly operating results tied to an ROI scenario."""

    period_start: date
    effective_revenue: float = Field(ge=0)
    operating_expenses: float = Field(ge=0)
    capex: float = Field(default=0, ge=0)
    debt_service: float = Field(default=0, ge=0)
    occupancy_rate: float | None = Field(default=None, ge=0, le=100)
    note: str = Field(default="", max_length=400)


class RoiActualSummary(RoiActualCreate):
    """Saved realized monthly result for variance analysis."""

    id: str
    project_id: str
    tenant_id: str
    scenario_id: str
    created_at: datetime | None = None


class RoiVariancePeriod(BaseModel):
    """Comparison of realized and underwritten monthly performance."""

    period_start: date
    month_index: int
    actual_revenue: float
    expected_revenue: float
    revenue_variance: float
    actual_operating_expenses: float
    expected_operating_expenses: float
    expense_variance: float
    actual_noi: float
    expected_noi: float
    noi_variance: float
    actual_debt_service: float
    expected_debt_service: float
    debt_service_variance: float
    actual_occupancy_rate: float | None = None
    expected_occupancy_rate: float | None = None
    occupancy_variance: float | None = None


class RoiVarianceAnalysis(BaseModel):
    """Aggregate realized-vs-underwritten drift analysis for a scenario."""

    periods: list[RoiVariancePeriod]
    total_revenue_variance: float
    total_expense_variance: float
    total_noi_variance: float
    average_occupancy_variance: float | None = None
    variance_summary: list[str]


class RoiScenarioCalculationResponse(BaseModel):
    """Ephemeral calculation preview for ROI inputs."""

    scenario: RoiScenarioSummary
    annual_cash_flows: list[RoiYearlyCashFlow]
    monthly_cash_flows: list[RoiMonthlyCashFlow]
    analysis: RoiScenarioAnalysis
    recommendation: RoiRecommendationSummary


class RoiScenarioAnalysisResponse(BaseModel):
    """Standalone ROI analysis payload for a project scenario input."""

    scenario: RoiScenarioSummary
    analysis: RoiScenarioAnalysis
    recommendation: RoiRecommendationSummary


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
    best_risk_adjusted_scenario_id: str | None = None
    best_risk_adjusted_scenario_name: str | None = None
    best_risk_adjusted_score: float | None = None
    scenario_rankings: list[RoiScenarioRankingItem] = Field(default_factory=list)
