from fastapi import FastAPI
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import logging

from app.api.router import api_router
from app.core.config import settings
from app.services.platform_storage_service import platform_storage_service
from app.services.security_storage_service import security_storage_service
from app.services.user_storage_service import user_storage_service


# Configure local structured logging early so audit events appear consistently.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

# Developer: Ravi Kafley
# Create the main FastAPI app and attach global middleware and API routes.
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    summary="Platform core for Torilaure Intelligence OS.",
)

security_storage_service.initialize()
user_storage_service.initialize()
platform_storage_service.initialize()

# Allow the React frontend to call the API during local development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_prefix)


@app.middleware("http")
async def add_security_headers(request: Request, call_next) -> Response:
    """Apply baseline HTTP security headers to every response."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none'; base-uri 'self'"
    return response


@app.get("/", tags=["meta"])
def read_root() -> dict[str, str]:
    """Lightweight health-style endpoint for local verification."""
    return {"message": "Torilaure Intelligence OS platform core is running."}
