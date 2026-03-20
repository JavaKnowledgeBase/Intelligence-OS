import unittest
from copy import deepcopy
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.models.auth_seed import AUTH_USERS
from app.models.seed_data import ALERTS, LISTINGS, MARKET_INSIGHTS, PROJECTS, ROI_SCENARIOS
from app.schemas.alert import AlertPreference
from app.schemas.auth import AuthUser
from app.schemas.listing import ListingSummary
from app.schemas.market import MarketInsight
from app.schemas.project import ProjectSummary
from app.schemas.roi import RoiScenarioSummary
from app.services.auth_service import auth_service
from app.services.platform_service import platform_service
from app.services.platform_storage_service import platform_storage_service
from app.services.revoked_token_service import revoked_token_service
from app.services.session_store_service import session_store_service
from app.services.user_storage_service import user_storage_service


class ProjectRoiApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def setUp(self) -> None:
        platform_storage_service._available = False
        user_storage_service._available = False
        session_store_service._local_sessions.clear()
        revoked_token_service._local_revocations.clear()
        self._original_list_tenant_users = user_storage_service.list_tenant_users
        user_storage_service.list_tenant_users = lambda tenant_id: [
            item for item in deepcopy(AUTH_USERS) if item["tenant_id"] == tenant_id
        ]
        platform_service._projects = [ProjectSummary.model_validate(item) for item in deepcopy(PROJECTS)]
        platform_service._listings = [ListingSummary.model_validate(item) for item in deepcopy(LISTINGS)]
        platform_service._market_insights = [MarketInsight.model_validate(item) for item in deepcopy(MARKET_INSIGHTS)]
        platform_service._alerts = [AlertPreference.model_validate(item) for item in deepcopy(ALERTS)]
        platform_service._roi_scenarios = [RoiScenarioSummary.model_validate(item) for item in deepcopy(ROI_SCENARIOS)]
        platform_service._roi_actuals = []
        platform_service._benchmark_comps = []

    def tearDown(self) -> None:
        user_storage_service.list_tenant_users = self._original_list_tenant_users

    def auth_headers(self, *, user_id: str, email: str, full_name: str, role: str, tenant_id: str) -> dict[str, str]:
        session_id = uuid4().hex
        refresh_jti = uuid4().hex
        refresh_expires_at = datetime.now(UTC) + timedelta(hours=1)
        session_store_service.create_session(
            session_id=session_id,
            user_id=user_id,
            refresh_jti=refresh_jti,
            refresh_expires_at=refresh_expires_at,
        )
        token = auth_service._create_token(
            AuthUser(
                id=user_id,
                email=email,
                full_name=full_name,
                role=role,
                tenant_id=tenant_id,
            ),
            token_type="access",
            expires_in_seconds=900,
            session_id=session_id,
        )
        return {"Authorization": f"Bearer {token}"}

    def test_get_workspace_includes_roi_scenarios_and_snapshot(self) -> None:
        response = self.client.get(
            "/api/v1/projects/proj-roi-sunbelt/workspace",
            headers=self.auth_headers(
                user_id="user-ravi-kafley",
                email="founder@example.com",
                full_name="Ravi Kafley",
                role="admin",
                tenant_id="tenant-torilaure",
            ),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["roi_scenarios"]), 3)
        self.assertEqual(payload["roi_snapshot"]["scenario_count"], 3)
        self.assertIsNotNone(payload["roi_snapshot"]["base_case_irr"])
        self.assertIn("best_equity_multiple", payload["roi_snapshot"])
        self.assertIn("best_risk_adjusted_scenario_id", payload["roi_snapshot"])
        self.assertEqual(len(payload["roi_snapshot"]["scenario_rankings"]), 3)
        self.assertGreaterEqual(
            payload["roi_snapshot"]["scenario_rankings"][0]["risk_adjusted_score"],
            payload["roi_snapshot"]["scenario_rankings"][-1]["risk_adjusted_score"],
        )
        self.assertIn(
            payload["roi_snapshot"]["scenario_rankings"][0]["recommendation"],
            {"invest", "watch", "reject"},
        )

    def test_preview_roi_scenario_returns_computed_metrics(self) -> None:
        response = self.client.post(
            "/api/v1/projects/proj-roi-sunbelt/roi-scenarios/calculate",
            headers=self.auth_headers(
                user_id="user-analyst-demo",
                email="analyst@example.com",
                full_name="Analyst Demo",
                role="analyst",
                tenant_id="tenant-torilaure",
            ),
            json={
                "name": "Preview case",
                "scenario_type": "custom",
                "listing_id": "deal-1001",
                "purchase_price": 6200000,
                "upfront_capex": 450000,
                "annual_revenue": 980000,
                "annual_operating_expenses": 320000,
                "initial_working_capital": 45000,
                "working_capital_percent_of_revenue": 3,
                "annual_depreciation": 180000,
                "acquisition_fee_rate": 1.0,
                "loan_origination_fee_rate": 0.75,
                "annual_revenue_growth_rate": 3,
                "annual_expense_growth_rate": 2,
                "exit_cap_rate": 6.5,
                "exit_cost_rate": 2,
                "hold_period_years": 5,
                "discount_rate": 12,
                "leverage_ratio": 55,
                "interest_rate": 6,
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        scenario = payload["scenario"]
        self.assertEqual(scenario["id"], "preview")
        self.assertGreater(scenario["projected_npv"], 0)
        self.assertGreater(scenario["cash_on_cash_multiple"], 1)
        self.assertGreater(scenario["sale_proceeds_after_debt"], 0)
        self.assertGreater(len(payload["annual_cash_flows"]), 0)
        self.assertGreater(len(payload["monthly_cash_flows"]), 0)
        self.assertIn("unlevered_irr", scenario)
        self.assertIn("cost_of_equity", scenario)
        self.assertIn("weighted_average_cost_of_capital", scenario)
        self.assertIn("average_annual_fcff", scenario)
        self.assertIn("total_tax_shield", scenario)
        self.assertIn("average_working_capital_balance", scenario)
        self.assertGreater(scenario["total_tax_shield"], 0)
        self.assertGreater(scenario["average_working_capital_balance"], 0)
        self.assertIn("depreciation", payload["monthly_cash_flows"][0])
        self.assertIn("change_in_working_capital", payload["monthly_cash_flows"][0])
        self.assertIn("tax_shield", payload["monthly_cash_flows"][0])
        self.assertIn("analysis", payload)
        self.assertIn("risk_flags", payload["analysis"])
        self.assertIn("stress_tests", payload["analysis"])
        self.assertIn("return_attribution", payload["analysis"])
        self.assertIn("value_driver_summary", payload["analysis"])
        self.assertIn("valuation_sanity", payload["analysis"])
        self.assertIn("quality_of_earnings", payload["analysis"])
        self.assertIn("execution_risk", payload["analysis"])
        self.assertIn("governance_risk", payload["analysis"])
        self.assertIn("benchmark_assessment", payload["analysis"])
        self.assertIn("monte_carlo", payload["analysis"])
        self.assertEqual(payload["analysis"]["monte_carlo"]["simulation_count"], 120)
        self.assertIn("probability_negative_npv", payload["analysis"]["monte_carlo"])
        self.assertIn("downside_irr_5th_percentile", payload["analysis"]["monte_carlo"])
        self.assertIn("expected_shortfall_npv", payload["analysis"]["monte_carlo"])
        self.assertIn("stressed_regime_probability", payload["analysis"]["monte_carlo"])
        self.assertIn("risk_adjusted_score", payload["analysis"])
        self.assertIn("recommendation", payload)
        self.assertIn(payload["recommendation"]["recommendation"], {"invest", "watch", "reject"})
        self.assertGreaterEqual(len(payload["recommendation"]["rationale"]), 1)
        self.assertIn("action_items", payload["recommendation"])
        self.assertGreaterEqual(len(payload["recommendation"]["action_items"]), 1)

    def test_create_and_list_project_roi_recommendations(self) -> None:
        response = self.client.post(
            "/api/v1/projects/proj-roi-sunbelt/roi-scenarios/roi-base-sunbelt/recommendations",
            headers=self.auth_headers(
                user_id="user-analyst-demo",
                email="analyst@example.com",
                full_name="Analyst Demo",
                role="analyst",
                tenant_id="tenant-torilaure",
            ),
        )

        self.assertEqual(response.status_code, 201)
        recommendation_record = response.json()
        self.assertEqual(recommendation_record["scenario_id"], "roi-base-sunbelt")
        self.assertEqual(recommendation_record["project_id"], "proj-roi-sunbelt")
        self.assertEqual(recommendation_record["tenant_id"], "tenant-torilaure")
        self.assertEqual(recommendation_record["created_by"], "user-analyst-demo")
        self.assertIn(recommendation_record["recommendation"]["recommendation"], {"invest", "watch", "reject"})
        self.assertGreaterEqual(len(recommendation_record["recommendation"]["action_items"]), 1)

        list_response = self.client.get(
            "/api/v1/projects/proj-roi-sunbelt/roi-scenarios/roi-base-sunbelt/recommendations",
            headers=self.auth_headers(
                user_id="user-analyst-demo",
                email="analyst@example.com",
                full_name="Analyst Demo",
                role="analyst",
                tenant_id="tenant-torilaure",
            ),
        )

        self.assertEqual(list_response.status_code, 200)
        items = list_response.json()
        self.assertTrue(len(items) >= 1)
        self.assertEqual(items[0]["scenario_id"], "roi-base-sunbelt")

    def test_download_project_roi_recommendations_pdf(self) -> None:
        # create a recommendation first
        create_response = self.client.post(
            "/api/v1/projects/proj-roi-sunbelt/roi-scenarios/roi-base-sunbelt/recommendations",
            headers=self.auth_headers(
                user_id="user-analyst-demo",
                email="analyst@example.com",
                full_name="Analyst Demo",
                role="analyst",
                tenant_id="tenant-torilaure",
            ),
        )
        self.assertEqual(create_response.status_code, 201)

        pdf_response = self.client.get(
            "/api/v1/projects/proj-roi-sunbelt/roi-scenarios/roi-base-sunbelt/recommendations/pdf",
            headers=self.auth_headers(
                user_id="user-analyst-demo",
                email="analyst@example.com",
                full_name="Analyst Demo",
                role="analyst",
                tenant_id="tenant-torilaure",
            ),
        )

        self.assertEqual(pdf_response.status_code, 200)
        self.assertEqual(pdf_response.headers["content-type"], "application/pdf")
        self.assertIn("attachment; filename=roi-recommendations-proj-roi-sunbelt-roi-base-sunbelt.pdf", pdf_response.headers["content-disposition"])
        self.assertGreater(len(pdf_response.content), 100)

    def test_analyze_roi_scenario_returns_diagnostics_and_stress_cases(self) -> None:
        response = self.client.post(
            "/api/v1/projects/proj-roi-sunbelt/roi-scenarios/analyze",
            headers=self.auth_headers(
                user_id="user-analyst-demo",
                email="analyst@example.com",
                full_name="Analyst Demo",
                role="analyst",
                tenant_id="tenant-torilaure",
            ),
            json={
                "name": "Analysis case",
                "scenario_type": "custom",
                "listing_id": "deal-1001",
                "purchase_price": 6200000,
                "upfront_capex": 450000,
                "annual_revenue": 980000,
                "vacancy_rate": 8,
                "annual_operating_expenses": 320000,
                "annual_capex_reserve": 45000,
                "annual_depreciation": 180000,
                "exit_cap_rate": 6.5,
                "hold_period_years": 5,
                "leverage_ratio": 78,
                "interest_rate": 6.75,
                "lease_assumptions": [
                    {
                        "tenant_name": "Major Tenant",
                        "monthly_rent": 81000,
                        "start_month": 1,
                        "end_month": 60,
                    }
                ],
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["scenario"]["id"], "preview")
        self.assertEqual(len(payload["analysis"]["stress_tests"]), 5)
        self.assertTrue(any(flag["code"] == "high_leverage" for flag in payload["analysis"]["risk_flags"]))
        self.assertIn("return_attribution", payload["analysis"])
        self.assertIn("terminal_value_share_of_present_value", payload["analysis"]["value_driver_summary"])
        self.assertIn("valuation_sanity", payload["analysis"])
        self.assertIn("quality_of_earnings", payload["analysis"])
        self.assertIn("execution_risk", payload["analysis"])
        self.assertIn("governance_risk", payload["analysis"])
        self.assertIn("benchmark_assessment", payload["analysis"])
        self.assertEqual(payload["analysis"]["monte_carlo"]["simulation_count"], 120)
        self.assertIn("probability_dscr_below_one", payload["analysis"]["monte_carlo"])
        self.assertIn("risk_adjusted_score", payload["analysis"])
        self.assertIn("recommendation", payload)
        self.assertIn(payload["recommendation"]["conviction"], {"low", "medium", "high"})

    def test_roi_sensitivity_returns_matrix(self) -> None:
        response = self.client.post(
            "/api/v1/projects/proj-roi-sunbelt/roi-scenarios/sensitivity",
            headers=self.auth_headers(
                user_id="user-analyst-demo",
                email="analyst@example.com",
                full_name="Analyst Demo",
                role="analyst",
                tenant_id="tenant-torilaure",
            ),
            json={
                "name": "Sensitivity case",
                "scenario_type": "custom",
                "listing_id": "deal-1001",
                "purchase_price": 6200000,
                "upfront_capex": 450000,
                "annual_revenue": 980000,
                "vacancy_rate": 5,
                "annual_operating_expenses": 320000,
                "annual_capex_reserve": 45000,
                "annual_revenue_growth_rate": 3,
                "annual_expense_growth_rate": 2,
                "exit_cap_rate": 6.5,
                "exit_cost_rate": 2,
                "hold_period_years": 5,
                "discount_rate": 12,
                "leverage_ratio": 55,
                "interest_rate": 6,
                "interest_only_years": 1,
                "amortization_period_years": 30,
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["points"]), 25)

    def test_admin_can_record_actuals_and_view_variance(self) -> None:
        headers = self.auth_headers(
            user_id="user-ravi-kafley",
            email="founder@example.com",
            full_name="Ravi Kafley",
            role="admin",
            tenant_id="tenant-torilaure",
        )
        create_response = self.client.post(
            "/api/v1/projects/proj-roi-sunbelt/roi-scenarios/roi-base-sunbelt/actuals",
            headers=headers,
            json={
                "period_start": str(date(2026, 1, 1)),
                "effective_revenue": 76000,
                "operating_expenses": 25500,
                "capex": 3000,
                "debt_service": 18250,
                "occupancy_rate": 94.0,
                "note": "January operating actuals",
            },
        )
        self.assertEqual(create_response.status_code, 201)
        created = create_response.json()
        self.assertEqual(created["scenario_id"], "roi-base-sunbelt")

        list_response = self.client.get(
            "/api/v1/projects/proj-roi-sunbelt/roi-scenarios/roi-base-sunbelt/actuals",
            headers=headers,
        )
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.json()), 1)

        variance_response = self.client.get(
            "/api/v1/projects/proj-roi-sunbelt/roi-scenarios/roi-base-sunbelt/variance",
            headers=headers,
        )
        self.assertEqual(variance_response.status_code, 200)
        variance = variance_response.json()
        self.assertEqual(len(variance["periods"]), 1)
        self.assertIn("total_noi_variance", variance)
        self.assertGreaterEqual(len(variance["variance_summary"]), 1)

    def test_admin_can_create_benchmark_comp_and_get_calibration(self) -> None:
        headers = self.auth_headers(
            user_id="user-ravi-kafley",
            email="founder@example.com",
            full_name="Ravi Kafley",
            role="admin",
            tenant_id="tenant-torilaure",
        )
        create_response = self.client.post(
            "/api/v1/market/benchmark-comps",
            headers=headers,
            json={
                "asset_class": "real-estate",
                "location": "Charlotte, NC",
                "source_name": "manual-comp-set",
                "closed_on": str(date(2025, 12, 31)),
                "sale_price": 6100000,
                "net_operating_income": 590000,
                "cap_rate": 9.67,
                "projected_irr": 19.4,
                "equity_multiple": 2.15,
                "average_dscr": 1.42,
                "occupancy_rate": 95.0,
                "leverage_ratio": 58.0,
                "note": "Recent local comp",
            },
        )
        self.assertEqual(create_response.status_code, 201)

        calibration_response = self.client.get(
            "/api/v1/market/benchmark-calibration/real-estate",
            headers=headers,
        )
        self.assertEqual(calibration_response.status_code, 200)
        calibration = calibration_response.json()
        self.assertEqual(calibration["source_mode"], "external_comps")
        self.assertGreaterEqual(calibration["comp_count"], 1)

        analysis_response = self.client.post(
            "/api/v1/projects/proj-roi-sunbelt/roi-scenarios/analyze",
            headers=headers,
            json={
                "name": "Comp-backed analysis",
                "scenario_type": "custom",
                "listing_id": "deal-1001",
                "purchase_price": 6200000,
                "upfront_capex": 450000,
                "annual_revenue": 980000,
                "vacancy_rate": 5,
                "annual_operating_expenses": 320000,
                "annual_capex_reserve": 45000,
                "exit_cap_rate": 6.5,
                "hold_period_years": 5,
                "leverage_ratio": 55,
                "interest_rate": 6,
            },
        )
        self.assertEqual(analysis_response.status_code, 200)
        analysis = analysis_response.json()
        self.assertEqual(
            analysis["analysis"]["benchmark_assessment"]["notes"][1],
            "Benchmark ranges were calibrated from comparable records.",
        )

    def test_investor_cannot_create_roi_scenario(self) -> None:
        response = self.client.post(
            "/api/v1/projects/proj-roi-sunbelt/roi-scenarios",
            headers=self.auth_headers(
                user_id="user-investor-demo",
                email="investor@example.com",
                full_name="Investor Demo",
                role="investor",
                tenant_id="tenant-torilaure",
            ),
            json={
                "name": "Blocked case",
                "scenario_type": "custom",
                "listing_id": "deal-1001",
                "purchase_price": 6200000,
                "upfront_capex": 450000,
                "annual_revenue": 980000,
                "annual_operating_expenses": 320000,
                "annual_revenue_growth_rate": 3,
                "annual_expense_growth_rate": 2,
                "exit_cap_rate": 6.5,
                "exit_cost_rate": 2,
                "hold_period_years": 5,
                "discount_rate": 12,
                "leverage_ratio": 55,
                "interest_rate": 6,
            },
        )

        self.assertEqual(response.status_code, 403)

    def test_admin_can_create_update_and_delete_roi_scenario(self) -> None:
        headers = self.auth_headers(
            user_id="user-ravi-kafley",
            email="founder@example.com",
            full_name="Ravi Kafley",
            role="admin",
            tenant_id="tenant-torilaure",
        )
        create_response = self.client.post(
            "/api/v1/projects/proj-roi-sunbelt/roi-scenarios",
            headers=headers,
            json={
                "name": "New case",
                "scenario_type": "custom",
                "listing_id": "deal-1002",
                "purchase_price": 1480000,
                "upfront_capex": 120000,
                "annual_revenue": 420000,
                "annual_operating_expenses": 170000,
                "annual_revenue_growth_rate": 4,
                "annual_expense_growth_rate": 2.5,
                "exit_cap_rate": 7,
                "exit_cost_rate": 2,
                "hold_period_years": 4,
                "discount_rate": 12,
                "leverage_ratio": 45,
                "interest_rate": 6.5,
            },
        )
        self.assertEqual(create_response.status_code, 201)
        created = create_response.json()
        self.assertEqual(created["listing_id"], "deal-1002")

        update_response = self.client.put(
            f"/api/v1/projects/proj-roi-sunbelt/roi-scenarios/{created['id']}",
            headers=headers,
            json={
                "name": "New case revised",
                "scenario_type": "custom",
                "listing_id": "deal-1002",
                "purchase_price": 1480000,
                "upfront_capex": 120000,
                "annual_revenue": 450000,
                "annual_operating_expenses": 170000,
                "annual_revenue_growth_rate": 4,
                "annual_expense_growth_rate": 2.5,
                "exit_cap_rate": 7,
                "exit_cost_rate": 2,
                "hold_period_years": 4,
                "discount_rate": 12,
                "leverage_ratio": 45,
                "interest_rate": 6.5,
            },
        )
        self.assertEqual(update_response.status_code, 200)
        updated = update_response.json()
        self.assertEqual(updated["name"], "New case revised")
        self.assertGreater(updated["projected_npv"], created["projected_npv"])

        delete_response = self.client.delete(
            f"/api/v1/projects/proj-roi-sunbelt/roi-scenarios/{created['id']}",
            headers=headers,
        )
        self.assertEqual(delete_response.status_code, 204)
        self.assertFalse(any(item.id == created["id"] for item in platform_service._roi_scenarios))


if __name__ == "__main__":
    unittest.main()
