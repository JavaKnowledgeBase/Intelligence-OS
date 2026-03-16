from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user
from app.schemas.auth import AuthUser
from app.schemas.listing import DealSearchResponse, ListingCreate, ListingSummary
from app.services.platform_service import platform_service


# Listing endpoints back the investment opportunity catalog and search flow.
router = APIRouter()


@router.get("", response_model=list[ListingSummary])
def list_listings(current_user: AuthUser = Depends(get_current_user)) -> list[ListingSummary]:
    """Return all current listings visible to the caller's tenant."""
    return platform_service.list_listings(current_user)


@router.get("/search", response_model=DealSearchResponse)
def search_listings(
    q: str = Query(default=""),
    current_user: AuthUser = Depends(get_current_user),
) -> DealSearchResponse:
    """Perform simple text matching across listings visible to the caller's tenant."""
    return platform_service.search_listings(q, current_user)


@router.post("", response_model=ListingSummary, status_code=201)
def create_listing(payload: ListingCreate, current_user: AuthUser = Depends(get_current_user)) -> ListingSummary:
    """Create a new tenant-scoped listing in the business catalog."""
    return platform_service.create_listing(payload, current_user)
