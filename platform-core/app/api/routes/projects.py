import io

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse
from starlette.responses import StreamingResponse

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
    RoiActualCreate,
    RoiActualSummary,
    RoiPortfolioSnapshot,
    RoiScenarioAnalysisResponse,
    RoiScenarioCalculationResponse,
    RoiScenarioCreate,
    RoiScenarioRecommendation,
    RoiScenarioSummary,
    RoiScenarioUpdate,
    RoiSensitivityResponse,
    RoiVarianceAnalysis,
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


@router.post("/{project_id}/roi-scenarios/{scenario_id}/recommendations", response_model=RoiScenarioRecommendation, status_code=201)
def create_project_roi_recommendation(
    project_id: str,
    scenario_id: str,
    current_user: AuthUser = Depends(get_current_user),
) -> RoiScenarioRecommendation:
    """Persist a recommendation action checklist for an existing ROI scenario."""
    return platform_service.create_project_roi_recommendation(project_id, scenario_id, current_user)


@router.get("/{project_id}/roi-scenarios/{scenario_id}/recommendations/pdf")
def download_project_roi_recommendations_pdf(
    project_id: str,
    scenario_id: str,
    current_user: AuthUser = Depends(get_current_user),
) -> StreamingResponse:
    """Return a PDF export of recommendations for a scenario."""
    pdf_bytes = platform_service.get_project_roi_recommendations_pdf(project_id, scenario_id, current_user)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=roi-recommendations-{project_id}-{scenario_id}.pdf",
        },
    )


@router.get("/{project_id}/roi-scenarios/{scenario_id}/recommendations", response_model=list[RoiScenarioRecommendation])
def list_project_roi_recommendations(
    project_id: str,
    scenario_id: str,
    current_user: AuthUser = Depends(get_current_user),
) -> list[RoiScenarioRecommendation]:
    """Return persisted recommendations for a scenario to support audit and workflow tracking."""
    return platform_service.list_project_roi_recommendations(project_id, scenario_id, current_user)


@router.post("/{project_id}/roi-scenarios/calculate", response_model=RoiScenarioCalculationResponse)
def calculate_project_roi_scenario(
    project_id: str,
    payload: RoiScenarioCreate,
    current_user: AuthUser = Depends(get_current_user),
) -> RoiScenarioCalculationResponse:
    """Preview calculated ROI outputs without saving a scenario."""
    return platform_service.calculate_project_roi_scenario(project_id, payload, current_user)


@router.post("/{project_id}/roi-scenarios/analyze", response_model=RoiScenarioAnalysisResponse)
def analyze_project_roi_scenario(
    project_id: str,
    payload: RoiScenarioCreate,
    current_user: AuthUser = Depends(get_current_user),
) -> RoiScenarioAnalysisResponse:
    """Return analytical diagnostics, value concentration, and stress outcomes for a scenario."""
    return platform_service.analyze_project_roi_scenario(project_id, payload, current_user)


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


@router.get("/{project_id}/roi-scenarios/{scenario_id}/actuals", response_model=list[RoiActualSummary])
def list_project_roi_actuals(
    project_id: str,
    scenario_id: str,
    current_user: AuthUser = Depends(get_current_user),
) -> list[RoiActualSummary]:
    """Return realized monthly operating actuals captured for an ROI scenario."""
    return platform_service.list_project_roi_actuals(project_id, scenario_id, current_user)


@router.post("/{project_id}/roi-scenarios/{scenario_id}/actuals", response_model=RoiActualSummary, status_code=201)
def create_project_roi_actual(
    project_id: str,
    scenario_id: str,
    payload: RoiActualCreate,
    current_user: AuthUser = Depends(get_current_user),
) -> RoiActualSummary:
    """Persist a realized monthly operating result for variance analysis."""
    return platform_service.create_project_roi_actual(project_id, scenario_id, payload, current_user)


@router.get("/{project_id}/roi-scenarios/{scenario_id}/variance", response_model=RoiVarianceAnalysis)
def get_project_roi_variance_analysis(
    project_id: str,
    scenario_id: str,
    current_user: AuthUser = Depends(get_current_user),
) -> RoiVarianceAnalysis:
    """Compare recorded realized operating results against the original underwriting path."""
    return platform_service.build_project_roi_variance_analysis(project_id, scenario_id, current_user)


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
