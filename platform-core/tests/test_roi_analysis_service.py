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


if __name__ == "__main__":
    unittest.main()
