from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.schemas.auth import AuthUser
from app.schemas.document import ProjectDocumentPreview, ProjectDocumentSummary
from app.services.platform_storage_service import platform_storage_service


class ProjectDocumentService:
    """Local project document storage with DB-backed metadata for the current platform phase."""

    def __init__(self) -> None:
        self._document_root = Path(settings.project_document_dir)
        self._document_root.mkdir(parents=True, exist_ok=True)

    def list_project_documents(self, *, project_id: str, tenant_id: str) -> list[ProjectDocumentSummary]:
        if not platform_storage_service.is_available():
            return []
        try:
            return platform_storage_service.list_project_documents(tenant_id, project_id)
        except SQLAlchemyError as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Project document storage is not available.",
            ) from error

    def get_document_preview(
        self,
        *,
        project_id: str,
        tenant_id: str,
        document_id: str,
    ) -> ProjectDocumentPreview:
        document = self._get_document_metadata(project_id=project_id, tenant_id=tenant_id, document_id=document_id)
        if not document.preview_available:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Preview is not available for this file type.")
        file_path = self._resolve_file_path(tenant_id=tenant_id, project_id=project_id, stored_name=document.stored_name)
        try:
            preview_text = file_path.read_text(encoding="utf-8")[:4000]
        except UnicodeDecodeError as error:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Preview could not be decoded as text.") from error
        return ProjectDocumentPreview(document=document, preview_text=preview_text)

    def get_document_download(
        self,
        *,
        project_id: str,
        tenant_id: str,
        document_id: str,
    ) -> FileResponse:
        document = self._get_document_metadata(project_id=project_id, tenant_id=tenant_id, document_id=document_id)
        file_path = self._resolve_file_path(tenant_id=tenant_id, project_id=project_id, stored_name=document.stored_name)

        return FileResponse(
            path=file_path,
            media_type=document.content_type,
            filename=document.file_name,
        )

    async def upload_project_document(
        self,
        *,
        project_id: str,
        user: AuthUser,
        upload: UploadFile,
    ) -> ProjectDocumentSummary:
        file_name = Path(upload.filename or "").name.strip()
        if not file_name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A valid file name is required.")

        content = await upload.read()
        if not content:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The uploaded file is empty.")
        if len(content) > settings.max_upload_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Files must be smaller than {settings.max_upload_size_bytes // (1024 * 1024)} MB.",
            )

        stored_name = f"{project_id}-{uuid4().hex[:12]}{Path(file_name).suffix.lower()}"
        project_dir = self._document_root / user.tenant_id / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        destination = project_dir / stored_name
        destination.write_bytes(content)
        preview_available, excerpt = self._extract_preview_data(file_name=file_name, content=content)

        if not platform_storage_service.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Document metadata storage is not available.",
            )

        try:
            return platform_storage_service.create_project_document(
                project_id=project_id,
                tenant_id=user.tenant_id,
                file_name=file_name,
                stored_name=stored_name,
                content_type=upload.content_type or "application/octet-stream",
                file_size_bytes=len(content),
                uploaded_by=user.full_name,
                processing_status="ready",
                preview_available=preview_available,
                extracted_text_excerpt=excerpt,
            )
        except SQLAlchemyError as error:
            destination.unlink(missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to save project document metadata.",
            ) from error

    def _get_document_metadata(self, *, project_id: str, tenant_id: str, document_id: str) -> ProjectDocumentSummary:
        documents = self.list_project_documents(project_id=project_id, tenant_id=tenant_id)
        document = next((item for item in documents if item.id == document_id), None)
        if document is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
        return document

    def _resolve_file_path(self, *, tenant_id: str, project_id: str, stored_name: str) -> Path:
        file_path = self._document_root / tenant_id / project_id / stored_name
        if not file_path.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stored document file was not found.")
        return file_path

    def _extract_preview_data(self, *, file_name: str, content: bytes) -> tuple[bool, str]:
        preview_extensions = {".txt", ".md", ".csv", ".json", ".log"}
        extension = Path(file_name).suffix.lower()
        if extension not in preview_extensions:
            return False, ""
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            return False, ""
        cleaned = text.strip()
        return True, cleaned[:280]


project_document_service = ProjectDocumentService()
