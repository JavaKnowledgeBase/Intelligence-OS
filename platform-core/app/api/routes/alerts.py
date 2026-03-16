from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.schemas.alert import AlertPreference, AlertPreferenceCreate
from app.schemas.auth import AuthUser
from app.services.platform_service import platform_service


# Alert endpoints represent the notification preferences layer in the platform.
router = APIRouter()


@router.get("", response_model=list[AlertPreference])
def list_alerts(current_user: AuthUser = Depends(get_current_user)) -> list[AlertPreference]:
    """Return currently configured alert rules visible to the caller's tenant."""
    return platform_service.list_alerts(current_user)


@router.post("", response_model=AlertPreference, status_code=201)
def create_alert(payload: AlertPreferenceCreate, current_user: AuthUser = Depends(get_current_user)) -> AlertPreference:
    """Create a new tenant-scoped alert rule."""
    return platform_service.create_alert(payload, current_user)
