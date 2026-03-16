from __future__ import annotations

from datetime import UTC, datetime
from statistics import mean
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from app.schemas.alert import AlertPreference, AlertPreferenceCreate
from app.schemas.auth import AuthUser
from app.schemas.document import ProjectDocumentSummary
from app.schemas.listing import DealSearchResponse, ListingCreate, ListingSummary
from app.schemas.market import MarketInsight, MarketInsightCreate
from app.schemas.note import ProjectActivityItem, ProjectNoteCreate, ProjectNoteSummary
from app.schemas.project import PlatformOverview, ProjectCreate, ProjectSummary, ProjectWorkspace
from app.services.authorization_service import authorization_service
from app.services.platform_storage_service import platform_storage_service
from app.services.project_document_service import project_document_service


class PlatformService:
    """Application service for platform domains with PostgreSQL as the primary source of truth."""

    def __init__(self) -> None:
        # Keep empty in-memory fallbacks so local development stays resilient if storage is unavailable.
        self._projects: list[ProjectSummary] = []
        self._listings: list[ListingSummary] = []
        self._market_insights: list[MarketInsight] = []
        self._alerts: list[AlertPreference] = []

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
        return ProjectWorkspace(
            project=project,
            listings=listings,
            market_insights=self.get_market_insights(user),
            alerts=self.list_alerts(user),
            documents=documents,
            notes=notes,
            activity=self._build_project_activity(project, documents, notes),
        )

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
                    author_name=user.full_name,
                    content=payload.content.strip(),
                )
            except SQLAlchemyError:
                pass
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Project note storage is not available.")

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


# Shared singleton for the API layer until dependency injection is introduced.
platform_service = PlatformService()
