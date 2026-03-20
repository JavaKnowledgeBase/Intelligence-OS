from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from app.schemas.roi import (
    RoiMonthlyCashFlow,
    RoiScenarioInput,
    RoiScenarioSummary,
    RoiSensitivityPoint,
    RoiSensitivityResponse,
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

    def _npv(self, cash_flows: list[float], discount_rate: float) -> float:
        return sum(cash_flow / ((1 + discount_rate) ** period) for period, cash_flow in enumerate(cash_flows))

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
