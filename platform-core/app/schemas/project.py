from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.schemas.alert import AlertPreference
from app.schemas.auth import AuthUser
from app.schemas.document import ProjectDocumentSummary
from app.schemas.listing import ListingSummary
from app.schemas.market import MarketInsight
from app.schemas.note import ProjectActivityItem, ProjectNoteSummary
from app.schemas.roi import RoiPortfolioSnapshot, RoiScenarioRankingItem, RoiScenarioSummary


class ProjectCreate(BaseModel):
    """Payload for creating a new shared platform project."""

    name: str = Field(min_length=3)
    project_type: str
    owner: str
    stage: str = "screening"
    investment_thesis: str = ""
    target_irr: float | None = None
    budget_amount: float | None = None


class ProjectSummary(BaseModel):
    """Top-level project record shown in workspace lists and summaries."""

    id: str
    name: str
    tenant_id: str
    project_type: str
    owner: str
    owner_id: str
    member_ids: list[str]
    status: str
    active_deals: int
    stage: str = "screening"
    investment_thesis: str = ""
    target_irr: float | None = None
    budget_amount: float | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class RoiPortfolioScenarioView(BaseModel):
    """Tenant-level scenario row enriched with project context for portfolio review."""

    project_id: str
    project_name: str
    project_type: str
    budget_amount: float | None = None
    ranking: RoiScenarioRankingItem


class RoiPortfolioProjectExposure(BaseModel):
    """Capital-allocation and scenario-density view for a single project."""

    project_id: str
    project_name: str
    project_type: str
    budget_amount: float | None = None
    budget_weight_percent: float | None = None
    scenario_count: int
    best_risk_adjusted_score: float | None = None


class RoiPortfolioStressView(BaseModel):
    """Tenant-level downside stress row enriched with project and scenario context."""

    project_id: str
    project_name: str
    project_type: str
    scenario_id: str
    scenario_name: str
    scenario_type: str
    stressed_irr: float | None = None
    stressed_npv: float | None = None
    base_irr: float | None = None
    base_npv: float | None = None
    irr_compression: float | None = None
    npv_drawdown: float | None = None
    minimum_dscr: float | None = None
    fragility: str


class PortfolioSavedViewBase(BaseModel):
    """Reusable portfolio dashboard view definition."""

    name: str = Field(min_length=2, max_length=80)
    portfolio_view: str = Field(min_length=2, max_length=40)
    is_shared: bool = False


class PortfolioSavedViewCreate(PortfolioSavedViewBase):
    """Payload for creating a tenant portfolio view preset."""


class PortfolioSavedViewUpdate(PortfolioSavedViewBase):
    """Payload for updating an existing tenant portfolio view preset."""


class PortfolioSavedViewSummary(PortfolioSavedViewBase):
    """Persisted tenant portfolio view preset."""

    id: str
    tenant_id: str
    created_by: str
    created_by_name: str
    created_at: datetime | None = None


class RoiPortfolioOverview(BaseModel):
    """Tenant-level portfolio ranking and concentration snapshot."""

    total_roi_projects: int
    total_roi_scenarios: int
    average_risk_adjusted_score: float | None = None
    invest_count: int
    watch_count: int
    reject_count: int
    downside_exposure_count: int
    top_scenarios: list[RoiPortfolioScenarioView]
    capital_allocation: list[RoiPortfolioProjectExposure]
    downside_stress_views: list[RoiPortfolioStressView]


class PlatformOverview(BaseModel):
    """Dashboard aggregate that combines project, listing, and market snapshots."""

    total_projects: int
    total_listings: int
    average_deal_score: float
    featured_deals: list[ListingSummary]
    market_insights: list[MarketInsight]
    roi_portfolio: RoiPortfolioOverview


class ProjectWorkspace(BaseModel):
    """Project detail payload that brings together the main workspace resources."""

    project: ProjectSummary
    members: list[AuthUser]
    listings: list[ListingSummary]
    market_insights: list[MarketInsight]
    alerts: list[AlertPreference]
    documents: list[ProjectDocumentSummary]
    notes: list[ProjectNoteSummary]
    roi_scenarios: list[RoiScenarioSummary]
    roi_snapshot: RoiPortfolioSnapshot
    activity: list[ProjectActivityItem]


class ProjectMemberAdd(BaseModel):
    """Payload for adding an existing tenant user to a project."""

    email: EmailStr
