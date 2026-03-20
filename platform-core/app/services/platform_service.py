from __future__ import annotations

from datetime import UTC, datetime
from statistics import mean
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from app.schemas.alert import AlertPreference, AlertPreferenceCreate, AlertPreferenceUpdate
from app.schemas.auth import AuthUser
from app.schemas.document import ProjectDocumentSummary
from app.schemas.listing import DealSearchResponse, ListingCreate, ListingSummary
from app.schemas.market import MarketInsight, MarketInsightCreate
from app.schemas.note import ProjectActivityItem, ProjectNoteCreate, ProjectNoteSummary, ProjectNoteUpdate
from app.schemas.project import (
    PlatformOverview,
    PortfolioSavedViewCreate,
    PortfolioSavedViewSummary,
    PortfolioSavedViewUpdate,
    ProjectCreate,
    ProjectMemberAdd,
    ProjectSummary,
    ProjectWorkspace,
    RoiPortfolioOverview,
    RoiPortfolioProjectExposure,
    RoiPortfolioScenarioView,
    RoiPortfolioStressView,
)
from app.schemas.roi import (
    RoiActualCreate,
    RoiActualSummary,
    RoiBenchmarkCalibrationResponse,
    RoiBenchmarkCompCreate,
    RoiBenchmarkCompInfluence,
    RoiBenchmarkCompSummary,
    RoiBenchmarkCompUpdate,
    RoiPortfolioSnapshot,
    RoiRecommendationDriftResponse,
    RoiRecommendationSummary,
    RoiScenarioAnalysisResponse,
    RoiScenarioBenchmarkContext,
    RoiScenarioCalculationResponse,
    RoiScenarioCreate,
    RoiScenarioInput,
    RoiScenarioRecommendation,
    RoiScenarioSummary,
    RoiSensitivityResponse,
    RoiScenarioUpdate,
    RoiVarianceAnalysis,
    RoiVariancePeriod,
)
from app.services.authorization_service import authorization_service
from app.services.platform_storage_service import platform_storage_service
from app.services.project_document_service import project_document_service
from app.services.roi_analysis_service import roi_analysis_service
from app.services.user_storage_service import user_storage_service


