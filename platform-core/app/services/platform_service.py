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
from app.schemas.project import PlatformOverview, ProjectCreate, ProjectMemberAdd, ProjectSummary, ProjectWorkspace
from app.schemas.roi import (
    RoiActualCreate,
    RoiActualSummary,
    RoiBenchmarkCalibrationResponse,
    RoiBenchmarkCompCreate,
    RoiBenchmarkCompSummary,
    RoiPortfolioSnapshot,
    RoiRecommendationSummary,
    RoiScenarioAnalysisResponse,
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
        benchmark_profile = self._resolve_benchmark_profile(payload.listing_id, user)
        benchmark_ranges = self._resolve_calibrated_benchmark_ranges(benchmark_profile, user)
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
        benchmark_profile = self._resolve_benchmark_profile(payload.listing_id, user)
        benchmark_ranges = self._resolve_calibrated_benchmark_ranges(benchmark_profile, user)
        analysis = roi_analysis_service.build_analysis(payload, computed, benchmark_profile, benchmark_ranges)
        return RoiScenarioAnalysisResponse(
            scenario=scenario,
            analysis=analysis,
            recommendation=roi_analysis_service.build_recommendation(payload, analysis, computed),
        )

    def list_benchmark_comps(self, user: AuthUser, asset_class: str | None = None) -> list[RoiBenchmarkCompSummary]:
        authorization_service.require_tenant_editor(user)
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
            **payload.model_dump(),
        )
        if platform_storage_service.is_available():
            try:
                return platform_storage_service.create_benchmark_comp(comp)
            except SQLAlchemyError:
                pass
        self._benchmark_comps.append(comp)
        return comp

    def get_benchmark_calibration(self, asset_class: str, user: AuthUser) -> RoiBenchmarkCalibrationResponse:
        authorization_service.require_tenant_editor(user)
        comps = self.list_benchmark_comps(user, asset_class)
        _, calibration = roi_analysis_service.calibrate_benchmark_profile(asset_class, comps)
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
        )

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

    def _resolve_benchmark_profile(self, listing_id: str | None, user: AuthUser) -> str:
        if listing_id is None:
            return "general"
        listing = next((item for item in self.list_listings(user) if item.id == listing_id), None)
        if listing is None:
            return "general"
        return listing.asset_class

    def _resolve_calibrated_benchmark_ranges(
        self,
        benchmark_profile: str,
        user: AuthUser,
    ) -> dict[str, tuple[float, float]] | None:
        comps = self.list_benchmark_comps(user, benchmark_profile)
        if not comps:
            return None
        ranges, _ = roi_analysis_service.calibrate_benchmark_profile(benchmark_profile, comps)
        return ranges


# Shared singleton for the API layer until dependency injection is introduced.
platform_service = PlatformService()
