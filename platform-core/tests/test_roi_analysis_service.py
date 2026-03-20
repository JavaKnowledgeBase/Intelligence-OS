import unittest

from app.schemas.roi import RoiScenarioCreate
from app.services.roi_analysis_service import roi_analysis_service


class RoiAnalysisServiceTests(unittest.TestCase):
    def test_calculate_returns_expected_core_metrics(self) -> None:
        payload = RoiScenarioCreate(
            name="Base case",
            scenario_type="base",
            purchase_price=1_000_000,
            upfront_capex=100_000,
            annual_revenue=240_000,
            vacancy_rate=5,
            annual_operating_expenses=90_000,
            annual_capex_reserve=10_000,
            initial_working_capital=18_000,
            working_capital_percent_of_revenue=4,
            annual_depreciation=28_000,
            acquisition_fee_rate=1.5,
            loan_origination_fee_rate=1.0,
            annual_revenue_growth_rate=3,
            annual_expense_growth_rate=2,
            exit_cap_rate=6.5,
            exit_cost_rate=2,
            hold_period_years=5,
            discount_rate=12,
            leverage_ratio=50,
            interest_rate=6,
            interest_only_years=1,
            amortization_period_years=25,
        )

        result = roi_analysis_service.calculate(payload)

        self.assertGreater(result.net_operating_income, 130000)
        self.assertGreater(result.terminal_value, 0)
        self.assertGreater(result.projected_npv, 0)
        self.assertGreater(result.cash_on_cash_multiple, 1)
        self.assertIsNotNone(result.projected_irr)
        self.assertGreater(result.projected_irr or 0, 0)
        self.assertGreater(result.debt_amount, 0)
        self.assertGreater(result.sale_proceeds_after_debt, 0)
        self.assertGreater(result.equity_multiple, 1)
        self.assertIsNotNone(result.minimum_dscr)
        self.assertEqual(len(result.annual_cash_flows), 5)
        self.assertEqual(len(result.monthly_cash_flows), 60)
        self.assertGreater(result.annual_cash_flows[-1].net_sale_proceeds, 0)
        self.assertIsNotNone(result.unlevered_irr)
        self.assertGreater(result.unlevered_npv, 0)
        self.assertGreater(result.unlevered_equity_multiple, 1)
        self.assertGreater(result.cost_of_equity, 0)
        self.assertGreater(result.pre_tax_cost_of_debt, 0)
        self.assertGreater(result.weighted_average_cost_of_capital, 0)
        self.assertGreater(result.average_annual_fcff, 0)
        self.assertGreater(result.average_annual_fcfe, 0)
        self.assertGreater(result.total_tax_shield, 0)
        self.assertGreater(result.average_working_capital_balance, 0)
        self.assertIn("fcff", result.monthly_cash_flows[0].model_dump())
        self.assertIn("fcfe", result.monthly_cash_flows[0].model_dump())
        self.assertIn("depreciation", result.monthly_cash_flows[0].model_dump())
        self.assertIn("change_in_working_capital", result.monthly_cash_flows[0].model_dump())
        self.assertIn("tax_shield", result.monthly_cash_flows[0].model_dump())
        self.assertIn("depreciation", result.annual_cash_flows[0].model_dump())
        self.assertIn("change_in_working_capital", result.annual_cash_flows[0].model_dump())
        self.assertIn("tax_shield", result.annual_cash_flows[0].model_dump())

    def test_lease_assumptions_drive_monthly_revenue_schedule(self) -> None:
        payload = RoiScenarioCreate(
            name="Lease roll case",
            scenario_type="custom",
            purchase_price=2_000_000,
            upfront_capex=150_000,
            annual_revenue=0,
            annual_operating_expenses=120_000,
            annual_capex_reserve=24_000,
            exit_cap_rate=7,
            hold_period_years=2,
            discount_rate=12,
            leverage_ratio=50,
            interest_rate=6,
            lease_assumptions=[
                {
                    "tenant_name": "Anchor A",
                    "monthly_rent": 12000,
                    "start_month": 1,
                    "end_month": 12,
                    "annual_rent_growth_rate": 3,
                    "reimbursement_monthly": 500,
                    "downtime_months_after_expiry": 2,
                    "renewal_rent_change_rate": 5,
                },
                {
                    "tenant_name": "Inline B",
                    "monthly_rent": 4500,
                    "start_month": 1,
                    "end_month": 24,
                    "annual_rent_growth_rate": 2,
                },
            ],
        )

        result = roi_analysis_service.calculate(payload)

        self.assertEqual(len(result.monthly_cash_flows), 24)
        first_month = result.monthly_cash_flows[0]
        fourteenth_month = result.monthly_cash_flows[13]
        fifteenth_month = result.monthly_cash_flows[14]
        self.assertGreater(first_month.effective_revenue, 16000)
        self.assertLess(fourteenth_month.effective_revenue, first_month.effective_revenue)
        self.assertGreater(fifteenth_month.effective_revenue, fourteenth_month.effective_revenue)

    def test_build_analysis_returns_risk_flags_and_stress_tests(self) -> None:
        payload = RoiScenarioCreate(
            name="Stress case",
            scenario_type="custom",
            purchase_price=1_500_000,
            upfront_capex=80_000,
            annual_revenue=260_000,
            vacancy_rate=9,
            annual_operating_expenses=120_000,
            annual_capex_reserve=12_000,
            annual_depreciation=40_000,
            acquisition_fee_rate=1.0,
            loan_origination_fee_rate=0.75,
            exit_cap_rate=7.5,
            hold_period_years=5,
            leverage_ratio=78,
            interest_rate=7.25,
            lease_assumptions=[
                {
                    "tenant_name": "Anchor A",
                    "monthly_rent": 18000,
                    "start_month": 1,
                    "end_month": 60,
                }
            ],
        )

        computed = roi_analysis_service.calculate(payload)
        analysis = roi_analysis_service.build_analysis(payload, computed)
        recommendation = roi_analysis_service.build_recommendation(payload, analysis, computed)

        self.assertGreaterEqual(len(analysis.risk_flags), 2)
        self.assertEqual(len(analysis.stress_tests), 5)
        self.assertGreaterEqual(analysis.return_attribution.sale_proceeds_contribution, 0)
        self.assertGreater(analysis.return_attribution.operating_cash_flow_contribution, 0)
        self.assertLess(analysis.return_attribution.fee_drag_contribution, 0)
        self.assertIsNotNone(analysis.value_driver_summary.terminal_value_share_of_present_value)
        self.assertIn(analysis.valuation_sanity.terminal_value_dependency, {"healthy", "elevated", "critical"})
        self.assertIn(analysis.quality_of_earnings.earnings_quality, {"strong", "moderate", "weak"})
        self.assertIn(analysis.execution_risk.execution_risk, {"low", "medium", "high"})
        self.assertIn(analysis.governance_risk.governance_risk, {"low", "medium", "high"})
        self.assertIn(analysis.benchmark_assessment.overall_assessment, {"outperform", "mixed", "underperform"})
        self.assertGreaterEqual(len(analysis.benchmark_assessment.metrics), 1)
        self.assertTrue(any(flag.code == "high_leverage" for flag in analysis.risk_flags))
        self.assertTrue(any(result.scenario_key == "combined_downside" for result in analysis.stress_tests))
        self.assertEqual(analysis.monte_carlo.simulation_count, 120)
        self.assertIsNotNone(analysis.monte_carlo.mean_projected_npv)
        self.assertIsNotNone(analysis.monte_carlo.downside_npv_5th_percentile)
        self.assertIsNotNone(analysis.monte_carlo.probability_negative_npv)
        self.assertIsNotNone(analysis.monte_carlo.expected_shortfall_npv)
        self.assertIsNotNone(analysis.monte_carlo.stressed_regime_probability)
        self.assertIsNotNone(analysis.risk_adjusted_score)
        self.assertLess(analysis.risk_adjusted_score or 0, computed.projected_irr or 0)
        self.assertIn(recommendation.recommendation, {"invest", "watch", "reject"})
        self.assertGreaterEqual(len(recommendation.rationale), 1)
        self.assertGreaterEqual(len(recommendation.required_assumption_checks), 1)
        self.assertTrue(any("validate" in item.lower() or "review" in item.lower() or "confirm" in item.lower() for item in recommendation.required_assumption_checks))


if __name__ == "__main__":
    unittest.main()
