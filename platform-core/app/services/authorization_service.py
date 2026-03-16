from fastapi import HTTPException, status

from app.schemas.auth import AuthUser
from app.schemas.project import ProjectSummary


class AuthorizationService:
    """Role, tenant, and project-level authorization checks for platform resources."""

    elevated_roles = {"admin", "analyst"}
    project_creator_roles = {"admin", "analyst"}
    tenant_editor_roles = {"admin", "analyst"}
    tenant_admin_roles = {"admin"}

    def can_access_project(self, user: AuthUser, project: ProjectSummary) -> bool:
        if user.tenant_id != project.tenant_id:
            return False
        if user.role in self.elevated_roles:
            return True
        return user.id == project.owner_id or user.id in project.member_ids

    def filter_projects(self, user: AuthUser, projects: list[ProjectSummary]) -> list[ProjectSummary]:
        return [project for project in projects if self.can_access_project(user, project)]

    def require_project_access(self, user: AuthUser, project: ProjectSummary) -> None:
        if not self.can_access_project(user, project):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this project.",
            )

    def require_project_creation(self, user: AuthUser) -> None:
        if user.role not in self.project_creator_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your role is not allowed to create projects.",
            )

    def require_tenant_editor(self, user: AuthUser) -> None:
        if user.role not in self.tenant_editor_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your role is not allowed to manage tenant investment data.",
            )

    def require_admin(self, user: AuthUser) -> None:
        if user.role not in self.tenant_admin_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access is required for this action.",
            )

    def can_manage_project(self, user: AuthUser, project: ProjectSummary) -> bool:
        if user.tenant_id != project.tenant_id:
            return False
        if user.role in self.tenant_editor_roles:
            return True
        return user.id == project.owner_id

    def require_project_management(self, user: AuthUser, project: ProjectSummary) -> None:
        if not self.can_manage_project(user, project):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to manage this project.",
            )


authorization_service = AuthorizationService()
