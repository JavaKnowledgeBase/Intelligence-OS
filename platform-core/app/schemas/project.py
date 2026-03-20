from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.schemas.alert import AlertPreference
from app.schemas.auth import AuthUser
from app.schemas.document import ProjectDocumentSummary
from app.schemas.listing import ListingSummary
from app.schemas.market import MarketInsight
from app.schemas.note import ProjectActivityItem, ProjectNoteSummary
from app.schemas.roi import RoiPortfolioSnapshot, RoiScenarioSummary


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


class PlatformOverview(BaseModel):
    """Dashboard aggregate that combines project, listing, and market snapshots."""

    total_projects: int
    total_listings: int
    average_deal_score: float
    featured_deals: list[ListingSummary]
    market_insights: list[MarketInsight]


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
