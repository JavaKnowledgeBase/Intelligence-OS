from datetime import datetime

from pydantic import BaseModel, Field


class IngestionTriggerRequest(BaseModel):
    """Request payload for triggering a local ingestion sync."""

    source_name: str = Field(default="starter_feed", min_length=3)


class IngestionRunSummary(BaseModel):
    """Result summary for a completed or historical ingestion run."""

    id: str
    tenant_id: str
    source_name: str
    status: str
    records_processed: int
    records_created: int
    records_updated: int
    detail: str
    started_at: datetime
    completed_at: datetime | None = None


class IngestionSourceSummary(BaseModel):
    """Available local ingestion source metadata for the operations UI."""

    source_name: str
    tenant_id: str | None = None
    listing_count: int
    market_insight_count: int
