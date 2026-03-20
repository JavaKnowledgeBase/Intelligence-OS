from __future__ import annotations

from datetime import UTC, date, datetime

from dataclasses import dataclass
from hashlib import md5
from math import isfinite
from random import Random

from app.schemas.roi import (
    RoiBenchmarkAssessment,
    RoiBenchmarkCalibrationResponse,
    RoiBenchmarkCompSummary,
    RoiBenchmarkMetricComparison,
    RoiExecutionRiskCheck,
    RoiGovernanceRiskCheck,
    RoiMonteCarloSummary,
    RoiRecommendationSummary,
    RoiRiskFlag,
    RoiMonthlyCashFlow,
    RoiQualityOfEarningsCheck,
    RoiReturnAttribution,
    RoiScenarioAnalysis,
    RoiScenarioRankingItem,
    RoiStressTestResult,
    RoiScenarioInput,
    RoiScenarioSummary,
    RoiSensitivityPoint,
    RoiSensitivityResponse,
    RoiValuationSanityCheck,
    RoiValueDriverSummary,
    RoiYearlyCashFlow,
)


@dataclass
class RoiComputation:
    net_operating_income: float
    terminal_value: float
    total_profit: float
    equity_invested: float
    debt_amount: float
    ending_loan_balance: float
    sale_proceeds_after_debt: float
    average_annual_cash_flow: float
    projected_irr: float | None
    projected_npv: float
    cost_of_equity: float
    pre_tax_cost_of_debt: float
    after_tax_cost_of_debt: float
    weighted_average_cost_of_capital: float
    unlevered_irr: float | None
    unlevered_npv: float
    total_tax_shield: float
    average_working_capital_balance: float
    cash_on_cash_multiple: float
    equity_multiple: float
    unlevered_equity_multiple: float
    average_annual_fcff: float
    average_annual_fcfe: float
    average_cash_on_cash_return: float | None
    first_year_cash_on_cash_return: float | None
    cap_rate_on_cost: float | None
    average_dscr: float | None
    minimum_dscr: float | None
    payback_period_years: float | None
    annual_cash_flows: list[RoiYearlyCashFlow]
    monthly_cash_flows: list[RoiMonthlyCashFlow]


