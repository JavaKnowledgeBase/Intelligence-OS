from datetime import datetime

from pydantic import BaseModel, Field


class ProjectDocumentSummary(BaseModel):
    """Document metadata attached to a project workspace."""

    id: str
    project_id: str
    tenant_id: str
    file_name: str
    stored_name: str
    content_type: str
    file_size_bytes: int
    uploaded_by: str
    processing_status: str = "ready"
    preview_available: bool = False
    extracted_text_excerpt: str = ""
    uploaded_at: datetime | None = None


class ProjectDocumentUploadResponse(BaseModel):
    """Upload response returned after a project document is persisted."""

    message: str = Field(default="Document uploaded successfully.")
    document: ProjectDocumentSummary


class ProjectDocumentPreview(BaseModel):
    """Lightweight preview payload for text-friendly project documents."""

    document: ProjectDocumentSummary
    preview_text: str