class PlatformService:
    """Application service for platform domains with PostgreSQL as the primary source of truth."""

    def __init__(self) -> None:
        # Keep empty in-memory fallbacks so local development stays resilient if storage is unavailable.
        self._projects: list[ProjectSummary] = []
        self._listings: list[ListingSummary] = []
        self._market_insights: list[MarketInsight] = []
        self._alerts: list[AlertPreference] = []
        self._roi_scenarios: list[RoiScenarioSummary] = []
        self._roi_actuals: list[RoiActualSummary] = []
        self._benchmark_comps: list[RoiBenchmarkCompSummary] = []
        self._roi_recommendations: list[RoiScenarioRecommendation] = []
        self._portfolio_saved_views: list[PortfolioSavedViewSummary] = []

    def list_projects(self, user: AuthUser) -> list[ProjectSummary]:
        """Return all shared projects."""
        projects = self._load_projects()
        return authorization_service.filter_projects(user, projects)

    def get_project(self, project_id: str, user: AuthUser) -> ProjectSummary | None:
        """Return a single project if the caller is authorized to access it."""
        project = self._load_project(project_id)
        if project is None:
            return None
        authorization_service.require_project_access(user, project)
        return project

    def create_project(self, payload: ProjectCreate, user: AuthUser) -> ProjectSummary:
        """Create a draft project until project lifecycle workflows are implemented."""
        authorization_service.require_project_creation(user)
        project = ProjectSummary(
            id=f"proj-{uuid4().hex[:8]}",
            name=payload.name,
            tenant_id=user.tenant_id,
            project_type=payload.project_type,
            owner=payload.owner,
            owner_id=user.id,
            member_ids=[user.id],
            status="draft",
            active_deals=0,
            stage=payload.stage,
            investment_thesis=payload.investment_thesis,
            target_irr=payload.target_irr,
            budget_amount=payload.budget_amount,
        )
        saved_project = self._save_project(project)
        if saved_project is None:
            self._projects.append(project)
            return project
        return saved_project

    def get_project_workspace(self, project_id: str, user: AuthUser) -> ProjectWorkspace:
        """Return a project-scoped workspace bundle for the frontend detail page."""
        project = self.get_project(project_id, user)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
        listings = [listing for listing in self.list_listings(user) if listing.project_id == project_id]
        documents = self.list_project_documents(project_id, user)
        notes = self.list_project_notes(project_id, user)
        roi_scenarios = self.list_project_roi_scenarios(project_id, user)
        return ProjectWorkspace(
            project=project,
            members=self.list_project_members(project_id, user),
            listings=listings,
            market_insights=self.get_market_insights(user),
            alerts=self.list_alerts(user),
            documents=documents,
            notes=notes,
            roi_scenarios=roi_scenarios,
            roi_snapshot=self.get_project_roi_snapshot(project_id, user),
            activity=self._build_project_activity(project, documents, notes),
        )

    def list_project_roi_scenarios(self, project_id: str, user: AuthUser) -> list[RoiScenarioSummary]:
        project = self.get_project(project_id, user)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
        if platform_storage_service.is_available():
            try:
                return platform_storage_service.list_project_roi_scenarios(user.tenant_id, project_id)
            except SQLAlchemyError:
                pass
        return [scenario for scenario in self._roi_scenarios if scenario.project_id == project_id and scenario.tenant_id == user.tenant_id]

    def get_project_roi_snapshot(self, project_id: str, user: AuthUser) -> RoiPortfolioSnapshot:
        scenarios = self.list_project_roi_scenarios(project_id, user)
        base_case = next((item for item in scenarios if item.scenario_type == "base"), None)
        upside_case = next((item for item in scenarios if item.scenario_type == "upside"), None)
        downside_case = next((item for item in scenarios if item.scenario_type == "downside"), None)
        irr_values = [item.projected_irr for item in scenarios if item.projected_irr is not None]
        npv_values = [item.projected_npv for item in scenarios]
        rankings = sorted(
            [roi_analysis_service.build_ranking_item(item) for item in scenarios],
            key=lambda item: item.risk_adjusted_score,
            reverse=True,
        )
        top_ranked = rankings[0] if rankings else None
        return RoiPortfolioSnapshot(
            scenario_count=len(scenarios),
            base_case_irr=base_case.projected_irr if base_case else None,
            upside_case_irr=upside_case.projected_irr if upside_case else None,
            downside_case_irr=downside_case.projected_irr if downside_case else None,
            best_case_irr=max(irr_values) if irr_values else None,
            average_npv=round(mean(npv_values), 2) if npv_values else None,
            best_equity_multiple=max(
                [item.equity_multiple for item in scenarios if item.equity_multiple is not None],
                default=None,
            ),
            average_dscr=round(
                mean([item.average_dscr for item in scenarios if item.average_dscr is not None]),
                3,
            )
            if any(item.average_dscr is not None for item in scenarios)
            else None,
            best_risk_adjusted_scenario_id=top_ranked.scenario_id if top_ranked else None,
            best_risk_adjusted_scenario_name=top_ranked.scenario_name if top_ranked else None,
            best_risk_adjusted_score=top_ranked.risk_adjusted_score if top_ranked else None,
            scenario_rankings=rankings,
        )

    def list_project_roi_recommendations(self, project_id: str, scenario_id: str, user: AuthUser) -> list[RoiScenarioRecommendation]:
        project = self.get_project(project_id, user)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
        authorization_service.require_project_access(user, project)
        return [
            rec
            for rec in self._roi_recommendations
            if rec.project_id == project_id and rec.tenant_id == user.tenant_id and rec.scenario_id == scenario_id
        ]

    def create_project_roi_recommendation(self, project_id: str, scenario_id: str, user: AuthUser) -> RoiScenarioRecommendation:
        project = self.get_project(project_id, user)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
        authorization_service.require_project_access(user, project)
        scenario = self.get_project_roi_scenario(project_id, scenario_id, user)
        if scenario is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ROI scenario not found.")
        payload = RoiScenarioInput.model_validate(scenario.model_dump())
        analysis = roi_analysis_service.build_analysis(payload)
        recommendation = roi_analysis_service.build_recommendation(payload, analysis)
        rec = RoiScenarioRecommendation(
            scenario_id=scenario_id,
            project_id=project_id,
            tenant_id=user.tenant_id,
            created_by=user.id,
            created_at=datetime.now(UTC),
            recommendation=recommendation,
        )
        if platform_storage_service.is_available():
            try:
                return platform_storage_service.create_project_roi_recommendation(rec)
            except SQLAlchemyError:
                pass
        self._roi_recommendations.append(rec)
        return rec

    def list_project_roi_recommendations(self, project_id: str, scenario_id: str, user: AuthUser) -> list[RoiScenarioRecommendation]:
        project = self.get_project(project_id, user)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
        authorization_service.require_project_access(user, project)
        if platform_storage_service.is_available():
            try:
                return platform_storage_service.list_project_roi_recommendations(
                    tenant_id=user.tenant_id,
                    project_id=project_id,
                    scenario_id=scenario_id,
                )
            except SQLAlchemyError:
                pass
        return [
            rec
            for rec in self._roi_recommendations
            if rec.project_id == project_id and rec.tenant_id == user.tenant_id and rec.scenario_id == scenario_id
        ]

    def get_project_roi_recommendations_pdf(self, project_id: str, scenario_id: str, user: AuthUser) -> bytes:
        from io import BytesIO

        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

        recommendations = self.list_project_roi_recommendations(project_id, scenario_id, user)
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        flowables = []

        flowables.append(Paragraph("ROI Scenario Recommendations", styles["Title"]))
        flowables.append(Spacer(1, 16))
        flowables.append(Paragraph(f"Project: {project_id}", styles["Normal"]))
        flowables.append(Paragraph(f"Scenario: {scenario_id}", styles["Normal"]))
        flowables.append(Spacer(1, 12))

        if not recommendations:
            flowables.append(Paragraph("No recommendations available.", styles["Normal"]))
        else:
            for idx, rec in enumerate(recommendations, start=1):
                flowables.append(Paragraph(f"Recommendation #{idx}", styles["Heading2"]))
                rec_summary = rec.recommendation
                flowables.append(Paragraph(f"Decision: {rec_summary.recommendation}", styles["Normal"]))
                flowables.append(Paragraph(f"Conviction: {rec_summary.conviction}", styles["Normal"]))
                flowables.append(Paragraph(f"Score: {rec_summary.score:.2f}", styles["Normal"]))
                flowables.append(Paragraph("Rationale:", styles["Normal"]))
                for rationale in rec_summary.rationale:
                    flowables.append(Paragraph(f"- {rationale}", styles["Bullet"]))
                flowables.append(Paragraph("Required assumption checks:", styles["Normal"]))
                for check in rec_summary.required_assumption_checks:
                    flowables.append(Paragraph(f"- {check}", styles["Bullet"]))
                if rec_summary.action_items:
                    flowables.append(Paragraph("Action items:", styles["Normal"]))
                    for item in rec_summary.action_items:
                        flowables.append(Paragraph(f"- {item}", styles["Bullet"]))
                flowables.append(Spacer(1, 12))

        doc.build(flowables)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes

    def calculate_project_roi_scenario(
        self,
        project_id: str,
        payload: RoiScenarioInput,
        user: AuthUser,
    ) -> RoiScenarioCalculationResponse:
        project = self.get_project(project_id, user)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
        self._validate_roi_listing(project_id, payload.listing_id, user)
        scenario = roi_analysis_service.to_summary(
            scenario_id="preview",
            project_id=project_id,
            tenant_id=user.tenant_id,
            payload=payload,
        )
        computed = roi_analysis_service.calculate(payload)
        benchmark_profile, benchmark_location = self._resolve_benchmark_context(payload.listing_id, user)
        benchmark_ranges = self._resolve_calibrated_benchmark_ranges(benchmark_profile, user, benchmark_location)
        analysis = roi_analysis_service.build_analysis(payload, computed, benchmark_profile, benchmark_ranges)
        return RoiScenarioCalculationResponse(
            scenario=scenario,
            annual_cash_flows=computed.annual_cash_flows,
            monthly_cash_flows=computed.monthly_cash_flows,
            analysis=analysis,
            recommendation=roi_analysis_service.build_recommendation(payload, analysis, computed),
        )

    def analyze_project_roi_scenario(
        self,
        project_id: str,
        payload: RoiScenarioInput,
        user: AuthUser,
    ) -> RoiScenarioAnalysisResponse:
        project = self.get_project(project_id, user)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
        self._validate_roi_listing(project_id, payload.listing_id, user)
        scenario = roi_analysis_service.to_summary(
            scenario_id="preview",
            project_id=project_id,
            tenant_id=user.tenant_id,
            payload=payload,
        )
        computed = roi_analysis_service.calculate(payload)
        benchmark_profile, benchmark_location = self._resolve_benchmark_context(payload.listing_id, user)
        benchmark_ranges = self._resolve_calibrated_benchmark_ranges(benchmark_profile, user, benchmark_location)
        analysis = roi_analysis_service.build_analysis(payload, computed, benchmark_profile, benchmark_ranges)
        benchmark_context = self._build_scenario_benchmark_context(benchmark_profile, user, benchmark_location)
        return RoiScenarioAnalysisResponse(
            scenario=scenario,
            analysis=analysis,
            recommendation=roi_analysis_service.build_recommendation(payload, analysis, computed),
            benchmark_context=benchmark_context,
        )

    def list_benchmark_comps(self, user: AuthUser, asset_class: str | None = None) -> list[RoiBenchmarkCompSummary]:
        authorization_service.require_tenant_editor(user)
        return self._list_benchmark_comps_for_tenant(user, asset_class)

    def _list_benchmark_comps_for_tenant(self, user: AuthUser, asset_class: str | None = None) -> list[RoiBenchmarkCompSummary]:
        if platform_storage_service.is_available():
            try:
                return platform_storage_service.list_benchmark_comps(user.tenant_id, asset_class)
            except SQLAlchemyError:
                pass
        comps = [item for item in self._benchmark_comps if item.tenant_id == user.tenant_id]
        if asset_class:
            comps = [item for item in comps if item.asset_class == asset_class]
        return comps

    def create_benchmark_comp(self, payload: RoiBenchmarkCompCreate, user: AuthUser) -> RoiBenchmarkCompSummary:
        authorization_service.require_tenant_editor(user)
        comp = RoiBenchmarkCompSummary(
            id=f"comp-{uuid4().hex[:8]}",
            tenant_id=user.tenant_id,
            included=True,
            override_mode="normal",
            **payload.model_dump(),
        )
        if platform_storage_service.is_available():
            try:
                return platform_storage_service.create_benchmark_comp(comp)
            except SQLAlchemyError:
                pass
        self._benchmark_comps.append(comp)
        return comp

    def update_benchmark_comp(self, comp_id: str, payload: RoiBenchmarkCompUpdate, user: AuthUser) -> RoiBenchmarkCompSummary:
        authorization_service.require_tenant_editor(user)
        if platform_storage_service.is_available():
            try:
                updated = platform_storage_service.update_benchmark_comp(user.tenant_id, comp_id, payload)
            except SQLAlchemyError:
                updated = None
            if updated is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Benchmark comp not found.")
            return updated
        for index, comp in enumerate(self._benchmark_comps):
            if comp.id == comp_id and comp.tenant_id == user.tenant_id:
                updated = comp.model_copy(
                    update={
                        "included": payload.included,
                        "override_mode": payload.override_mode,
                        "note": payload.note if payload.note is not None else comp.note,
                    }
                )
                self._benchmark_comps[index] = updated
                return updated
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Benchmark comp not found.")

    def get_benchmark_calibration(self, asset_class: str, user: AuthUser, location: str | None = None) -> RoiBenchmarkCalibrationResponse:
        authorization_service.require_tenant_editor(user)
        comps = [comp for comp in self.list_benchmark_comps(user, asset_class) if comp.included]
        _, calibration = roi_analysis_service.calibrate_benchmark_profile(asset_class, comps, location)
        return calibration

    def list_project_roi_actuals(self, project_id: str, scenario_id: str, user: AuthUser) -> list[RoiActualSummary]:
        project = self.get_project(project_id, user)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
        scenario = self.get_project_roi_scenario(project_id, scenario_id, user)
        if scenario is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ROI scenario not found.")
        if platform_storage_service.is_available():
            try:
                return platform_storage_service.list_project_roi_actuals(
                    tenant_id=user.tenant_id,
                    project_id=project_id,
                    scenario_id=scenario_id,
                )
            except SQLAlchemyError:
                pass
        return [
            item for item in self._roi_actuals
            if item.project_id == project_id and item.scenario_id == scenario_id and item.tenant_id == user.tenant_id
        ]

    def create_project_roi_actual(
        self,
        project_id: str,
        scenario_id: str,
        payload: RoiActualCreate,
        user: AuthUser,
    ) -> RoiActualSummary:
        project = self.get_project(project_id, user)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
        authorization_service.require_project_management(user, project)
        scenario = self.get_project_roi_scenario(project_id, scenario_id, user)
        if scenario is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ROI scenario not found.")
        actual = RoiActualSummary(
            id=f"roi-actual-{uuid4().hex[:8]}",
            project_id=project_id,
            tenant_id=user.tenant_id,
            scenario_id=scenario_id,
            **payload.model_dump(),
        )
        if platform_storage_service.is_available():
            try:
                return platform_storage_service.create_project_roi_actual(actual)
            except SQLAlchemyError:
                pass
        self._roi_actuals.append(actual)
        self._roi_actuals.sort(key=lambda item: item.period_start)
        return actual

    def build_project_roi_variance_analysis(
        self,
        project_id: str,
        scenario_id: str,
        user: AuthUser,
    ) -> RoiVarianceAnalysis:
        scenario = self.get_project_roi_scenario(project_id, scenario_id, user)
        if scenario is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ROI scenario not found.")
        actuals = self.list_project_roi_actuals(project_id, scenario_id, user)
        computed = roi_analysis_service.calculate(RoiScenarioInput.model_validate(scenario.model_dump()))
        monthly_expectations = computed.monthly_cash_flows
        periods: list[RoiVariancePeriod] = []
        for index, actual in enumerate(sorted(actuals, key=lambda item: item.period_start), start=1):
            if index > len(monthly_expectations):
                break
            expected = monthly_expectations[index - 1]
            actual_noi = actual.effective_revenue - actual.operating_expenses - actual.capex
            expected_noi = expected.net_operating_income - expected.capex_reserve
            expected_occupancy = max(0.0, 100 - scenario.vacancy_rate)
            periods.append(
                RoiVariancePeriod(
                    period_start=actual.period_start,
                    month_index=index,
                    actual_revenue=actual.effective_revenue,
                    expected_revenue=expected.effective_revenue,
                    revenue_variance=round(actual.effective_revenue - expected.effective_revenue, 2),
                    actual_operating_expenses=actual.operating_expenses,
                    expected_operating_expenses=expected.operating_expenses,
                    expense_variance=round(actual.operating_expenses - expected.operating_expenses, 2),
                    actual_noi=round(actual_noi, 2),
                    expected_noi=round(expected_noi, 2),
                    noi_variance=round(actual_noi - expected_noi, 2),
                    actual_debt_service=actual.debt_service,
                    expected_debt_service=expected.debt_service,
                    debt_service_variance=round(actual.debt_service - expected.debt_service, 2),
                    actual_occupancy_rate=actual.occupancy_rate,
                    expected_occupancy_rate=round(expected_occupancy, 2) if actual.occupancy_rate is not None else None,
                    occupancy_variance=round(actual.occupancy_rate - expected_occupancy, 2)
                    if actual.occupancy_rate is not None
                    else None,
                )
            )
        total_revenue_variance = round(sum(item.revenue_variance for item in periods), 2)
        total_expense_variance = round(sum(item.expense_variance for item in periods), 2)
        total_noi_variance = round(sum(item.noi_variance for item in periods), 2)
        occupancy_variances = [item.occupancy_variance for item in periods if item.occupancy_variance is not None]
        summary: list[str] = []
        if total_revenue_variance < 0:
            summary.append("Realized revenue is trailing the underwriting path.")
        elif total_revenue_variance > 0:
            summary.append("Realized revenue is outperforming underwriting so far.")
        if total_expense_variance > 0:
            summary.append("Operating expenses are running above plan.")
        if total_noi_variance < 0:
            summary.append("NOI underperformance suggests the business plan may need to be revised.")
        elif total_noi_variance > 0:
            summary.append("NOI is outperforming the original underwriting.")
        return RoiVarianceAnalysis(
            periods=periods,
            total_revenue_variance=total_revenue_variance,
            total_expense_variance=total_expense_variance,
            total_noi_variance=total_noi_variance,
            average_occupancy_variance=round(mean(occupancy_variances), 2) if occupancy_variances else None,
            variance_summary=summary or ["No actual periods have been recorded yet."],
        )

    def build_project_roi_recommendation_drift(
        self,
        project_id: str,
        scenario_id: str,
        user: AuthUser,
    ) -> RoiRecommendationDriftResponse:
        scenario = self.get_project_roi_scenario(project_id, scenario_id, user)
        if scenario is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ROI scenario not found.")

        base_payload = RoiScenarioInput.model_validate(scenario.model_dump())
        original_computed = roi_analysis_service.calculate(base_payload)
        original_analysis = roi_analysis_service.build_analysis(base_payload, original_computed)
        original_recommendation = roi_analysis_service.build_recommendation(
            base_payload,
            original_analysis,
            original_computed,
        )

        actuals = self.list_project_roi_actuals(project_id, scenario_id, user)
        if not actuals:
            return RoiRecommendationDriftResponse(
                original_recommendation=original_recommendation,
                reforecast_recommendation=original_recommendation,
                drift_status="stable",
                recommended_action="maintain",
                actual_months_recorded=0,
                confidence="low",
                summary=["No actual operating periods have been recorded yet, so the original recommendation still stands."],
                reforecast_scenario=scenario,
            )

        actuals = sorted(actuals, key=lambda item: item.period_start)
        computed = roi_analysis_service.calculate(base_payload)
        expectations = computed.monthly_cash_flows[: len(actuals)]
        weight = min(len(actuals), 12) / 12

        avg_actual_revenue = mean(item.effective_revenue for item in actuals)
        avg_actual_operating_expenses = mean(item.operating_expenses for item in actuals)
        avg_actual_capex = mean(item.capex for item in actuals)
        occupancy_points = [item.occupancy_rate for item in actuals if item.occupancy_rate is not None]
        avg_actual_occupancy = mean(occupancy_points) if occupancy_points else None

        avg_expected_revenue = mean(item.effective_revenue for item in expectations) if expectations else scenario.annual_revenue / 12
        avg_expected_operating_expenses = (
            mean(item.operating_expenses for item in expectations) if expectations else scenario.annual_operating_expenses / 12
        )
        avg_expected_capex = mean(item.capex_reserve for item in expectations) if expectations else scenario.annual_capex_reserve / 12

        realized_annual_revenue = avg_actual_revenue * 12
        realized_annual_operating_expenses = avg_actual_operating_expenses * 12
        realized_annual_capex = avg_actual_capex * 12

        blended_revenue = scenario.annual_revenue * (1 - weight) + realized_annual_revenue * weight
        blended_operating_expenses = scenario.annual_operating_expenses * (1 - weight) + realized_annual_operating_expenses * weight
        blended_capex = scenario.annual_capex_reserve * (1 - weight) + realized_annual_capex * weight

        blended_vacancy_rate = scenario.vacancy_rate
        if avg_actual_occupancy is not None:
            blended_vacancy_rate = min(max(scenario.vacancy_rate * (1 - weight) + max(0.0, 100 - avg_actual_occupancy) * weight, 0.0), 100.0)

        remaining_hold_period = max(scenario.hold_period_years - (len(actuals) // 12), 1)
        reforecast_payload = base_payload.model_copy(
            update={
                "name": f"{scenario.name} reforecast",
                "annual_revenue": round(blended_revenue, 2),
                "annual_operating_expenses": round(blended_operating_expenses, 2),
                "annual_capex_reserve": round(blended_capex, 2),
                "vacancy_rate": round(blended_vacancy_rate, 2),
                "hold_period_years": remaining_hold_period,
            }
        )

        reforecast_computed = roi_analysis_service.calculate(reforecast_payload)
        reforecast_analysis = roi_analysis_service.build_analysis(reforecast_payload, reforecast_computed)
        reforecast_recommendation = roi_analysis_service.build_recommendation(
            reforecast_payload,
            reforecast_analysis,
            reforecast_computed,
        )
        reforecast_scenario = roi_analysis_service.to_summary(
            scenario_id=f"{scenario.id}-reforecast",
            project_id=project_id,
            tenant_id=user.tenant_id,
            payload=reforecast_payload,
        )

        decision_rank = {"reject": 0, "watch": 1, "invest": 2}
        original_rank = decision_rank[original_recommendation.recommendation]
        reforecast_rank = decision_rank[reforecast_recommendation.recommendation]
        if reforecast_rank > original_rank:
            drift_status = "improving"
            recommended_action = "upgrade"
        elif reforecast_rank < original_rank:
            drift_status = "deteriorating"
            recommended_action = "downgrade"
        else:
            drift_status = "stable"
            recommended_action = "maintain"

        confidence = "low"
        if len(actuals) >= 6:
            confidence = "medium"
        if len(actuals) >= 12:
            confidence = "high"

        summary: list[str] = []
        revenue_delta = avg_actual_revenue - avg_expected_revenue
        expense_delta = avg_actual_operating_expenses - avg_expected_operating_expenses
        capex_delta = avg_actual_capex - avg_expected_capex
        if revenue_delta < 0:
            summary.append("Trailing realized revenue is below the original underwriting run-rate.")
        elif revenue_delta > 0:
            summary.append("Trailing realized revenue is ahead of the original underwriting run-rate.")
        if expense_delta > 0:
            summary.append("Trailing operating expenses are higher than planned.")
        elif expense_delta < 0:
            summary.append("Trailing operating expenses are running below plan.")
        if capex_delta > 0:
            summary.append("Recorded capex is tracking above the reserved underwriting path.")
        if avg_actual_occupancy is not None:
            expected_occupancy = 100 - scenario.vacancy_rate
            if avg_actual_occupancy < expected_occupancy:
                summary.append("Observed occupancy is below the original stabilization assumption.")
            elif avg_actual_occupancy > expected_occupancy:
                summary.append("Observed occupancy is outperforming the original plan.")
        if recommended_action == "downgrade":
            summary.append("The actuals-adjusted reforecast indicates the scenario should be downgraded.")
        elif recommended_action == "upgrade":
            summary.append("The actuals-adjusted reforecast supports an improved recommendation if execution remains durable.")
        else:
            summary.append("The actuals-adjusted reforecast does not change the current recommendation.")

        return RoiRecommendationDriftResponse(
            original_recommendation=original_recommendation,
            reforecast_recommendation=reforecast_recommendation,
            drift_status=drift_status,
            recommended_action=recommended_action,
            actual_months_recorded=len(actuals),
            confidence=confidence,
            summary=summary[:5],
            reforecast_scenario=reforecast_scenario,
        )

    def build_project_roi_sensitivity(
        self,
        project_id: str,
        payload: RoiScenarioInput,
        user: AuthUser,
    ) -> RoiSensitivityResponse:
        project = self.get_project(project_id, user)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
        self._validate_roi_listing(project_id, payload.listing_id, user)
        return roi_analysis_service.build_sensitivity(payload)

    def create_project_roi_scenario(
        self,
        project_id: str,
        payload: RoiScenarioCreate,
        user: AuthUser,
    ) -> RoiScenarioSummary:
        project = self.get_project(project_id, user)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
        authorization_service.require_project_management(user, project)
        self._validate_roi_listing(project_id, payload.listing_id, user)
        scenario = roi_analysis_service.to_summary(
            scenario_id=f"roi-{uuid4().hex[:8]}",
            project_id=project_id,
            tenant_id=user.tenant_id,
            payload=payload,
        )
        if platform_storage_service.is_available():
            try:
                return platform_storage_service.create_project_roi_scenario(scenario)
            except SQLAlchemyError:
                pass
        self._roi_scenarios.append(scenario)
        return scenario

    def update_project_roi_scenario(
        self,
        project_id: str,
        scenario_id: str,
        payload: RoiScenarioUpdate,
        user: AuthUser,
    ) -> RoiScenarioSummary:
        project = self.get_project(project_id, user)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
        authorization_service.require_project_management(user, project)
        self._validate_roi_listing(project_id, payload.listing_id, user)
        scenario = roi_analysis_service.to_summary(
            scenario_id=scenario_id,
            project_id=project_id,
            tenant_id=user.tenant_id,
            payload=payload,
        )
        if platform_storage_service.is_available():
            try:
                updated = platform_storage_service.update_project_roi_scenario(scenario)
            except SQLAlchemyError:
                updated = None
            if updated is not None:
                return updated
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ROI scenario not found.")
        for index, current in enumerate(self._roi_scenarios):
            if current.id == scenario_id and current.project_id == project_id and current.tenant_id == user.tenant_id:
                self._roi_scenarios[index] = scenario
                return scenario
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ROI scenario not found.")

    def delete_project_roi_scenario(self, project_id: str, scenario_id: str, user: AuthUser) -> None:
        project = self.get_project(project_id, user)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
        authorization_service.require_project_management(user, project)
        if platform_storage_service.is_available():
            try:
                deleted = platform_storage_service.delete_project_roi_scenario(
                    tenant_id=user.tenant_id,
                    project_id=project_id,
                    scenario_id=scenario_id,
                )
            except SQLAlchemyError:
                deleted = False
            if deleted:
                return
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ROI scenario not found.")
        for index, current in enumerate(self._roi_scenarios):
            if current.id == scenario_id and current.project_id == project_id and current.tenant_id == user.tenant_id:
                self._roi_scenarios.pop(index)
                return
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ROI scenario not found.")

    def list_project_documents(self, project_id: str, user: AuthUser) -> list[ProjectDocumentSummary]:
        """Return metadata for documents attached to a project the user can access."""
        project = self.get_project(project_id, user)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
        return project_document_service.list_project_documents(project_id=project_id, tenant_id=user.tenant_id)

    def list_project_notes(self, project_id: str, user: AuthUser) -> list[ProjectNoteSummary]:
        """Return notes attached to a project the user can access."""
        project = self.get_project(project_id, user)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
        if platform_storage_service.is_available():
            try:
                return platform_storage_service.list_project_notes(user.tenant_id, project_id)
            except SQLAlchemyError:
                pass
        return []

    def create_project_note(self, project_id: str, payload: ProjectNoteCreate, user: AuthUser) -> ProjectNoteSummary:
        """Persist a note into a project workspace for an authorized user."""
        project = self.get_project(project_id, user)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
        if platform_storage_service.is_available():
            try:
                return platform_storage_service.create_project_note(
                    project_id=project_id,
                    tenant_id=user.tenant_id,
                    author_id=user.id,
                    author_name=user.full_name,
                    content=payload.content.strip(),
                )
            except SQLAlchemyError:
                pass
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Project note storage is not available.")

    def update_project_note(
        self,
        project_id: str,
        note_id: str,
        payload: ProjectNoteUpdate,
        user: AuthUser,
    ) -> ProjectNoteSummary:
        """Update a project note for an authorized user."""
        project = self.get_project(project_id, user)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
        if platform_storage_service.is_available():
            try:
                note = platform_storage_service.get_project_note(
                    tenant_id=user.tenant_id,
                    project_id=project_id,
                    note_id=note_id,
                )
                if note is None:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project note not found.")
                authorization_service.require_project_note_management(user, project, note)
                updated = platform_storage_service.update_project_note(
                    tenant_id=user.tenant_id,
                    project_id=project_id,
                    note_id=note_id,
                    content=payload.content.strip(),
                )
            except SQLAlchemyError:
                updated = None
            if updated is not None:
                return updated
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project note not found.")

    def delete_project_note(self, project_id: str, note_id: str, user: AuthUser) -> None:
        """Delete a project note for an authorized user."""
        project = self.get_project(project_id, user)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
        if platform_storage_service.is_available():
            try:
                note = platform_storage_service.get_project_note(
                    tenant_id=user.tenant_id,
                    project_id=project_id,
                    note_id=note_id,
                )
                if note is None:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project note not found.")
                authorization_service.require_project_note_management(user, project, note)
                deleted = platform_storage_service.delete_project_note(
                    tenant_id=user.tenant_id,
                    project_id=project_id,
                    note_id=note_id,
                )
            except SQLAlchemyError:
                deleted = False
            if deleted:
                return
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project note not found.")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Project note storage is not available.")

    def list_project_members(self, project_id: str, user: AuthUser) -> list[AuthUser]:
        """Return users attached to a project that the caller can access."""
        project = self.get_project(project_id, user)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
        if platform_storage_service.is_available():
            try:
                return platform_storage_service.list_project_members(user.tenant_id, project_id)
            except SQLAlchemyError:
                pass
        tenant_users = {item["id"]: item for item in user_storage_service.list_tenant_users(user.tenant_id)}
        return [
            AuthUser(
                id=tenant_users[user_id]["id"],
                email=tenant_users[user_id]["email"],
                full_name=tenant_users[user_id]["full_name"],
                role=tenant_users[user_id]["role"],
                tenant_id=tenant_users[user_id]["tenant_id"],
            )
            for user_id in project.member_ids
            if user_id in tenant_users
        ]

    def add_project_member(self, project_id: str, payload: ProjectMemberAdd, user: AuthUser) -> AuthUser:
        """Add an existing tenant user to a project."""
        project = self.get_project(project_id, user)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
        authorization_service.require_project_management(user, project)
        member = user_storage_service.find_by_email(payload.email)
        if member is None or member["tenant_id"] != user.tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant user not found for that email.")
        if platform_storage_service.is_available():
            try:
                return platform_storage_service.add_project_member(
                    project_id=project_id,
                    tenant_id=user.tenant_id,
                    user_id=member["id"],
                )
            except SQLAlchemyError:
                pass
        if member["id"] not in project.member_ids:
            project.member_ids.append(member["id"])
        return AuthUser(
            id=member["id"],
            email=member["email"],
            full_name=member["full_name"],
            role=member["role"],
            tenant_id=member["tenant_id"],
        )

    def remove_project_member(self, project_id: str, member_user_id: str, user: AuthUser) -> None:
        """Remove a non-owner member from a project."""
        project = self.get_project(project_id, user)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
        authorization_service.require_project_management(user, project)
        if member_user_id == project.owner_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The project owner cannot be removed from membership.")
        if platform_storage_service.is_available():
            try:
                removed = platform_storage_service.remove_project_member(project_id=project_id, user_id=member_user_id)
            except SQLAlchemyError:
                removed = False
            if not removed:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project member not found.")
            return
        if member_user_id not in project.member_ids:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project member not found.")
        project.member_ids = [user_id for user_id in project.member_ids if user_id != member_user_id]

    def list_listings(self, user: AuthUser) -> list[ListingSummary]:
        """Return the current opportunity catalog."""
        records = self._load_listings(user)
        return records

    def create_listing(self, payload: ListingCreate, user: AuthUser) -> ListingSummary:
        """Create a tenant-scoped listing record in the business catalog."""
        authorization_service.require_tenant_editor(user)
        if payload.project_id:
            project = self.get_project(payload.project_id, user)
            if project is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
        if platform_storage_service.is_available():
            try:
                return platform_storage_service.create_listing(user.tenant_id, payload)
            except SQLAlchemyError:
                pass
        listing = ListingSummary(
            id=f"deal-{uuid4().hex[:8]}",
            project_id=payload.project_id,
            title=payload.title,
            asset_class=payload.asset_class,
            location=payload.location,
            asking_price=payload.asking_price,
            projected_irr=payload.projected_irr,
            deal_score=payload.deal_score,
            summary=payload.summary,
            risk_level=payload.risk_level,
            occupancy_rate=payload.occupancy_rate,
            hold_period_months=payload.hold_period_months,
            status=payload.status,
        )
        self._listings.append(listing)
        return listing

    def search_listings(self, query: str, user: AuthUser) -> DealSearchResponse:
        """Use local text matching as a stand-in for future semantic search."""
        normalized = query.strip().lower()
        scoped_listings = self.list_listings(user)
        if not normalized:
            results = scoped_listings
        else:
            results = [
                listing
                for listing in scoped_listings
                if normalized in listing.title.lower()
                or normalized in listing.location.lower()
                or normalized in listing.asset_class.lower()
                or normalized in listing.summary.lower()
            ]
        return DealSearchResponse(query=query, total=len(results), results=results)

    def get_market_insights(self, user: AuthUser) -> list[MarketInsight]:
        """Return region-level market observations."""
        return self._load_market_insights(user)

    def create_market_insight(self, payload: MarketInsightCreate, user: AuthUser) -> MarketInsight:
        """Create a market insight for the caller's tenant."""
        authorization_service.require_tenant_editor(user)
        if platform_storage_service.is_available():
            try:
                return platform_storage_service.create_market_insight(user.tenant_id, payload)
            except SQLAlchemyError:
                pass
        insight = MarketInsight(
            id=f"insight-{uuid4().hex[:8]}",
            region=payload.region,
            signal=payload.signal,
            trend=payload.trend,
            confidence=payload.confidence,
            source=payload.source,
            as_of_date=payload.as_of_date,
        )
        self._market_insights.append(insight)
        return insight

    def list_alerts(self, user: AuthUser) -> list[AlertPreference]:
        """Return the active notification preferences."""
        return self._load_alerts(user)

    def list_portfolio_saved_views(self, user: AuthUser) -> list[PortfolioSavedViewSummary]:
        authorization_service.require_project_creation(user)
        if platform_storage_service.is_available():
            try:
                return platform_storage_service.list_portfolio_saved_views(user.tenant_id, user.id)
            except SQLAlchemyError:
                pass
        return [
            item
            for item in self._portfolio_saved_views
            if item.tenant_id == user.tenant_id and (item.is_shared or item.created_by == user.id)
        ]

    def create_portfolio_saved_view(self, payload: PortfolioSavedViewCreate, user: AuthUser) -> PortfolioSavedViewSummary:
        authorization_service.require_project_creation(user)
        if platform_storage_service.is_available():
            try:
                return platform_storage_service.create_portfolio_saved_view(
                    user.tenant_id,
                    user.id,
                    user.full_name,
                    payload,
                )
            except SQLAlchemyError:
                pass
        view = PortfolioSavedViewSummary(
            id=f"portfolio-view-{uuid4().hex[:8]}",
            tenant_id=user.tenant_id,
            created_by=user.id,
            created_by_name=user.full_name,
            name=payload.name,
            portfolio_view=payload.portfolio_view,
            is_shared=payload.is_shared,
            created_at=datetime.now(UTC),
        )
        self._portfolio_saved_views.append(view)
        return view

    def delete_portfolio_saved_view(self, view_id: str, user: AuthUser) -> None:
        authorization_service.require_project_creation(user)
        if platform_storage_service.is_available():
            try:
                deleted = platform_storage_service.delete_portfolio_saved_view(user.tenant_id, user.id, view_id)
            except SQLAlchemyError:
                deleted = False
            if deleted:
                return
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio saved view not found.")
        for index, item in enumerate(self._portfolio_saved_views):
            if item.id == view_id and item.tenant_id == user.tenant_id and item.created_by == user.id:
                self._portfolio_saved_views.pop(index)
                return
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio saved view not found.")

    def update_portfolio_saved_view(
        self,
        view_id: str,
        payload: PortfolioSavedViewUpdate,
        user: AuthUser,
    ) -> PortfolioSavedViewSummary:
        authorization_service.require_project_creation(user)
        if platform_storage_service.is_available():
            try:
                updated = platform_storage_service.update_portfolio_saved_view(user.tenant_id, user.id, view_id, payload)
            except SQLAlchemyError:
                updated = None
            if updated is not None:
                return updated
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio saved view not found.")
        for index, item in enumerate(self._portfolio_saved_views):
            if item.id == view_id and item.tenant_id == user.tenant_id and item.created_by == user.id:
                updated = item.model_copy(update=payload.model_dump())
                self._portfolio_saved_views[index] = updated
                return updated
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio saved view not found.")

    def create_alert(self, payload: AlertPreferenceCreate, user: AuthUser) -> AlertPreference:
        """Create a tenant-scoped alert rule."""
        authorization_service.require_tenant_editor(user)
        if platform_storage_service.is_available():
            try:
                return platform_storage_service.create_alert(user.tenant_id, payload)
            except SQLAlchemyError:
                pass
        alert = AlertPreference(
            id=f"alert-{uuid4().hex[:8]}",
            name=payload.name,
            channel=payload.channel,
            trigger=payload.trigger,
            enabled=payload.enabled,
            scope=payload.scope,
            severity=payload.severity,
        )
        self._alerts.append(alert)
        return alert

    def update_alert(self, alert_id: str, payload: AlertPreferenceUpdate, user: AuthUser) -> AlertPreference:
        """Update a tenant-scoped alert rule."""
        authorization_service.require_tenant_editor(user)
        if platform_storage_service.is_available():
            try:
                updated = platform_storage_service.update_alert(user.tenant_id, alert_id, payload)
            except SQLAlchemyError:
                updated = None
            if updated is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert rule not found.")
            return updated
        for index, alert in enumerate(self._alerts):
            if alert.id == alert_id:
                updated = AlertPreference(id=alert_id, **payload.model_dump())
                self._alerts[index] = updated
                return updated
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert rule not found.")

    def delete_alert(self, alert_id: str, user: AuthUser) -> None:
        """Delete a tenant-scoped alert rule."""
        authorization_service.require_tenant_editor(user)
        if platform_storage_service.is_available():
            try:
                deleted = platform_storage_service.delete_alert(user.tenant_id, alert_id)
            except SQLAlchemyError:
                deleted = False
            if not deleted:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert rule not found.")
            return
        for index, alert in enumerate(self._alerts):
            if alert.id == alert_id:
                self._alerts.pop(index)
                return
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert rule not found.")

    def get_overview(self, user: AuthUser) -> PlatformOverview:
        """Build summary metrics for the main dashboard."""
        visible_projects = self.list_projects(user)
        visible_listings = self.list_listings(user)
        return PlatformOverview(
            total_projects=len(visible_projects),
            total_listings=len(visible_listings),
            average_deal_score=round(mean(item.deal_score for item in visible_listings), 1) if visible_listings else 0,
            featured_deals=sorted(visible_listings, key=lambda item: item.deal_score, reverse=True)[:3],
            market_insights=self.get_market_insights(user),
            roi_portfolio=self.get_roi_portfolio_overview(user),
        )

    def get_roi_portfolio_overview(self, user: AuthUser) -> RoiPortfolioOverview:
        projects = self.list_projects(user)
        total_budget = sum(project.budget_amount or 0 for project in projects)
        top_scenarios: list[RoiPortfolioScenarioView] = []
        capital_allocation: list[RoiPortfolioProjectExposure] = []
        downside_stress_views: list[RoiPortfolioStressView] = []
        risk_scores: list[float] = []
        invest_count = 0
        watch_count = 0
        reject_count = 0
        downside_exposure_count = 0
        total_roi_scenarios = 0
        total_roi_projects = 0

        for project in projects:
            scenarios = self.list_project_roi_scenarios(project.id, user)
            if scenarios:
                total_roi_projects += 1
            snapshot = self.get_project_roi_snapshot(project.id, user)
            total_roi_scenarios += len(snapshot.scenario_rankings)
            for ranking in snapshot.scenario_rankings:
                top_scenarios.append(
                    RoiPortfolioScenarioView(
                        project_id=project.id,
                        project_name=project.name,
                        project_type=project.project_type,
                        budget_amount=project.budget_amount,
                        ranking=ranking,
                    )
                )
                risk_scores.append(ranking.risk_adjusted_score)
                if ranking.recommendation == "invest":
                    invest_count += 1
                elif ranking.recommendation == "watch":
                    watch_count += 1
                elif ranking.recommendation == "reject":
                    reject_count += 1
                if (ranking.probability_negative_npv or 0) >= 35 or (ranking.probability_dscr_below_one or 0) >= 20:
                    downside_exposure_count += 1

            downside_stress_views.extend(self._build_project_downside_stress_views(project, scenarios))

            capital_allocation.append(
                RoiPortfolioProjectExposure(
                    project_id=project.id,
                    project_name=project.name,
                    project_type=project.project_type,
                    budget_amount=project.budget_amount,
                    budget_weight_percent=round(((project.budget_amount or 0) / total_budget) * 100, 2) if total_budget > 0 and project.budget_amount is not None else None,
                    scenario_count=len(scenarios),
                    best_risk_adjusted_score=snapshot.best_risk_adjusted_score,
                )
            )

        return RoiPortfolioOverview(
            total_roi_projects=total_roi_projects,
            total_roi_scenarios=total_roi_scenarios,
            average_risk_adjusted_score=round(mean(risk_scores), 2) if risk_scores else None,
            invest_count=invest_count,
            watch_count=watch_count,
            reject_count=reject_count,
            downside_exposure_count=downside_exposure_count,
            top_scenarios=sorted(top_scenarios, key=lambda item: item.ranking.risk_adjusted_score, reverse=True)[:5],
            capital_allocation=sorted(
                capital_allocation,
                key=lambda item: (item.budget_amount or 0, item.best_risk_adjusted_score or 0),
                reverse=True,
            )[:5],
            downside_stress_views=sorted(
                downside_stress_views,
                key=lambda item: (
                    item.npv_drawdown if item.npv_drawdown is not None else float("-inf"),
                    -9999 if item.stressed_irr is None else -item.stressed_irr,
                ),
            )[:5],
        )

    def _build_project_downside_stress_views(
        self,
        project: ProjectSummary,
        scenarios: list[RoiScenarioSummary],
    ) -> list[RoiPortfolioStressView]:
        stress_rows: list[RoiPortfolioStressView] = []
        for scenario in scenarios:
            payload = RoiScenarioInput.model_validate(scenario.model_dump())
            stress_tests = roi_analysis_service.build_analysis(payload).stress_tests
            downside_case = next((item for item in stress_tests if item.scenario_key == "combined_downside"), None)
            if downside_case is None:
                continue
            irr_compression = None
            if scenario.projected_irr is not None and downside_case.projected_irr is not None:
                irr_compression = round(scenario.projected_irr - downside_case.projected_irr, 2)
            npv_drawdown = None
            if downside_case.projected_npv is not None:
                npv_drawdown = round(scenario.projected_npv - downside_case.projected_npv, 2)
            stress_rows.append(
                RoiPortfolioStressView(
                    project_id=project.id,
                    project_name=project.name,
                    project_type=project.project_type,
                    scenario_id=scenario.id,
                    scenario_name=scenario.name,
                    scenario_type=scenario.scenario_type,
                    stressed_irr=downside_case.projected_irr,
                    stressed_npv=downside_case.projected_npv,
                    base_irr=scenario.projected_irr,
                    base_npv=scenario.projected_npv,
                    irr_compression=irr_compression,
                    npv_drawdown=npv_drawdown,
                    minimum_dscr=downside_case.minimum_dscr,
                    fragility=self._classify_downside_fragility(downside_case.projected_irr, downside_case.projected_npv, downside_case.minimum_dscr),
                )
            )
        return stress_rows

    def _classify_downside_fragility(
        self,
        stressed_irr: float | None,
        stressed_npv: float | None,
        minimum_dscr: float | None,
    ) -> str:
        if (stressed_irr is not None and stressed_irr < 0) or (stressed_npv is not None and stressed_npv < 0) or (minimum_dscr is not None and minimum_dscr < 1.0):
            return "high"
        if (stressed_irr is not None and stressed_irr < 8.0) or (minimum_dscr is not None and minimum_dscr < 1.2):
            return "medium"
        return "low"

    def _load_projects(self) -> list[ProjectSummary]:
        if platform_storage_service.is_available():
            try:
                return platform_storage_service.list_projects()
            except SQLAlchemyError:
                pass
        return list(self._projects)

    def _load_project(self, project_id: str) -> ProjectSummary | None:
        if platform_storage_service.is_available():
            try:
                return platform_storage_service.get_project(project_id)
            except SQLAlchemyError:
                pass
        return next((project for project in self._projects if project.id == project_id), None)

    def _save_project(self, project: ProjectSummary) -> ProjectSummary | None:
        if platform_storage_service.is_available():
            try:
                return platform_storage_service.create_project(project)
            except SQLAlchemyError:
                return None
        return None

    def _load_listings(self, user: AuthUser) -> list[ListingSummary]:
        if platform_storage_service.is_available():
            try:
                return platform_storage_service.list_listings(user.tenant_id)
            except SQLAlchemyError:
                pass
        return list(self._listings)

    def _load_market_insights(self, user: AuthUser) -> list[MarketInsight]:
        if platform_storage_service.is_available():
            try:
                return platform_storage_service.list_market_insights(user.tenant_id)
            except SQLAlchemyError:
                pass
        return list(self._market_insights)

    def _load_alerts(self, user: AuthUser) -> list[AlertPreference]:
        if platform_storage_service.is_available():
            try:
                return platform_storage_service.list_alerts(user.tenant_id)
            except SQLAlchemyError:
                pass
        return list(self._alerts)

    def _build_project_activity(
        self,
        project: ProjectSummary,
        documents: list[ProjectDocumentSummary],
        notes: list[ProjectNoteSummary],
    ) -> list[ProjectActivityItem]:
        items = [
            ProjectActivityItem(
                id=f"activity-project-{project.id}",
                activity_type="project_created",
                title="Project initialized",
                detail=f"{project.name} was created and assigned to {project.owner}.",
                actor=project.owner,
                occurred_at=project.created_at,
            )
        ]
        items.extend(
            ProjectActivityItem(
                id=f"activity-document-{document.id}",
                activity_type="document_uploaded",
                title="Evidence uploaded",
                detail=f"{document.file_name} was added to the project workspace.",
                actor=document.uploaded_by,
                occurred_at=document.uploaded_at,
            )
            for document in documents
        )
        items.extend(
            ProjectActivityItem(
                id=f"activity-note-{note.id}",
                activity_type="note_added",
                title="Project note added",
                detail=note.content,
                actor=note.author_name,
                occurred_at=note.created_at,
            )
            for note in notes
        )
        return sorted(
            items,
            key=lambda item: item.occurred_at or datetime.min.replace(tzinfo=UTC),
            reverse=True,
        )

    def _validate_roi_listing(self, project_id: str, listing_id: str | None, user: AuthUser) -> None:
        if listing_id is None:
            return
        listing = next((item for item in self.list_listings(user) if item.id == listing_id), None)
        if listing is None or listing.project_id != project_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ROI scenario listing must belong to this project.")

    def get_project_roi_scenario(self, project_id: str, scenario_id: str, user: AuthUser) -> RoiScenarioSummary | None:
        return next((item for item in self.list_project_roi_scenarios(project_id, user) if item.id == scenario_id), None)

    def _resolve_benchmark_context(self, listing_id: str | None, user: AuthUser) -> tuple[str, str | None]:
        if listing_id is None:
            return "general", None
        listing = next((item for item in self.list_listings(user) if item.id == listing_id), None)
        if listing is None:
            return "general", None
        return listing.asset_class, listing.location

    def _resolve_calibrated_benchmark_ranges(
        self,
        benchmark_profile: str,
        user: AuthUser,
        location: str | None = None,
    ) -> dict[str, tuple[float, float]] | None:
        comps = [comp for comp in self._list_benchmark_comps_for_tenant(user, benchmark_profile) if comp.included]
        if not comps:
            return None
        ranges, _ = roi_analysis_service.calibrate_benchmark_profile(benchmark_profile, comps, location)
        return ranges

    def _build_scenario_benchmark_context(
        self,
        benchmark_profile: str,
        user: AuthUser,
        location: str | None = None,
    ) -> RoiScenarioBenchmarkContext:
        all_comps = self._list_benchmark_comps_for_tenant(user, benchmark_profile)
        included_comps = [comp for comp in all_comps if comp.included]
        if not included_comps:
            return RoiScenarioBenchmarkContext(
                benchmark_profile=benchmark_profile,
                location=location,
                source_mode="default_profile",
                comp_count=0,
                effective_comp_count=0,
                matched_location=location,
                notes=["No active comparable records are available for this scenario yet."],
                comps=[],
            )

        _ranges, calibration = roi_analysis_service.calibrate_benchmark_profile(benchmark_profile, included_comps, location)
        contributing_metrics_by_comp = self._map_benchmark_comp_contributions(included_comps, location)
        effective_comp_ids = {comp_id for comp_id, metrics in contributing_metrics_by_comp.items() if metrics}
        comp_cards: list[RoiBenchmarkCompInfluence] = []
        for comp in sorted(
            all_comps,
            key=lambda item: (
                0 if item.id in effective_comp_ids else 1,
                0 if item.included else 1,
                item.source_name.lower(),
            ),
        ):
            weight = round(roi_analysis_service._benchmark_comp_weight(comp, location), 2) if comp.included else None
            contributing_metrics = sorted(contributing_metrics_by_comp.get(comp.id, set()))
            comp_cards.append(
                RoiBenchmarkCompInfluence(
                    comp_id=comp.id,
                    source_name=comp.source_name,
                    location=comp.location,
                    closed_on=comp.closed_on,
                    included=comp.included,
                    override_mode=comp.override_mode,
                    fit_label=self._benchmark_comp_fit_label(comp, location),
                    freshness_label=self._benchmark_comp_freshness_label(comp),
                    influence=self._benchmark_comp_influence_label(comp, contributing_metrics, weight),
                    weight=weight,
                    contributing_metrics=contributing_metrics,
                    note=comp.note,
                )
            )

        return RoiScenarioBenchmarkContext(
            benchmark_profile=calibration.benchmark_profile,
            location=location,
            source_mode=calibration.source_mode,
            comp_count=calibration.comp_count,
            effective_comp_count=len(effective_comp_ids) or calibration.effective_comp_count,
            matched_location=calibration.matched_location,
            notes=calibration.notes,
            comps=comp_cards,
        )

    def _map_benchmark_comp_contributions(
        self,
        comps: list[RoiBenchmarkCompSummary],
        location: str | None,
    ) -> dict[str, set[str]]:
        eligible_items = [
            {
                "comp": comp,
                "weight": roi_analysis_service._benchmark_comp_weight(comp, location),
            }
            for comp in comps
            if comp.override_mode != "exclude_outlier"
        ]
        eligible_items = [item for item in eligible_items if item["weight"] > 0]
        contributions: dict[str, set[str]] = {comp.id: set() for comp in comps}
        metric_sources = {
            "projected_irr": [(item["comp"].projected_irr, item["weight"]) for item in eligible_items if item["comp"].projected_irr is not None],
            "equity_multiple": [(item["comp"].equity_multiple, item["weight"]) for item in eligible_items if item["comp"].equity_multiple is not None],
            "average_dscr": [(item["comp"].average_dscr, item["weight"]) for item in eligible_items if item["comp"].average_dscr is not None],
            "leverage_ratio": [(item["comp"].leverage_ratio, item["weight"]) for item in eligible_items if item["comp"].leverage_ratio is not None],
            "vacancy_rate": [(100 - item["comp"].occupancy_rate, item["weight"]) for item in eligible_items if item["comp"].occupancy_rate is not None],
        }

        for metric, weighted_values in metric_sources.items():
            if not weighted_values:
                continue
            filtered_values, _excluded = roi_analysis_service._exclude_outliers(metric, weighted_values, eligible_items)
            if not filtered_values:
                filtered_values = weighted_values
            for item in eligible_items:
                comp = item["comp"]
                metric_value = 100 - comp.occupancy_rate if metric == "vacancy_rate" and comp.occupancy_rate is not None else getattr(comp, metric)
                if metric_value is None:
                    continue
                if (metric_value, item["weight"]) in filtered_values:
                    contributions.setdefault(comp.id, set()).add(metric)
        return contributions

    def _benchmark_comp_fit_label(self, comp: RoiBenchmarkCompSummary, location: str | None) -> str:
        if not location:
            return "General benchmark fit"
        comp_location = roi_analysis_service._normalize_location(comp.location)
        target_location = roi_analysis_service._normalize_location(location)
        if comp_location == target_location:
            return "Exact market match"
        comp_state = roi_analysis_service._extract_state(comp.location)
        target_state = roi_analysis_service._extract_state(location)
        if comp_state and target_state and comp_state == target_state:
            return "Same-state match"
        return "Out-of-market reference"

    def _benchmark_comp_freshness_label(self, comp: RoiBenchmarkCompSummary) -> str:
        age_weight = roi_analysis_service._benchmark_comp_age_weight(comp)
        if comp.closed_on is None:
            return "Undated comp"
        if age_weight >= 1.0:
            return "Fresh comp"
        if age_weight >= 0.8:
            return "Aging comp"
        if age_weight >= 0.6:
            return "Stale comp"
        return "Very stale comp"

    def _benchmark_comp_influence_label(
        self,
        comp: RoiBenchmarkCompSummary,
        contributing_metrics: list[str],
        weight: float | None,
    ) -> str:
        if not comp.included:
            return "excluded_by_analyst"
        if comp.override_mode == "exclude_outlier":
            return "excluded_outlier"
        if comp.override_mode == "force_include" and contributing_metrics:
            return "forced"
        if contributing_metrics and weight is not None and weight < 1.0:
            return "downweighted"
        if contributing_metrics:
            return "used"
        return "not_used"


# Shared singleton for the API layer until dependency injection is introduced.
platform_service = PlatformService()
