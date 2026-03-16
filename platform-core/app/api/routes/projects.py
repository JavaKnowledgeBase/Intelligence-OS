from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
from app.schemas.auth import AuthUser
from app.schemas.project import (
    PlatformOverview,
    ProjectCreate,
    ProjectSummary,
)
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
