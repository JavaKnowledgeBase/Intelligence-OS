from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse

from app.api.deps import get_current_user
from app.schemas.auth import AuthUser
from app.schemas.document import ProjectDocumentPreview, ProjectDocumentSummary, ProjectDocumentUploadResponse
from app.schemas.note import ProjectNoteCreate, ProjectNoteSummary, ProjectNoteUpdate
from app.schemas.project import (
    PlatformOverview,
    ProjectCreate,
    ProjectMemberAdd,
    ProjectSummary,
    ProjectWorkspace,
)
from app.schemas.roi import (
    RoiPortfolioSnapshot,
    RoiScenarioCalculationResponse,
    RoiScenarioCreate,
    RoiScenarioSummary,
    RoiScenarioUpdate,
    RoiSensitivityResponse,
)
from app.services.project_document_service import project_document_service
from app.services.platform_service import platform_service


# Project endpoints expose the shared project root model used by all solution packs.
router = APIRouter()


@router.get("", response_model=list[ProjectSummary])
def list_projects(current_user: AuthUser = Depends(get_current_user)) -> list[ProjectSummary]:
    """Return the current project workspace list."""
    return platform_service.list_projects(current_user)


@router.get("/overview", response_model=PlatformOverview)
def get_platform_overview(current_user: AuthUser = Depends(get_current_user)) -> PlatformOverview:
    """Aggregate dashboard-friendly metrics for the frontend."""
    return platform_service.get_overview(current_user)


@router.get("/{project_id}/workspace", response_model=ProjectWorkspace)
def get_project_workspace(project_id: str, current_user: AuthUser = Depends(get_current_user)) -> ProjectWorkspace:
    """Return the project detail workspace for an authorized caller."""
    return platform_service.get_project_workspace(project_id, current_user)


@router.get("/{project_id}/members", response_model=list[AuthUser])
def list_project_members(project_id: str, current_user: AuthUser = Depends(get_current_user)) -> list[AuthUser]:
    """Return users currently attached to the project workspace."""
    return platform_service.list_project_members(project_id, current_user)


@router.post("/{project_id}/members", response_model=AuthUser, status_code=201)
def add_project_member(
    project_id: str,
    payload: ProjectMemberAdd,
    current_user: AuthUser = Depends(get_current_user),
) -> AuthUser:
    """Add an existing tenant user to a project."""
    return platform_service.add_project_member(project_id, payload, current_user)


