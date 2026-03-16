from pydantic import BaseModel, Field


class ListingSummary(BaseModel):
    """Compact listing shape for dashboards, search results, and ranking views."""

    id: str
    project_id: str | None = None
    title: str
    asset_class: str
    location: str
    asking_price: float
    projected_irr: float
    deal_score: int
    summary: str
    risk_level: str = "medium"
    occupancy_rate: float | None = None
    hold_period_months: int | None = None
    status: str = "pipeline"


class ListingCreate(BaseModel):
    """Payload for creating a new investment opportunity record."""

    title: str = Field(min_length=3)
    project_id: str | None = None
    asset_class: str
    location: str
    asking_price: float = Field(ge=0)
    projected_irr: float = Field(ge=0)
    deal_score: int = Field(ge=0, le=100)
    summary: str
    risk_level: str = "medium"
    occupancy_rate: float | None = Field(default=None, ge=0, le=100)
    hold_period_months: int | None = Field(default=None, ge=1)
    status: str = "pipeline"


class DealSearchResponse(BaseModel):
    """Search payload combining query metadata with matched listings."""

    query: str
    total: int
    results: list[ListingSummary]
