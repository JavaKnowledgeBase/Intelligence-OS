from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.schemas.auth import AuthUser
from app.schemas.market import MarketInsight, MarketInsightCreate
from app.schemas.roi import (
    RoiBenchmarkCalibrationResponse,
    RoiBenchmarkCompCreate,
    RoiBenchmarkCompSummary,
    RoiBenchmarkCompUpdate,
)
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


@router.get("/benchmark-comps", response_model=list[RoiBenchmarkCompSummary])
def list_benchmark_comps(
    asset_class: str | None = None,
    current_user: AuthUser = Depends(get_current_user),
) -> list[RoiBenchmarkCompSummary]:
    """Return stored external or manually curated comparable records for benchmark calibration."""
    return platform_service.list_benchmark_comps(current_user, asset_class)


@router.post("/benchmark-comps", response_model=RoiBenchmarkCompSummary, status_code=201)
def create_benchmark_comp(
    payload: RoiBenchmarkCompCreate,
    current_user: AuthUser = Depends(get_current_user),
) -> RoiBenchmarkCompSummary:
    """Create a comparable record used to calibrate benchmark ranges."""
    return platform_service.create_benchmark_comp(payload, current_user)


@router.put("/benchmark-comps/{comp_id}", response_model=RoiBenchmarkCompSummary)
def update_benchmark_comp(
    comp_id: str,
    payload: RoiBenchmarkCompUpdate,
    current_user: AuthUser = Depends(get_current_user),
) -> RoiBenchmarkCompSummary:
    """Update inclusion state or note for a benchmark comparable."""
    return platform_service.update_benchmark_comp(comp_id, payload, current_user)


@router.get("/benchmark-calibration/{asset_class}", response_model=RoiBenchmarkCalibrationResponse)
def get_benchmark_calibration(
    asset_class: str,
    location: str | None = None,
    current_user: AuthUser = Depends(get_current_user),
) -> RoiBenchmarkCalibrationResponse:
    """Return the calibrated benchmark profile for an asset class."""
    return platform_service.get_benchmark_calibration(asset_class, current_user, location)