@router.delete("/{project_id}/members/{member_user_id}", status_code=204)
def remove_project_member(
    project_id: str,
    member_user_id: str,
    current_user: AuthUser = Depends(get_current_user),
) -> Response:
    """Remove a member from the project workspace."""
    platform_service.remove_project_member(project_id, member_user_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{project_id}/documents", response_model=list[ProjectDocumentSummary])
def list_project_documents(
    project_id: str,
    current_user: AuthUser = Depends(get_current_user),
) -> list[ProjectDocumentSummary]:
    """Return the documents attached to an authorized project."""
    return platform_service.list_project_documents(project_id, current_user)


@router.get("/{project_id}/documents/{document_id}/download")
def download_project_document(
    project_id: str,
    document_id: str,
    current_user: AuthUser = Depends(get_current_user),
) -> FileResponse:
    """Download a project-scoped document when the caller is authorized."""
    project = platform_service.get_project(project_id, current_user)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    return project_document_service.get_document_download(
        project_id=project_id,
        tenant_id=current_user.tenant_id,
        document_id=document_id,
    )


@router.get("/{project_id}/documents/{document_id}/preview", response_model=ProjectDocumentPreview)
def preview_project_document(
    project_id: str,
    document_id: str,
    current_user: AuthUser = Depends(get_current_user),
) -> ProjectDocumentPreview:
    """Return a text preview for a previewable project document."""
    project = platform_service.get_project(project_id, current_user)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    return project_document_service.get_document_preview(
        project_id=project_id,
        tenant_id=current_user.tenant_id,
        document_id=document_id,
    )


@router.post("/{project_id}/documents", response_model=ProjectDocumentUploadResponse, status_code=201)
async def upload_project_document(
    project_id: str,
    file: UploadFile = File(...),
    current_user: AuthUser = Depends(get_current_user),
) -> ProjectDocumentUploadResponse:
    """Upload a document into a project-scoped workspace."""
    project = platform_service.get_project(project_id, current_user)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    document = await project_document_service.upload_project_document(
        project_id=project_id,
        user=current_user,
        upload=file,
    )
    return ProjectDocumentUploadResponse(document=document)


@router.get("/{project_id}/notes", response_model=list[ProjectNoteSummary])
def list_project_notes(
    project_id: str,
    current_user: AuthUser = Depends(get_current_user),
) -> list[ProjectNoteSummary]:
    """Return notes attached to an authorized project."""
    return platform_service.list_project_notes(project_id, current_user)


@router.post("/{project_id}/notes", response_model=ProjectNoteSummary, status_code=201)
def create_project_note(
    project_id: str,
    payload: ProjectNoteCreate,
    current_user: AuthUser = Depends(get_current_user),
) -> ProjectNoteSummary:
    """Create a note in a project workspace."""
    return platform_service.create_project_note(project_id, payload, current_user)


@router.put("/{project_id}/notes/{note_id}", response_model=ProjectNoteSummary)
def update_project_note(
    project_id: str,
    note_id: str,
    payload: ProjectNoteUpdate,
    current_user: AuthUser = Depends(get_current_user),
) -> ProjectNoteSummary:
    """Update an existing project note."""
    return platform_service.update_project_note(project_id, note_id, payload, current_user)


@router.delete("/{project_id}/notes/{note_id}", status_code=204)
def delete_project_note(
    project_id: str,
    note_id: str,
    current_user: AuthUser = Depends(get_current_user),
) -> Response:
    """Delete a project note."""
    platform_service.delete_project_note(project_id, note_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{project_id}/roi-scenarios", response_model=list[RoiScenarioSummary])
def list_project_roi_scenarios(
    project_id: str,
    current_user: AuthUser = Depends(get_current_user),
) -> list[RoiScenarioSummary]:
    """Return saved ROI scenarios for an authorized project."""
    return platform_service.list_project_roi_scenarios(project_id, current_user)


@router.get("/{project_id}/roi-snapshot", response_model=RoiPortfolioSnapshot)
def get_project_roi_snapshot(
    project_id: str,
    current_user: AuthUser = Depends(get_current_user),
) -> RoiPortfolioSnapshot:
    """Return an aggregate ROI snapshot for the project."""
    return platform_service.get_project_roi_snapshot(project_id, current_user)


@router.post("/{project_id}/roi-scenarios/calculate", response_model=RoiScenarioCalculationResponse)
def calculate_project_roi_scenario(
    project_id: str,
    payload: RoiScenarioCreate,
    current_user: AuthUser = Depends(get_current_user),
) -> RoiScenarioCalculationResponse:
    """Preview calculated ROI outputs without saving a scenario."""
    return platform_service.calculate_project_roi_scenario(project_id, payload, current_user)


@router.post("/{project_id}/roi-scenarios/sensitivity", response_model=RoiSensitivityResponse)
def build_project_roi_sensitivity(
    project_id: str,
    payload: RoiScenarioCreate,
    current_user: AuthUser = Depends(get_current_user),
) -> RoiSensitivityResponse:
    """Return a sensitivity matrix for core ROI drivers."""
    return platform_service.build_project_roi_sensitivity(project_id, payload, current_user)


@router.post("/{project_id}/roi-scenarios", response_model=RoiScenarioSummary, status_code=201)
def create_project_roi_scenario(
    project_id: str,
    payload: RoiScenarioCreate,
    current_user: AuthUser = Depends(get_current_user),
) -> RoiScenarioSummary:
    """Create and persist a project ROI scenario."""
    return platform_service.create_project_roi_scenario(project_id, payload, current_user)


@router.put("/{project_id}/roi-scenarios/{scenario_id}", response_model=RoiScenarioSummary)
def update_project_roi_scenario(
    project_id: str,
    scenario_id: str,
    payload: RoiScenarioUpdate,
    current_user: AuthUser = Depends(get_current_user),
) -> RoiScenarioSummary:
    """Update a persisted project ROI scenario."""
    return platform_service.update_project_roi_scenario(project_id, scenario_id, payload, current_user)


@router.delete("/{project_id}/roi-scenarios/{scenario_id}", status_code=204)
def delete_project_roi_scenario(
    project_id: str,
    scenario_id: str,
    current_user: AuthUser = Depends(get_current_user),
) -> Response:
    """Delete a persisted project ROI scenario."""
    platform_service.delete_project_roi_scenario(project_id, scenario_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{project_id}", response_model=ProjectSummary)
def get_project(project_id: str, current_user: AuthUser = Depends(get_current_user)) -> ProjectSummary:
    """Return a single project when the caller is authorized for it."""
    project = platform_service.get_project(project_id, current_user)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    return project


@router.post("", response_model=ProjectSummary, status_code=201)
def create_project(payload: ProjectCreate, current_user: AuthUser = Depends(get_current_user)) -> ProjectSummary:
    """Create a new project entry in the shared platform model."""
    return platform_service.create_project(payload, current_user)
