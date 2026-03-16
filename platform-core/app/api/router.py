from fastapi import APIRouter

from app.api.routes import alerts, auth, ingestion, listings, market, projects


# Central router that groups the first platform domains behind one API prefix.
api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(listings.router, prefix="/listings", tags=["listings"])
api_router.include_router(market.router, prefix="/market", tags=["market"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
api_router.include_router(ingestion.router, prefix="/ingestion", tags=["ingestion"])
