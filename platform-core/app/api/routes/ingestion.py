from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
from app.schemas.auth import AuthUser
from app.schemas.ingestion import IngestionRunSummary, IngestionTriggerRequest
from app.services.ingestion_service import ingestion_service


router = APIRouter()


@router.get("/runs", response_model=list[IngestionRunSummary])
def list_ingestion_runs(current_user: AuthUser = Depends(get_current_user)) -> list[IngestionRunSummary]:
    """Return ingestion run history visible to the caller's tenant."""
    return ingestion_service.list_runs(current_user)


@router.post("/sync", response_model=IngestionRunSummary, status_code=202)
def sync_ingestion_source(
    payload: IngestionTriggerRequest,
    current_user: AuthUser = Depends(get_current_user),
) -> IngestionRunSummary:
    """Trigger a local source sync into the platform catalog."""
    try:
        return ingestion_service.sync_source(payload.source_name, current_user)
    except FileNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except PermissionError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
