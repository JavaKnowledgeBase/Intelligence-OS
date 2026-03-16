from datetime import datetime

from pydantic import BaseModel, Field


class ProjectNoteCreate(BaseModel):
    """Payload for adding a note to a project workspace."""

    content: str = Field(min_length=3, max_length=5000)


class ProjectNoteSummary(BaseModel):
    """Project note returned to the workspace UI."""

    id: str
    project_id: str
    tenant_id: str
    author_name: str
    content: str
    created_at: datetime | None = None


class ProjectActivityItem(BaseModel):
    """Normalized activity event shown in the project timeline."""

    id: str
    activity_type: str
    title: str
    detail: str
    actor: str
    occurred_at: datetime | None = None
