from datetime import date

from pydantic import BaseModel, Field


class MarketInsight(BaseModel):
    """Regional signal used to explain scoring and investment context."""

    id: str | None = None
    region: str
    signal: str
    trend: str
    confidence: float
    source: str = "internal-research"
    as_of_date: date | None = None


class MarketInsightCreate(BaseModel):
    """Payload for publishing a new market insight record."""

    region: str = Field(min_length=2)
    signal: str = Field(min_length=8)
    trend: str
    confidence: float = Field(ge=0, le=1)
    source: str = "internal-research"
    as_of_date: date | None = None
