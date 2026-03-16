from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.schemas.auth import AuthUser
from app.schemas.market import MarketInsight, MarketInsightCreate
from app.services.platform_service import platform_service


# Market endpoints expose regional signals that inform scoring and analyst review.
router = APIRouter()


@router.get("/insights", response_model=list[MarketInsight])
def get_market_insights(current_user: AuthUser = Depends(get_current_user)) -> list[MarketInsight]:
    """Return market intelligence records visible to the caller's tenant."""
    return platform_service.get_market_insights(current_user)


@router.post("/insights", response_model=MarketInsight, status_code=201)
def create_market_insight(
    payload: MarketInsightCreate,
    current_user: AuthUser = Depends(get_current_user),
) -> MarketInsight:
    """Create a market insight record for the caller's tenant."""
    return platform_service.create_market_insight(payload, current_user)