class RoiAnalysisService:
    """Institutional-style ROI engine with monthly underwriting, FCFF/FCFE, and sensitivity analysis."""

    BENCHMARK_PROFILES = {
        "general": {
            "projected_irr": (12.0, 20.0),
            "equity_multiple": (1.5, 2.5),
            "average_dscr": (1.2, 1.8),
            "leverage_ratio": (45.0, 65.0),
            "vacancy_rate": (3.0, 8.0),
            "terminal_value_share_of_present_value": (0.0, 55.0),
        },
        "real-estate": {
            "projected_irr": (14.0, 22.0),
            "equity_multiple": (1.7, 2.8),
            "average_dscr": (1.25, 1.9),
            "leverage_ratio": (50.0, 70.0),
            "vacancy_rate": (2.0, 7.0),
            "terminal_value_share_of_present_value": (0.0, 60.0),
        },
        "franchise": {
            "projected_irr": (16.0, 24.0),
            "equity_multiple": (1.8, 3.0),
            "average_dscr": (1.3, 2.0),
            "leverage_ratio": (40.0, 60.0),
            "vacancy_rate": (0.0, 5.0),
            "terminal_value_share_of_present_value": (0.0, 50.0),
        },
        "business": {
            "projected_irr": (15.0, 25.0),
            "equity_multiple": (1.8, 3.2),
            "average_dscr": (1.25, 2.0),
            "leverage_ratio": (35.0, 60.0),
            "vacancy_rate": (0.0, 4.0),
            "terminal_value_share_of_present_value": (0.0, 45.0),
        },
    }

    def calculate(self, payload: RoiScenarioInput) -> RoiComputation:
        months = payload.hold_period_years * 12
        monthly_revenue_growth = (1 + (payload.annual_revenue_growth_rate / 100)) ** (1 / 12) - 1
        monthly_expense_growth = (1 + (payload.annual_expense_growth_rate / 100)) ** (1 / 12) - 1
        vacancy_rate = payload.vacancy_rate / 100
        exit_cap_rate = payload.exit_cap_rate / 100
        exit_cost_rate = payload.exit_cost_rate / 100
        leverage_ratio = payload.leverage_ratio / 100
        tax_rate = payload.tax_rate / 100

        cost_of_equity = payload.risk_free_rate + (payload.beta * payload.equity_risk_premium)
        pre_tax_cost_of_debt = payload.risk_free_rate + payload.debt_spread
        after_tax_cost_of_debt = pre_tax_cost_of_debt * (1 - tax_rate)
        weighted_average_cost_of_capital = (cost_of_equity * (1 - leverage_ratio)) + (after_tax_cost_of_debt * leverage_ratio)
        monthly_cost_of_equity = (1 + (cost_of_equity / 100)) ** (1 / 12) - 1
        monthly_wacc = (1 + (weighted_average_cost_of_capital / 100)) ** (1 / 12) - 1

        debt_amount = round(payload.purchase_price * leverage_ratio, 2)
        acquisition_fees = payload.purchase_price * (payload.acquisition_fee_rate / 100)
        loan_origination_fees = debt_amount * (payload.loan_origination_fee_rate / 100)
        gross_investment = payload.purchase_price + payload.upfront_capex + acquisition_fees + loan_origination_fees
        total_initial_uses = gross_investment + payload.initial_working_capital
        equity_invested = round(max(total_initial_uses - debt_amount, 0), 2)
        amortization_years = payload.amortization_period_years or (30 if debt_amount > 0 else payload.hold_period_years)
        coupon_rate = payload.interest_rate / 100
        monthly_interest_rate = coupon_rate / 12
        monthly_payment = self._payment(debt_amount, monthly_interest_rate, amortization_years * 12) if debt_amount > 0 else 0.0

        monthly_cash_flows: list[RoiMonthlyCashFlow] = []
        fcff_series = [-round(total_initial_uses, 2)]
        fcfe_series = [-equity_invested]
        loan_balance = debt_amount

        monthly_revenues = self._build_monthly_revenue_schedule(payload, months, monthly_revenue_growth)
        monthly_operating_expenses = payload.annual_operating_expenses / 12
        monthly_capex_reserve = payload.annual_capex_reserve / 12
        monthly_depreciation = payload.annual_depreciation / 12
        dscr_values: list[float] = []
        working_capital_rate = payload.working_capital_percent_of_revenue / 100
        prior_working_capital_balance = payload.initial_working_capital
        working_capital_balances: list[float] = []
        tax_shield_total = 0.0

        for month in range(1, months + 1):
            year = ((month - 1) // 12) + 1
            effective_revenue = monthly_revenues[month - 1] * (1 - vacancy_rate)
            net_operating_income = effective_revenue - monthly_operating_expenses
            working_capital_balance = effective_revenue * working_capital_rate
            change_in_working_capital = working_capital_balance - prior_working_capital_balance
            prior_working_capital_balance = working_capital_balance

            if debt_amount > 0:
                if month <= payload.interest_only_years * 12:
                    interest_expense = loan_balance * monthly_interest_rate
                    principal_paydown = 0.0
                    debt_service = interest_expense
                else:
                    interest_expense = loan_balance * monthly_interest_rate
                    debt_service = monthly_payment
                    principal_paydown = max(min(debt_service - interest_expense, loan_balance), 0.0)
                    if debt_service < interest_expense:
                        debt_service = interest_expense
                        principal_paydown = 0.0
                loan_balance = max(loan_balance - principal_paydown, 0.0)
            else:
                interest_expense = 0.0
                principal_paydown = 0.0
                debt_service = 0.0

            taxable_operating_income = max(net_operating_income - monthly_depreciation, 0.0)
            income_tax_expense = taxable_operating_income * tax_rate
            equity_taxable_income = max(net_operating_income - monthly_depreciation - interest_expense, 0.0)
            equity_tax_expense = equity_taxable_income * tax_rate
            depreciation_tax_shield = monthly_depreciation * tax_rate
            interest_tax_shield = interest_expense * tax_rate
            tax_shield = depreciation_tax_shield + interest_tax_shield

            fcff = net_operating_income - income_tax_expense + monthly_depreciation - monthly_capex_reserve - change_in_working_capital
            fcfe = fcff - (interest_expense * (1 - tax_rate)) - principal_paydown
            unlevered_cash_flow = fcff
            levered_cash_flow = fcfe
            dscr = (net_operating_income / debt_service) if debt_service > 0 else None
            if dscr is not None and isfinite(dscr):
                dscr_values.append(dscr)

            net_sale_proceeds = 0.0
            total_cash_flow = levered_cash_flow
            if month == months:
                next_month_revenue = self._project_next_month_revenue(payload, monthly_revenues, monthly_revenue_growth)
                next_month_expenses = monthly_operating_expenses * (1 + monthly_expense_growth)
                stabilized_noi = (next_month_revenue * (1 - vacancy_rate) - next_month_expenses) * 12
                terminal_value = max(stabilized_noi / exit_cap_rate, 0) if exit_cap_rate > 0 else 0
                gross_sale_proceeds = max(terminal_value * (1 - exit_cost_rate), 0)
                net_sale_proceeds = max(gross_sale_proceeds - loan_balance, 0)
                total_cash_flow += net_sale_proceeds
                fcff += gross_sale_proceeds + working_capital_balance
                fcfe += net_sale_proceeds + working_capital_balance
                sale_proceeds_after_debt = net_sale_proceeds
            else:
                terminal_value = 0.0
                sale_proceeds_after_debt = 0.0

            working_capital_balances.append(working_capital_balance)
            tax_shield_total += tax_shield
            fcff_series.append(fcff)
            fcfe_series.append(fcfe)
            monthly_cash_flows.append(
                RoiMonthlyCashFlow(
                    month=month,
                    year=year,
                    effective_revenue=round(effective_revenue, 2),
                    operating_expenses=round(monthly_operating_expenses, 2),
                    net_operating_income=round(net_operating_income, 2),
                    income_tax_expense=round(income_tax_expense, 2),
                    depreciation=round(monthly_depreciation, 2),
                    change_in_working_capital=round(change_in_working_capital, 2),
                    tax_shield=round(tax_shield, 2),
                    capex_reserve=round(monthly_capex_reserve, 2),
                    interest_expense=round(interest_expense, 2),
                    principal_paydown=round(principal_paydown, 2),
                    debt_service=round(debt_service, 2),
                    fcff=round(fcff, 2),
                    fcfe=round(fcfe, 2),
                    unlevered_cash_flow=round(unlevered_cash_flow, 2),
                    levered_cash_flow=round(levered_cash_flow, 2),
                    net_sale_proceeds=round(net_sale_proceeds, 2),
                    total_cash_flow=round(total_cash_flow, 2),
                    discounted_cash_flow=round(fcfe / ((1 + monthly_cost_of_equity) ** month), 2),
                    ending_loan_balance=round(loan_balance, 2),
                    dscr=round(dscr, 3) if dscr is not None else None,
                )
            )

            monthly_operating_expenses *= 1 + monthly_expense_growth

        annual_cash_flows = self._rollup_years(monthly_cash_flows, monthly_cost_of_equity, monthly_wacc)
        first_year_noi = annual_cash_flows[0].net_operating_income if annual_cash_flows else 0.0
        terminal_value = monthly_cash_flows[-1].net_sale_proceeds + monthly_cash_flows[-1].ending_loan_balance if monthly_cash_flows else 0.0
        sale_proceeds_after_debt = monthly_cash_flows[-1].net_sale_proceeds if monthly_cash_flows else 0.0
        total_distributions = sum(item.total_cash_flow for item in annual_cash_flows)
        total_profit = total_distributions - equity_invested
        average_annual_cash_flow = total_distributions / len(annual_cash_flows) if annual_cash_flows else 0.0
        equity_multiple = (sum(item.fcfe for item in monthly_cash_flows) / equity_invested) if equity_invested > 0 else 0.0
        unlevered_equity_multiple = (
            sum(item.fcff for item in monthly_cash_flows) / (payload.purchase_price + payload.upfront_capex)
            if (payload.purchase_price + payload.upfront_capex) > 0
            else 0.0
        )
        annual_before_sale = [item.cash_flow_before_sale for item in annual_cash_flows]
        average_cash_on_cash_return = (
            (sum(annual_before_sale) / len(annual_before_sale)) / equity_invested * 100
            if annual_before_sale and equity_invested > 0
            else None
        )
        first_year_cash_on_cash_return = (
            (annual_before_sale[0] / equity_invested) * 100 if annual_before_sale and equity_invested > 0 else None
        )
        cap_rate_on_cost = (
            (first_year_noi / (payload.purchase_price + payload.upfront_capex)) * 100
            if (payload.purchase_price + payload.upfront_capex) > 0
            else None
        )
        projected_npv = self._npv(fcfe_series, monthly_cost_of_equity)
        projected_irr = self._irr(fcfe_series)
        unlevered_npv = self._npv(fcff_series, monthly_wacc)
        unlevered_irr = self._irr(fcff_series)
        payback_period_years = self._payback_period(fcfe_series)
        average_annual_fcff = sum(item.fcff for item in annual_cash_flows) / len(annual_cash_flows) if annual_cash_flows else 0.0
        average_annual_fcfe = sum(item.fcfe for item in annual_cash_flows) / len(annual_cash_flows) if annual_cash_flows else 0.0
        average_working_capital_balance = sum(working_capital_balances) / len(working_capital_balances) if working_capital_balances else 0.0

        return RoiComputation(
            net_operating_income=round(first_year_noi, 2),
            terminal_value=round(terminal_value, 2),
            total_profit=round(total_profit, 2),
            equity_invested=round(equity_invested, 2),
            debt_amount=round(debt_amount, 2),
            ending_loan_balance=round(monthly_cash_flows[-1].ending_loan_balance if monthly_cash_flows else 0.0, 2),
            sale_proceeds_after_debt=round(sale_proceeds_after_debt, 2),
            average_annual_cash_flow=round(average_annual_cash_flow, 2),
            projected_irr=round((((1 + projected_irr) ** 12) - 1) * 100, 2) if projected_irr is not None else None,
            projected_npv=round(projected_npv, 2),
            cost_of_equity=round(cost_of_equity, 2),
            pre_tax_cost_of_debt=round(pre_tax_cost_of_debt, 2),
            after_tax_cost_of_debt=round(after_tax_cost_of_debt, 2),
            weighted_average_cost_of_capital=round(weighted_average_cost_of_capital, 2),
            unlevered_irr=round((((1 + unlevered_irr) ** 12) - 1) * 100, 2) if unlevered_irr is not None else None,
            unlevered_npv=round(unlevered_npv, 2),
            total_tax_shield=round(tax_shield_total, 2),
            average_working_capital_balance=round(average_working_capital_balance, 2),
            cash_on_cash_multiple=round(equity_multiple, 3),
            equity_multiple=round(equity_multiple, 3),
            unlevered_equity_multiple=round(unlevered_equity_multiple, 3),
            average_annual_fcff=round(average_annual_fcff, 2),
            average_annual_fcfe=round(average_annual_fcfe, 2),
            average_cash_on_cash_return=round(average_cash_on_cash_return, 2) if average_cash_on_cash_return is not None else None,
            first_year_cash_on_cash_return=round(first_year_cash_on_cash_return, 2) if first_year_cash_on_cash_return is not None else None,
            cap_rate_on_cost=round(cap_rate_on_cost, 2) if cap_rate_on_cost is not None else None,
            average_dscr=round(sum(dscr_values) / len(dscr_values), 3) if dscr_values else None,
            minimum_dscr=round(min(dscr_values), 3) if dscr_values else None,
            payback_period_years=payback_period_years,
            annual_cash_flows=annual_cash_flows,
            monthly_cash_flows=monthly_cash_flows,
        )

    def to_summary(self, *, scenario_id: str, project_id: str, tenant_id: str, payload: RoiScenarioInput) -> RoiScenarioSummary:
        computed = self.calculate(payload)
        return RoiScenarioSummary(
            id=scenario_id,
            project_id=project_id,
            tenant_id=tenant_id,
            **payload.model_dump(),
            net_operating_income=computed.net_operating_income,
            terminal_value=computed.terminal_value,
            total_profit=computed.total_profit,
            equity_invested=computed.equity_invested,
            debt_amount=computed.debt_amount,
            ending_loan_balance=computed.ending_loan_balance,
            sale_proceeds_after_debt=computed.sale_proceeds_after_debt,
            average_annual_cash_flow=computed.average_annual_cash_flow,
            projected_irr=computed.projected_irr,
            projected_npv=computed.projected_npv,
            cost_of_equity=computed.cost_of_equity,
            pre_tax_cost_of_debt=computed.pre_tax_cost_of_debt,
            after_tax_cost_of_debt=computed.after_tax_cost_of_debt,
            weighted_average_cost_of_capital=computed.weighted_average_cost_of_capital,
            unlevered_irr=computed.unlevered_irr,
            unlevered_npv=computed.unlevered_npv,
            total_tax_shield=computed.total_tax_shield,
            average_working_capital_balance=computed.average_working_capital_balance,
            cash_on_cash_multiple=computed.cash_on_cash_multiple,
            equity_multiple=computed.equity_multiple,
            unlevered_equity_multiple=computed.unlevered_equity_multiple,
            average_annual_fcff=computed.average_annual_fcff,
            average_annual_fcfe=computed.average_annual_fcfe,
            average_cash_on_cash_return=computed.average_cash_on_cash_return,
            first_year_cash_on_cash_return=computed.first_year_cash_on_cash_return,
            cap_rate_on_cost=computed.cap_rate_on_cost,
            average_dscr=computed.average_dscr,
            minimum_dscr=computed.minimum_dscr,
            payback_period_years=computed.payback_period_years,
        )

    def build_analysis(
        self,
        payload: RoiScenarioInput,
        computed: RoiComputation | None = None,
        benchmark_profile: str | None = None,
        benchmark_ranges: dict[str, tuple[float, float]] | None = None,
    ) -> RoiScenarioAnalysis:
        computed = computed or self.calculate(payload)
        return_attribution = self._build_return_attribution(payload, computed)
        value_driver_summary = self._build_value_driver_summary(payload, computed)
        valuation_sanity = self._build_valuation_sanity(payload, computed, value_driver_summary)
        quality_of_earnings = self._build_quality_of_earnings(payload, computed)
        execution_risk = self._build_execution_risk(payload, computed)
        governance_risk = self._build_governance_risk(payload, computed, value_driver_summary)
        benchmark_assessment = self._build_benchmark_assessment(
            payload,
            computed,
            value_driver_summary,
            benchmark_profile,
            benchmark_ranges,
        )
        risk_flags = self._build_risk_flags(payload, computed, value_driver_summary)
        stress_tests = self._build_stress_tests(payload)
        monte_carlo = self._build_monte_carlo_summary(payload)
        risk_adjusted_score = self._compute_risk_adjusted_score(computed, value_driver_summary, monte_carlo)
        return RoiScenarioAnalysis(
            return_attribution=return_attribution,
            value_driver_summary=value_driver_summary,
            valuation_sanity=valuation_sanity,
            quality_of_earnings=quality_of_earnings,
            execution_risk=execution_risk,
            governance_risk=governance_risk,
            benchmark_assessment=benchmark_assessment,
            risk_flags=risk_flags,
            stress_tests=stress_tests,
            monte_carlo=monte_carlo,
            risk_adjusted_score=risk_adjusted_score,
        )

    def build_recommendation(
        self,
        payload: RoiScenarioInput,
        analysis: RoiScenarioAnalysis,
        computed: RoiComputation | None = None,
    ) -> RoiRecommendationSummary:
        computed = computed or self.calculate(payload)
        score = analysis.risk_adjusted_score or 0.0
        rationale: list[str] = []
        required_assumption_checks: list[str] = []

        if computed.projected_irr is not None and computed.projected_irr >= 18:
            rationale.append(f"Projected levered IRR is {computed.projected_irr:.2f}%, which is above a typical institutional hurdle.")
        elif computed.projected_irr is not None:
            rationale.append(f"Projected levered IRR is {computed.projected_irr:.2f}%, which limits upside versus stronger opportunities.")

        if computed.minimum_dscr is not None and computed.minimum_dscr >= 1.25:
            rationale.append(f"Minimum DSCR of {computed.minimum_dscr:.2f} suggests manageable debt coverage.")
        elif computed.minimum_dscr is not None:
            rationale.append(f"Minimum DSCR of {computed.minimum_dscr:.2f} is thin and increases downside fragility.")
            required_assumption_checks.append("Validate debt sizing, amortization, and downside NOI coverage.")

        if analysis.monte_carlo.probability_negative_npv is not None and analysis.monte_carlo.probability_negative_npv <= 15:
            rationale.append("Monte Carlo downside probability for negative NPV remains relatively contained.")
        elif analysis.monte_carlo.probability_negative_npv is not None:
            rationale.append("Monte Carlo shows a meaningful probability of capital impairment.")
            required_assumption_checks.append("Pressure-test revenue, exit cap, and expense assumptions against external comps.")

        if analysis.quality_of_earnings.earnings_quality == "weak":
            required_assumption_checks.append("Perform a quality-of-earnings review before relying on the modeled NOI and growth path.")
        if analysis.execution_risk.execution_risk == "high":
            required_assumption_checks.append("Validate execution capacity, leasing timeline, and capex delivery because the model is operationally fragile.")
        if analysis.governance_risk.governance_risk == "high":
            required_assumption_checks.append("Review business-model alignment, control quality, and downside governance protections.")

        terminal_share = analysis.value_driver_summary.terminal_value_share_of_present_value or 0.0
        if terminal_share >= 55:
            required_assumption_checks.append("Confirm exit cap and terminal NOI assumptions because a large share of value comes from disposition.")
        if payload.lease_assumptions and len(payload.lease_assumptions) <= 2:
            required_assumption_checks.append("Review tenant rollover and concentration because the rent roll is highly concentrated.")
        if payload.vacancy_rate >= 10:
            required_assumption_checks.append("Verify vacancy stabilization path and leasing assumptions.")

        if (
            score >= 25
            and (analysis.monte_carlo.probability_negative_npv or 0.0) <= 20
            and ((computed.minimum_dscr or 0.0) >= 1.15 if computed.minimum_dscr is not None else True)
        ):
            recommendation = "invest"
        elif (
            score >= 5
            and (analysis.monte_carlo.probability_negative_npv or 0.0) <= 40
            and ((computed.minimum_dscr or 0.0) >= 1.0 if computed.minimum_dscr is not None else True)
        ):
            recommendation = "watch"
        else:
            recommendation = "reject"

        if recommendation == "invest" and score >= 40:
            conviction = "high"
        elif recommendation == "reject" and score <= 0:
            conviction = "high"
        elif abs(score) >= 15:
            conviction = "medium"
        else:
            conviction = "low"

        if not required_assumption_checks:
            required_assumption_checks.append("No critical model gaps surfaced from the current analysis set.")

        # Derive explicit, actionable items for analysts from risk signals.
        action_items: list[str] = []
        if analysis.risk_flags:
            for flag in analysis.risk_flags:
                action_items.append(f"{flag.severity.title()} risk flag {flag.code}: {flag.detail}")
        if analysis.benchmark_assessment.overall_assessment == "underperform":
            action_items.append("Benchmark assessment suggests underlying assumptions are conservative; either improve performance levers or reprice the opportunity.")
        if analysis.valuation_sanity.terminal_value_dependency == "critical":
            action_items.append("Terminal value dependency is critical; get independent exit cap validation and adjust hold-period sensitivity.")
        if analysis.governance_risk.governance_risk != "low":
            action_items.append("Ramp up governance due diligence while progressing deal team approval.")

        if not action_items:
            action_items.append("No urgent action items detected, proceed with standard diligence.")

        return RoiRecommendationSummary(
            recommendation=recommendation,
            conviction=conviction,
            score=round(score, 2),
            rationale=rationale[:4],
            required_assumption_checks=required_assumption_checks[:4],
            action_items=action_items[:4],
        )

    def build_ranking_item(self, scenario: RoiScenarioSummary) -> RoiScenarioRankingItem:
        payload = RoiScenarioInput.model_validate(scenario.model_dump())
        analysis = self.build_analysis(payload)
        recommendation = self.build_recommendation(payload, analysis)
        return RoiScenarioRankingItem(
            scenario_id=scenario.id,
            scenario_name=scenario.name,
            scenario_type=scenario.scenario_type,
            projected_irr=scenario.projected_irr,
            projected_npv=scenario.projected_npv,
            equity_multiple=scenario.equity_multiple,
            risk_adjusted_score=analysis.risk_adjusted_score or 0.0,
            recommendation=recommendation.recommendation,
            probability_negative_npv=analysis.monte_carlo.probability_negative_npv,
            probability_dscr_below_one=analysis.monte_carlo.probability_dscr_below_one,
        )

    def build_sensitivity(self, payload: RoiScenarioInput) -> RoiSensitivityResponse:
        points: list[RoiSensitivityPoint] = []
        for exit_cap_delta in (-1.0, -0.5, 0.0, 0.5, 1.0):
            for growth_delta in (-2.0, -1.0, 0.0, 1.0, 2.0):
                varied = payload.model_copy(
                    update={
                        "exit_cap_rate": max(0.1, payload.exit_cap_rate + exit_cap_delta),
                        "annual_revenue_growth_rate": payload.annual_revenue_growth_rate + growth_delta,
                    }
                )
                computed = self.calculate(varied)
                points.append(
                    RoiSensitivityPoint(
                        exit_cap_rate=varied.exit_cap_rate,
                        annual_revenue_growth_rate=varied.annual_revenue_growth_rate,
                        projected_irr=computed.projected_irr,
                        projected_npv=computed.projected_npv,
                        equity_multiple=computed.equity_multiple,
                    )
                )
        return RoiSensitivityResponse(
            base_exit_cap_rate=payload.exit_cap_rate,
            base_annual_revenue_growth_rate=payload.annual_revenue_growth_rate,
            points=points,
        )

    def _build_value_driver_summary(self, payload: RoiScenarioInput, computed: RoiComputation) -> RoiValueDriverSummary:
        monthly_cost_of_equity = (1 + (computed.cost_of_equity / 100)) ** (1 / 12) - 1 if computed.cost_of_equity > -100 else 0.0
        operating_cash_flow_present_value = 0.0
        terminal_value_present_value = 0.0
        sale_proceeds_total = 0.0
        total_cash_flow = 0.0
        for item in computed.monthly_cash_flows:
            discount_factor = (1 + monthly_cost_of_equity) ** item.month if monthly_cost_of_equity > -1 else 1.0
            operating_component = item.total_cash_flow - item.net_sale_proceeds
            operating_cash_flow_present_value += operating_component / discount_factor
            terminal_value_present_value += item.net_sale_proceeds / discount_factor
            sale_proceeds_total += item.net_sale_proceeds
            total_cash_flow += item.total_cash_flow

        total_present_value = operating_cash_flow_present_value + terminal_value_present_value
        tax_shield_share = (
            min(max(computed.total_tax_shield / total_present_value, 0.0), 1.0) * 100
            if total_present_value > 0 and computed.total_tax_shield > 0
            else None
        )
        return RoiValueDriverSummary(
            operating_cash_flow_present_value=round(operating_cash_flow_present_value, 2),
            terminal_value_present_value=round(terminal_value_present_value, 2),
            terminal_value_share_of_present_value=round((terminal_value_present_value / total_present_value) * 100, 2)
            if total_present_value > 0
            else None,
            sale_proceeds_share_of_total_cash_flow=round((sale_proceeds_total / total_cash_flow) * 100, 2)
            if total_cash_flow > 0
            else None,
            tax_shield_share_of_present_value=round(tax_shield_share, 2) if tax_shield_share is not None else None,
            leverage_ratio=round(payload.leverage_ratio, 2),
        )

    def _build_return_attribution(self, payload: RoiScenarioInput, computed: RoiComputation) -> RoiReturnAttribution:
        sale_proceeds_contribution = computed.sale_proceeds_after_debt
        total_fcfe = sum(item.fcfe for item in computed.monthly_cash_flows)
        operating_cash_flow_contribution = max(total_fcfe - sale_proceeds_contribution, 0.0)
        acquisition_fees = payload.purchase_price * (payload.acquisition_fee_rate / 100)
        debt_amount = payload.purchase_price * (payload.leverage_ratio / 100)
        origination_fees = debt_amount * (payload.loan_origination_fee_rate / 100)
        fee_drag = acquisition_fees + origination_fees
        base_cost = payload.purchase_price + payload.upfront_capex + payload.initial_working_capital
        leverage_contribution = computed.equity_multiple - computed.unlevered_equity_multiple
        leverage_contribution_value = max(leverage_contribution, 0.0) * max(base_cost - debt_amount, 0.0)
        working_capital_drag = computed.average_working_capital_balance
        return RoiReturnAttribution(
            operating_cash_flow_contribution=round(operating_cash_flow_contribution, 2),
            sale_proceeds_contribution=round(sale_proceeds_contribution, 2),
            tax_shield_contribution=round(computed.total_tax_shield, 2),
            leverage_contribution=round(leverage_contribution_value, 2),
            fee_drag_contribution=round(-fee_drag, 2),
            working_capital_drag_contribution=round(-working_capital_drag, 2),
        )

    def _build_valuation_sanity(
        self,
        payload: RoiScenarioInput,
        computed: RoiComputation,
        value_driver_summary: RoiValueDriverSummary,
    ) -> RoiValuationSanityCheck:
        notes: list[str] = []
        entry_cap_rate = (
            ((payload.annual_revenue * (1 - (payload.vacancy_rate / 100)) - payload.annual_operating_expenses) / payload.purchase_price) * 100
            if payload.purchase_price > 0
            else None
        )
        spread_to_exit = (payload.exit_cap_rate - entry_cap_rate) if entry_cap_rate is not None else None
        implied_value_creation_multiple = (
            computed.terminal_value / payload.purchase_price if payload.purchase_price > 0 else None
        )
        terminal_share = value_driver_summary.terminal_value_share_of_present_value or 0.0
        if terminal_share >= 65:
            dependency = "critical"
            notes.append("Most present value comes from the terminal assumption rather than in-period operations.")
        elif terminal_share >= 50:
            dependency = "elevated"
            notes.append("A large share of value comes from exit assumptions, so the underwriting is exit-sensitive.")
        else:
            dependency = "healthy"
            notes.append("The valuation is supported by a more balanced mix of operating cash flow and exit value.")
        if spread_to_exit is not None and spread_to_exit < -0.5:
            notes.append("Exit cap is tighter than the implied entry cap, which assumes valuation expansion to realize returns.")
        return RoiValuationSanityCheck(
            terminal_value_dependency=dependency,
            entry_cap_rate=round(entry_cap_rate, 2) if entry_cap_rate is not None else None,
            spread_to_exit_cap_rate=round(spread_to_exit, 2) if spread_to_exit is not None else None,
            implied_value_creation_multiple=round(implied_value_creation_multiple, 2) if implied_value_creation_multiple is not None else None,
            notes=notes,
        )

    def _build_quality_of_earnings(self, payload: RoiScenarioInput, computed: RoiComputation) -> RoiQualityOfEarningsCheck:
        notes: list[str] = []
        concentration = "low"
        if payload.lease_assumptions:
            if len(payload.lease_assumptions) <= 2:
                concentration = "high"
                notes.append("Rent roll concentration is high, so one tenant can materially change projected cash flow.")
            elif len(payload.lease_assumptions) <= 4:
                concentration = "medium"
                notes.append("The revenue base is moderately concentrated across a small number of lease lines.")

        earnings_quality = "strong"
        revenue_quality = "strong"
        reserve_ratio = (payload.annual_capex_reserve / payload.annual_revenue * 100) if payload.annual_revenue > 0 else 0.0
        if reserve_ratio < 2 and payload.upfront_capex == 0:
            earnings_quality = "weak"
            notes.append("Capex reserve is light relative to revenue, which may overstate distributable cash flow.")
        elif reserve_ratio < 4:
            earnings_quality = "moderate"
            notes.append("Capex reserve coverage is modest and should be validated against asset condition.")
        if payload.annual_revenue_growth_rate > 6:
            revenue_quality = "weak"
            notes.append("Revenue growth assumptions are aggressive and should be supported by leases or market evidence.")
        elif payload.annual_revenue_growth_rate > 3.5:
            revenue_quality = "moderate"
            notes.append("Revenue growth is above a conservative base case and needs external validation.")
        if payload.vacancy_rate >= 10:
            revenue_quality = "weak"
            notes.append("Elevated vacancy suggests the revenue base may be less durable than the model implies.")
        return RoiQualityOfEarningsCheck(
            revenue_quality=revenue_quality,
            earnings_quality=earnings_quality,
            revenue_concentration_risk=concentration,
            notes=notes or ["No major revenue-quality or earnings-quality distortions surfaced from the current inputs."],
        )

    def _build_execution_risk(self, payload: RoiScenarioInput, computed: RoiComputation) -> RoiExecutionRiskCheck:
        notes: list[str] = []
        execution_risk = "low"
        lease_rollover_risk = "low"
        downside_case_reliance = "low"

        if payload.upfront_capex > (payload.purchase_price * 0.15):
            execution_risk = "high"
            notes.append("The business plan relies on a large capex program, increasing execution and delivery risk.")
        elif payload.upfront_capex > (payload.purchase_price * 0.08):
            execution_risk = "medium"
            notes.append("The plan requires meaningful capex execution to hit modeled outcomes.")

        if payload.lease_assumptions and any(lease.end_month <= 24 for lease in payload.lease_assumptions):
            lease_rollover_risk = "high"
            notes.append("Near-term lease rollover creates a meaningful leasing execution burden.")
        elif payload.lease_assumptions and any(lease.end_month <= 36 for lease in payload.lease_assumptions):
            lease_rollover_risk = "medium"
            notes.append("A portion of the rent roll rolls within the medium term and should be monitored.")

        if (computed.projected_irr or 0.0) - (computed.unlevered_irr or 0.0) > 8 or (computed.sale_proceeds_after_debt / max(computed.total_profit + computed.equity_invested, 1.0)) > 0.6:
            downside_case_reliance = "high"
            notes.append("Returns rely heavily on leverage and/or exit realization rather than resilient operating cash flow.")
        elif (computed.projected_irr or 0.0) - (computed.unlevered_irr or 0.0) > 4:
            downside_case_reliance = "medium"
            notes.append("Leveraged returns are meaningfully above unlevered returns, increasing downside sensitivity.")

        return RoiExecutionRiskCheck(
            execution_risk=execution_risk,
            lease_rollover_risk=lease_rollover_risk,
            downside_case_reliance=downside_case_reliance,
            notes=notes or ["Execution risk appears manageable under the current underwriting assumptions."],
        )

    def _build_governance_risk(
        self,
        payload: RoiScenarioInput,
        computed: RoiComputation,
        value_driver_summary: RoiValueDriverSummary,
    ) -> RoiGovernanceRiskCheck:
        notes: list[str] = []
        governance_risk = "low"
        model_complexity_risk = "low"
        leverage_discipline = "strong"

        if payload.leverage_ratio >= 80 or (computed.minimum_dscr is not None and computed.minimum_dscr < 1.0):
            governance_risk = "high"
            notes.append("The capital structure leaves little margin for error, which raises discipline and downside-control concerns.")
        elif payload.leverage_ratio >= 70:
            governance_risk = "medium"
            notes.append("Aggressive leverage increases the importance of disciplined asset management and governance controls.")

        complexity_score = sum(
            [
                1 if payload.lease_assumptions else 0,
                1 if payload.interest_only_years > 0 else 0,
                1 if payload.upfront_capex > 0 else 0,
                1 if payload.working_capital_percent_of_revenue > 0 else 0,
                1 if payload.annual_depreciation > 0 else 0,
            ]
        )
        if complexity_score >= 4:
            model_complexity_risk = "high"
            notes.append("The thesis depends on several interacting assumptions, increasing model risk and governance burden.")
        elif complexity_score >= 2:
            model_complexity_risk = "medium"
            notes.append("The scenario has multiple moving parts that should be reviewed with tighter assumption governance.")

        if payload.leverage_ratio >= 75:
            leverage_discipline = "weak"
        elif payload.leverage_ratio >= 60:
            leverage_discipline = "moderate"

        if (value_driver_summary.terminal_value_share_of_present_value or 0.0) >= 60:
            notes.append("A high share of value is deferred to exit, so governance should focus on preventing narrative-driven overvaluation.")

        return RoiGovernanceRiskCheck(
            governance_risk=governance_risk,
            model_complexity_risk=model_complexity_risk,
            leverage_discipline=leverage_discipline,
            notes=notes or ["No clear governance-style fragility surfaced from the current structure."],
        )

    def _build_benchmark_assessment(
        self,
        payload: RoiScenarioInput,
        computed: RoiComputation,
        value_driver_summary: RoiValueDriverSummary,
        benchmark_profile: str | None,
        benchmark_ranges: dict[str, tuple[float, float]] | None,
    ) -> RoiBenchmarkAssessment:
        profile_name = benchmark_profile if benchmark_profile in self.BENCHMARK_PROFILES else "general"
        profile = benchmark_ranges or self.BENCHMARK_PROFILES[profile_name]
        metric_values = {
            "projected_irr": computed.projected_irr,
            "equity_multiple": computed.equity_multiple,
            "average_dscr": computed.average_dscr,
            "leverage_ratio": payload.leverage_ratio,
            "vacancy_rate": payload.vacancy_rate,
            "terminal_value_share_of_present_value": value_driver_summary.terminal_value_share_of_present_value,
        }
        metrics: list[RoiBenchmarkMetricComparison] = []
        within = 0
        adverse = 0
        for metric, bounds in profile.items():
            actual = metric_values.get(metric)
            metrics.append(self._benchmark_metric(metric, actual, bounds[0], bounds[1]))
            status = metrics[-1].status
            if status == "within":
                within += 1
            elif status in {"below", "above"}:
                adverse += 1
        if within >= max(len(metrics) - 1, 1) and adverse <= 1:
            overall = "outperform"
        elif adverse >= 3:
            overall = "underperform"
        else:
            overall = "mixed"
        confidence = "high" if payload.listing_id or payload.lease_assumptions else "medium"
        if not payload.lease_assumptions and payload.annual_revenue == 0:
            confidence = "low"
        notes = [f"Compared against the {profile_name} benchmark profile."]
        notes.append(
            "Benchmark ranges were calibrated from comparable records."
            if benchmark_ranges
            else "Benchmark ranges are internal defaults until external comps are connected."
        )
        return RoiBenchmarkAssessment(
            benchmark_profile=profile_name,
            overall_assessment=overall,
            confidence=confidence,
            metrics=metrics,
            notes=notes,
        )

    def calibrate_benchmark_profile(
        self,
        asset_class: str,
        comps: list[RoiBenchmarkCompSummary],
        location: str | None = None,
    ) -> tuple[dict[str, tuple[float, float]], RoiBenchmarkCalibrationResponse]:
        profile_name = asset_class if asset_class in self.BENCHMARK_PROFILES else "general"
        if not comps:
            default_profile = self.BENCHMARK_PROFILES[profile_name]
            return default_profile, RoiBenchmarkCalibrationResponse(
                benchmark_profile=profile_name,
                comp_count=0,
                effective_comp_count=0,
                matched_location=location,
                stale_comp_count=0,
                excluded_outlier_count=0,
                source_mode="default_profile",
                metrics=[
                    RoiBenchmarkMetricComparison(
                        metric=metric,
                        actual=None,
                        benchmark_min=bounds[0],
                        benchmark_max=bounds[1],
                        status="unavailable",
                        note="Using default benchmark range because no comparable records are available.",
                    )
                    for metric, bounds in default_profile.items()
                ],
                notes=["No comparable records were available, so default ranges were used."],
            )

        calibrated: dict[str, tuple[float, float]] = {}
        metrics: list[RoiBenchmarkMetricComparison] = []
        weighted_comps = [
            {
                "comp": comp,
                "weight": self._benchmark_comp_weight(comp, location),
            }
            for comp in comps
        ]
        weighted_comps = [item for item in weighted_comps if item["comp"].override_mode != "exclude_outlier"]
        weighted_comps = [item for item in weighted_comps if item["weight"] > 0]
        stale_comp_count = sum(1 for item in weighted_comps if self._benchmark_comp_age_weight(item["comp"]) < 1.0)
        excluded_outlier_count = 0
        metric_sources = {
            "projected_irr": [(item["comp"].projected_irr, item["weight"]) for item in weighted_comps if item["comp"].projected_irr is not None],
            "equity_multiple": [(item["comp"].equity_multiple, item["weight"]) for item in weighted_comps if item["comp"].equity_multiple is not None],
            "average_dscr": [(item["comp"].average_dscr, item["weight"]) for item in weighted_comps if item["comp"].average_dscr is not None],
            "leverage_ratio": [(item["comp"].leverage_ratio, item["weight"]) for item in weighted_comps if item["comp"].leverage_ratio is not None],
            "vacancy_rate": [(100 - item["comp"].occupancy_rate, item["weight"]) for item in weighted_comps if item["comp"].occupancy_rate is not None],
        }
        effective_comp_keys: set[str] = set()
        for metric, weighted_values in metric_sources.items():
            if weighted_values:
                filtered_values, excluded = self._exclude_outliers(metric, weighted_values, weighted_comps)
                excluded_outlier_count += excluded
                numeric_values = [value for value, _weight in filtered_values]
                if not numeric_values:
                    continue
                min_value = round(self._weighted_percentile(filtered_values, 25) or min(numeric_values), 2)
                max_value = round(self._weighted_percentile(filtered_values, 75) or max(numeric_values), 2)
                calibrated[metric] = (min_value, max_value)
                for value, _weight in filtered_values:
                    for item in weighted_comps:
                        comp = item["comp"]
                        if metric == "vacancy_rate":
                            metric_value = 100 - comp.occupancy_rate if comp.occupancy_rate is not None else None
                        else:
                            metric_value = getattr(comp, metric)
                        if metric_value == value:
                            effective_comp_keys.add(comp.id)
                metrics.append(
                    RoiBenchmarkMetricComparison(
                        metric=metric,
                        actual=None,
                        benchmark_min=min_value,
                        benchmark_max=max_value,
                        status="unavailable",
                        note="Calibrated from comparable records.",
                    )
                )
        if "terminal_value_share_of_present_value" not in calibrated:
            calibrated["terminal_value_share_of_present_value"] = self.BENCHMARK_PROFILES[profile_name]["terminal_value_share_of_present_value"]
            metrics.append(
                RoiBenchmarkMetricComparison(
                    metric="terminal_value_share_of_present_value",
                    actual=None,
                    benchmark_min=calibrated["terminal_value_share_of_present_value"][0],
                    benchmark_max=calibrated["terminal_value_share_of_present_value"][1],
                    status="unavailable",
                    note="Using default range for terminal-value dependency because comps do not directly encode it.",
                )
            )
        return calibrated, RoiBenchmarkCalibrationResponse(
            benchmark_profile=profile_name,
            comp_count=len(comps),
            effective_comp_count=len(effective_comp_keys) or len(weighted_comps),
            matched_location=location,
            stale_comp_count=stale_comp_count,
            excluded_outlier_count=excluded_outlier_count,
            source_mode="external_comps",
            metrics=metrics,
            notes=self._build_calibration_notes(location, len(comps), len(effective_comp_keys) or len(weighted_comps), stale_comp_count, excluded_outlier_count),
        )

    def _build_calibration_notes(
        self,
        location: str | None,
        comp_count: int,
        effective_comp_count: int,
        stale_comp_count: int,
        excluded_outlier_count: int,
    ) -> list[str]:
        notes = ["Benchmark calibration derived from tenant-provided comparable records."]
        if location:
            notes.append(f"Calibration favored records closest to {location}.")
        if stale_comp_count:
            notes.append(f"{stale_comp_count} older comparable records were down-weighted for staleness.")
        if excluded_outlier_count:
            notes.append(f"{excluded_outlier_count} outlier metric observations were excluded from range construction.")
        if effective_comp_count < comp_count:
            notes.append("Only the most relevant comparable observations contributed to the final calibration range.")
        return notes

    def _normalize_location(self, value: str | None) -> str:
        return (value or "").strip().lower()

    def _extract_state(self, value: str | None) -> str | None:
        normalized = self._normalize_location(value)
        if "," in normalized:
            return normalized.split(",")[-1].strip()
        return None

    def _benchmark_comp_age_weight(self, comp: RoiBenchmarkCompSummary) -> float:
        if comp.closed_on is None:
            return 0.6
        today = datetime.now(UTC).date()
        age_days = max((today - comp.closed_on).days, 0)
        if age_days <= 365:
            return 1.0
        if age_days <= 730:
            return 0.8
        if age_days <= 1095:
            return 0.6
        return 0.35

    def _benchmark_comp_weight(self, comp: RoiBenchmarkCompSummary, location: str | None) -> float:
        age_weight = self._benchmark_comp_age_weight(comp)
        if not location:
            return age_weight
        target_location = self._normalize_location(location)
        comp_location = self._normalize_location(comp.location)
        if comp_location == target_location:
            return age_weight * 1.0
        if self._extract_state(comp.location) and self._extract_state(comp.location) == self._extract_state(location):
            return age_weight * 0.75
        return age_weight * 0.45

    def _exclude_outliers(
        self,
        metric: str,
        weighted_values: list[tuple[float, float]],
        weighted_comps: list[dict[str, object]],
    ) -> tuple[list[tuple[float, float]], int]:
        values = [value for value, _weight in weighted_values]
        if len(values) < 4:
            return weighted_values, 0
        q1 = self._percentile(values, 25)
        q3 = self._percentile(values, 75)
        if q1 is None or q3 is None:
            return weighted_values, 0
        iqr = q3 - q1
        if iqr <= 0:
            return weighted_values, 0
        lower = q1 - (1.5 * iqr)
        upper = q3 + (1.5 * iqr)
        forced_values: list[tuple[float, float]] = []
        for item in weighted_comps:
            comp = item["comp"]
            if getattr(comp, "override_mode", "normal") != "force_include":
                continue
            if metric == "vacancy_rate":
                metric_value = 100 - comp.occupancy_rate if comp.occupancy_rate is not None else None
            else:
                metric_value = getattr(comp, metric)
            if metric_value is not None:
                forced_values.append((metric_value, item["weight"]))
        filtered = [(value, weight) for value, weight in weighted_values if lower <= value <= upper]
        for forced in forced_values:
            if forced not in filtered:
                filtered.append(forced)
        return (filtered or weighted_values), max(len(weighted_values) - len(filtered), 0)

    def _weighted_percentile(self, weighted_values: list[tuple[float, float]], percentile: float) -> float | None:
        if not weighted_values:
            return None
        ordered = sorted(weighted_values, key=lambda item: item[0])
        total_weight = sum(weight for _value, weight in ordered)
        if total_weight <= 0:
            return None
        threshold = total_weight * (percentile / 100)
        cumulative = 0.0
        for value, weight in ordered:
            cumulative += weight
            if cumulative >= threshold:
                return value
        return ordered[-1][0]

    def _benchmark_metric(self, metric: str, actual: float | None, benchmark_min: float, benchmark_max: float) -> RoiBenchmarkMetricComparison:
        label = metric.replace("_", " ")
        if actual is None:
            return RoiBenchmarkMetricComparison(
                metric=metric,
                actual=None,
                benchmark_min=benchmark_min,
                benchmark_max=benchmark_max,
                status="unavailable",
                note=f"{label.title()} is unavailable for benchmark comparison.",
            )
        if actual < benchmark_min:
            status = "below"
            note = f"{label.title()} is below the benchmark range."
        elif actual > benchmark_max:
            status = "above"
            note = f"{label.title()} is above the benchmark range."
        else:
            status = "within"
            note = f"{label.title()} sits inside the benchmark range."
        return RoiBenchmarkMetricComparison(
            metric=metric,
            actual=round(actual, 2),
            benchmark_min=benchmark_min,
            benchmark_max=benchmark_max,
            status=status,
            note=note,
        )

    def _build_risk_flags(
        self,
        payload: RoiScenarioInput,
        computed: RoiComputation,
        value_driver_summary: RoiValueDriverSummary,
    ) -> list[RoiRiskFlag]:
        flags: list[RoiRiskFlag] = []
        if computed.minimum_dscr is not None and computed.minimum_dscr < 1.0:
            flags.append(
                RoiRiskFlag(
                    severity="high",
                    code="dscr_below_1",
                    title="Debt service shortfall",
                    detail=f"Minimum DSCR falls to {computed.minimum_dscr:.2f}, which implies debt service is not covered in at least one period.",
                )
            )
        elif computed.minimum_dscr is not None and computed.minimum_dscr < 1.2:
            flags.append(
                RoiRiskFlag(
                    severity="medium",
                    code="tight_dscr",
                    title="Thin debt coverage",
                    detail=f"Minimum DSCR is {computed.minimum_dscr:.2f}, leaving limited room for revenue misses or higher expenses.",
                )
            )
        if value_driver_summary.terminal_value_share_of_present_value is not None and value_driver_summary.terminal_value_share_of_present_value >= 65:
            flags.append(
                RoiRiskFlag(
                    severity="high",
                    code="terminal_value_concentration",
                    title="Terminal value concentration",
                    detail=f"{value_driver_summary.terminal_value_share_of_present_value:.1f}% of present value comes from the exit, so the deal is highly sensitive to disposition assumptions.",
                )
            )
        elif value_driver_summary.terminal_value_share_of_present_value is not None and value_driver_summary.terminal_value_share_of_present_value >= 50:
            flags.append(
                RoiRiskFlag(
                    severity="medium",
                    code="elevated_terminal_value_concentration",
                    title="Exit-heavy valuation",
                    detail=f"{value_driver_summary.terminal_value_share_of_present_value:.1f}% of present value comes from terminal value rather than in-period cash flow.",
                )
            )
        if payload.leverage_ratio >= 75:
            flags.append(
                RoiRiskFlag(
                    severity="medium",
                    code="high_leverage",
                    title="Aggressive leverage",
                    detail=f"Leverage is modeled at {payload.leverage_ratio:.1f}%, which can amplify equity returns but narrows downside tolerance.",
                )
            )
        if computed.payback_period_years is None:
            flags.append(
                RoiRiskFlag(
                    severity="medium",
                    code="no_payback_within_hold",
                    title="Equity not repaid within hold",
                    detail="The modeled equity outlay is not fully paid back during the hold period without relying on post-hold assumptions.",
                )
            )
        if computed.projected_irr is not None and computed.projected_irr < 0:
            flags.append(
                RoiRiskFlag(
                    severity="high",
                    code="negative_irr",
                    title="Negative projected IRR",
                    detail=f"The levered IRR is {computed.projected_irr:.2f}%, indicating value destruction under current assumptions.",
                )
            )
        if payload.lease_assumptions and len(payload.lease_assumptions) <= 2:
            flags.append(
                RoiRiskFlag(
                    severity="low",
                    code="tenant_concentration",
                    title="Tenant concentration risk",
                    detail=f"The rent roll is driven by {len(payload.lease_assumptions)} lease lines, so one rollover event can materially change value.",
                )
            )
        return flags

    def _build_stress_tests(self, payload: RoiScenarioInput) -> list[RoiStressTestResult]:
        scenarios = [
            (
                "Revenue Down 10%",
                "revenue_down_10",
                {
                    "annual_revenue": payload.annual_revenue * 0.9,
                    "lease_assumptions": [
                        lease.model_copy(update={"monthly_rent": lease.monthly_rent * 0.9})
                        for lease in payload.lease_assumptions
                    ],
                },
            ),
            (
                "Exit Cap +100 bps",
                "exit_cap_up_100bps",
                {"exit_cap_rate": payload.exit_cap_rate + 1.0},
            ),
            (
                "Interest Rate +100 bps",
                "interest_rate_up_100bps",
                {"interest_rate": payload.interest_rate + 1.0},
            ),
            (
                "Vacancy +5 pts",
                "vacancy_up_500bps",
                {"vacancy_rate": min(payload.vacancy_rate + 5.0, 100.0)},
            ),
            (
                "Downside Blend",
                "combined_downside",
                {
                    "annual_revenue": payload.annual_revenue * 0.93,
                    "lease_assumptions": [
                        lease.model_copy(update={"monthly_rent": lease.monthly_rent * 0.93})
                        for lease in payload.lease_assumptions
                    ],
                    "vacancy_rate": min(payload.vacancy_rate + 3.0, 100.0),
                    "exit_cap_rate": payload.exit_cap_rate + 0.75,
                    "interest_rate": payload.interest_rate + 0.75,
                },
            ),
        ]

        results: list[RoiStressTestResult] = []
        for scenario_name, scenario_key, updates in scenarios:
            stressed_payload = payload.model_copy(update=updates)
            stressed = self.calculate(stressed_payload)
            results.append(
                RoiStressTestResult(
                    scenario_name=scenario_name,
                    scenario_key=scenario_key,
                    projected_irr=stressed.projected_irr,
                    projected_npv=stressed.projected_npv,
                    equity_multiple=stressed.equity_multiple,
                    average_dscr=stressed.average_dscr,
                    minimum_dscr=stressed.minimum_dscr,
                )
            )
        return results

    def _build_monte_carlo_summary(self, payload: RoiScenarioInput, simulation_count: int = 120) -> RoiMonteCarloSummary:
        seed_basis = payload.model_dump_json()
        seed = int(md5(seed_basis.encode("utf-8")).hexdigest()[:8], 16)
        rng = Random(seed)
        irr_values: list[float] = []
        npv_values: list[float] = []
        equity_multiples: list[float] = []
        negative_irr_count = 0
        negative_npv_count = 0
        dscr_below_one_count = 0
        equity_multiple_below_one_count = 0
        stressed_regime_count = 0

        for _ in range(simulation_count):
            market_factor = rng.gauss(0.0, 1.0)
            rate_factor = (0.55 * market_factor) + rng.gauss(0.0, 0.7)
            operations_factor = (-0.45 * market_factor) + rng.gauss(0.0, 0.7)
            execution_factor = rng.gauss(0.0, 1.0)
            stressed_regime = market_factor < -1.15 or rate_factor > 1.35
            if stressed_regime:
                stressed_regime_count += 1
            stressed_payload = payload.model_copy(
                update={
                    "annual_revenue": payload.annual_revenue
                    * self._bounded(1.0 + (market_factor * 0.07) - (operations_factor * 0.03), 0.65, 1.35),
                    "annual_operating_expenses": payload.annual_operating_expenses
                    * self._bounded(1.0 + (operations_factor * 0.05) + (market_factor * 0.02), 0.8, 1.3),
                    "annual_revenue_growth_rate": payload.annual_revenue_growth_rate + (market_factor * 0.9) - (operations_factor * 0.35),
                    "annual_expense_growth_rate": payload.annual_expense_growth_rate + (operations_factor * 0.65) + (market_factor * 0.15),
                    "exit_cap_rate": max(0.25, payload.exit_cap_rate + (rate_factor * 0.35) - (market_factor * 0.12)),
                    "interest_rate": max(0.0, payload.interest_rate + (rate_factor * 0.45)),
                    "vacancy_rate": self._bounded(payload.vacancy_rate + (operations_factor * 1.7) - (market_factor * 0.8), 0.0, 100.0),
                    "lease_assumptions": [
                        lease.model_copy(
                            update={
                                "monthly_rent": lease.monthly_rent
                                * self._bounded(1.0 + (market_factor * 0.07) - (operations_factor * 0.03), 0.65, 1.35),
                                "renewal_rent_change_rate": lease.renewal_rent_change_rate + (market_factor * 1.1),
                                "downtime_months_after_expiry": int(
                                    round(
                                        self._bounded(
                                            lease.downtime_months_after_expiry + (execution_factor * 1.2) + max(-market_factor, 0.0) * 0.8,
                                            0.0,
                                            24.0,
                                        )
                                    )
                                ),
                            }
                        )
                        for lease in payload.lease_assumptions
                    ],
                }
            )
            result = self.calculate(stressed_payload)
            if result.projected_irr is not None:
                irr_values.append(result.projected_irr)
                if result.projected_irr < 0:
                    negative_irr_count += 1
            if result.projected_npv < 0:
                negative_npv_count += 1
            npv_values.append(result.projected_npv)
            if result.equity_multiple is not None:
                equity_multiples.append(result.equity_multiple)
                if result.equity_multiple < 1:
                    equity_multiple_below_one_count += 1
            if result.minimum_dscr is not None and result.minimum_dscr < 1.0:
                dscr_below_one_count += 1

        expected_shortfall_npv = None
        if npv_values:
            lower_tail_cutoff = self._percentile(npv_values, 5)
            lower_tail = [value for value in npv_values if lower_tail_cutoff is not None and value <= lower_tail_cutoff]
            if lower_tail:
                expected_shortfall_npv = round(sum(lower_tail) / len(lower_tail), 2)

        return RoiMonteCarloSummary(
            simulation_count=simulation_count,
            mean_projected_irr=round(sum(irr_values) / len(irr_values), 2) if irr_values else None,
            median_projected_irr=self._percentile(irr_values, 50),
            downside_irr_5th_percentile=self._percentile(irr_values, 5),
            upside_irr_95th_percentile=self._percentile(irr_values, 95),
            mean_projected_npv=round(sum(npv_values) / len(npv_values), 2) if npv_values else None,
            downside_npv_5th_percentile=self._percentile(npv_values, 5),
            upside_npv_95th_percentile=self._percentile(npv_values, 95),
            mean_equity_multiple=round(sum(equity_multiples) / len(equity_multiples), 3) if equity_multiples else None,
            probability_negative_irr=round((negative_irr_count / simulation_count) * 100, 2) if irr_values else None,
            probability_negative_npv=round((negative_npv_count / simulation_count) * 100, 2),
            probability_dscr_below_one=round((dscr_below_one_count / simulation_count) * 100, 2),
            probability_equity_multiple_below_one=round((equity_multiple_below_one_count / simulation_count) * 100, 2)
            if equity_multiples
            else None,
            expected_shortfall_npv=expected_shortfall_npv,
            stressed_regime_probability=round((stressed_regime_count / simulation_count) * 100, 2),
        )

    def _compute_risk_adjusted_score(
        self,
        computed: RoiComputation,
        value_driver_summary: RoiValueDriverSummary,
        monte_carlo: RoiMonteCarloSummary,
    ) -> float:
        base_return = (computed.projected_irr or 0.0) * 1.6
        npv_scale = min(max(computed.projected_npv / max(computed.equity_invested, 1.0), -1.0), 3.0) * 12
        downside_penalty = (
            (monte_carlo.probability_negative_npv or 0.0) * 0.55
            + (monte_carlo.probability_dscr_below_one or 0.0) * 0.45
            + (monte_carlo.probability_equity_multiple_below_one or 0.0) * 0.35
        )
        concentration_penalty = max((value_driver_summary.terminal_value_share_of_present_value or 0.0) - 45.0, 0.0) * 0.35
        leverage_penalty = max(computed.debt_amount / max(computed.debt_amount + computed.equity_invested, 1.0) * 100 - 65.0, 0.0) * 0.4
        coverage_bonus = max(((computed.minimum_dscr or 1.0) - 1.1) * 14, 0.0)
        score = base_return + npv_scale + coverage_bonus - downside_penalty - concentration_penalty - leverage_penalty
        return round(score, 2)

    def _build_monthly_revenue_schedule(self, payload: RoiScenarioInput, months: int, monthly_revenue_growth: float) -> list[float]:
        if not payload.lease_assumptions:
            monthly_revenue = payload.annual_revenue / 12
            schedule: list[float] = []
            for _ in range(months):
                schedule.append(monthly_revenue)
                monthly_revenue *= 1 + monthly_revenue_growth
            return schedule

        schedule = [0.0 for _ in range(months)]
        for lease in payload.lease_assumptions:
            monthly_growth = (1 + (lease.annual_rent_growth_rate / 100)) ** (1 / 12) - 1
            active_rent = lease.monthly_rent
            for month in range(max(1, lease.start_month), min(months, lease.end_month) + 1):
                schedule[month - 1] += active_rent + lease.reimbursement_monthly
                active_rent *= 1 + monthly_growth

            renewal_start = lease.end_month + lease.downtime_months_after_expiry + 1
            if renewal_start > months:
                continue
            renewal_rent = lease.renewal_monthly_rent
            if renewal_rent is None:
                renewal_rent = active_rent * (1 + (lease.renewal_rent_change_rate / 100))
            renewed_rent = renewal_rent
            for month in range(renewal_start, months + 1):
                schedule[month - 1] += renewed_rent + lease.reimbursement_monthly
                renewed_rent *= 1 + monthly_growth
        return schedule

    def _project_next_month_revenue(self, payload: RoiScenarioInput, monthly_revenues: list[float], monthly_revenue_growth: float) -> float:
        if not monthly_revenues:
            return 0.0
        if not payload.lease_assumptions:
            return monthly_revenues[-1] * (1 + monthly_revenue_growth)

        next_month_index = len(monthly_revenues) + 1
        next_value = 0.0
        for lease in payload.lease_assumptions:
            monthly_growth = (1 + (lease.annual_rent_growth_rate / 100)) ** (1 / 12) - 1
            if next_month_index <= lease.end_month:
                months_active = max(0, next_month_index - lease.start_month)
                if next_month_index >= lease.start_month:
                    next_value += (lease.monthly_rent * ((1 + monthly_growth) ** months_active)) + lease.reimbursement_monthly
                continue
            renewal_start = lease.end_month + lease.downtime_months_after_expiry + 1
            if next_month_index < renewal_start:
                continue
            base_renewal_rent = lease.renewal_monthly_rent
            if base_renewal_rent is None:
                original_term_months = max(0, lease.end_month - lease.start_month + 1)
                base_renewal_rent = lease.monthly_rent * ((1 + monthly_growth) ** original_term_months)
                base_renewal_rent *= 1 + (lease.renewal_rent_change_rate / 100)
            renewal_months = next_month_index - renewal_start
            next_value += (base_renewal_rent * ((1 + monthly_growth) ** renewal_months)) + lease.reimbursement_monthly
        return next_value

    def _payment(self, principal: float, rate: float, periods: int) -> float:
        if principal <= 0 or periods <= 0:
            return 0.0
        if rate == 0:
            return principal / periods
        return principal * (rate / (1 - ((1 + rate) ** (-periods))))

    def _bounded(self, value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))

    def _npv(self, cash_flows: list[float], discount_rate: float) -> float:
        return sum(cash_flow / ((1 + discount_rate) ** period) for period, cash_flow in enumerate(cash_flows))

    def _percentile(self, values: list[float], percentile: float) -> float | None:
        if not values:
            return None
        ordered = sorted(values)
        if len(ordered) == 1:
            return round(ordered[0], 2)
        rank = (percentile / 100) * (len(ordered) - 1)
        lower_index = int(rank)
        upper_index = min(lower_index + 1, len(ordered) - 1)
        weight = rank - lower_index
        interpolated = ordered[lower_index] + ((ordered[upper_index] - ordered[lower_index]) * weight)
        return round(interpolated, 2)

    def _irr(self, cash_flows: list[float]) -> float | None:
        if len(cash_flows) < 2 or all(cash_flow >= 0 for cash_flow in cash_flows):
            return None
        low = -0.99
        high = 2.0
        npv_low = self._npv(cash_flows, low)
        npv_high = self._npv(cash_flows, high)
        if npv_low * npv_high > 0:
            return None
        for _ in range(140):
            mid = (low + high) / 2
            npv_mid = self._npv(cash_flows, mid)
            if not isfinite(npv_mid):
                return None
            if abs(npv_mid) < 1e-7:
                return mid
            if npv_low * npv_mid <= 0:
                high = mid
            else:
                low = mid
                npv_low = npv_mid
        return (low + high) / 2

    def _payback_period(self, cash_flows: list[float]) -> float | None:
        cumulative = 0.0
        for index, cash_flow in enumerate(cash_flows):
            cumulative += cash_flow
            if cumulative >= 0 and index > 0:
                previous = cumulative - cash_flow
                if cash_flow <= 0:
                    return round(index / 12, 2)
                return round(((index - 1) + (abs(previous) / cash_flow)) / 12, 2)
        return None

    def _rollup_years(
        self,
        monthly_cash_flows: list[RoiMonthlyCashFlow],
        monthly_cost_of_equity: float,
        monthly_wacc: float,
    ) -> list[RoiYearlyCashFlow]:
        annual: list[RoiYearlyCashFlow] = []
        grouped: dict[int, list[RoiMonthlyCashFlow]] = {}
        for item in monthly_cash_flows:
            grouped.setdefault(item.year, []).append(item)
        for year in sorted(grouped):
            items = grouped[year]
            debt_service = sum(item.debt_service for item in items)
            noi = sum(item.net_operating_income for item in items)
            fcff = sum(item.fcff for item in items)
            fcfe = sum(item.fcfe for item in items)
            annual.append(
                RoiYearlyCashFlow(
                    year=year,
                    effective_revenue=round(sum(item.effective_revenue for item in items), 2),
                    operating_expenses=round(sum(item.operating_expenses for item in items), 2),
                    net_operating_income=round(noi, 2),
                    income_tax_expense=round(sum(item.income_tax_expense for item in items), 2),
                    depreciation=round(sum(item.depreciation for item in items), 2),
                    change_in_working_capital=round(sum(item.change_in_working_capital for item in items), 2),
                    tax_shield=round(sum(item.tax_shield for item in items), 2),
                    capex_reserve=round(sum(item.capex_reserve for item in items), 2),
                    interest_expense=round(sum(item.interest_expense for item in items), 2),
                    principal_paydown=round(sum(item.principal_paydown for item in items), 2),
                    debt_service=round(debt_service, 2),
                    fcff=round(fcff, 2),
                    fcfe=round(fcfe, 2),
                    cash_flow_before_sale=round(sum(item.levered_cash_flow for item in items), 2),
                    net_sale_proceeds=round(sum(item.net_sale_proceeds for item in items), 2),
                    total_cash_flow=round(sum(item.total_cash_flow for item in items), 2),
                    discounted_cash_flow=round(sum(item.fcfe / ((1 + monthly_cost_of_equity) ** item.month) for item in items), 2),
                    ending_loan_balance=items[-1].ending_loan_balance,
                    dscr=round((noi / debt_service), 3) if debt_service > 0 else None,
                )
            )
        return annual


roi_analysis_service = RoiAnalysisService()
