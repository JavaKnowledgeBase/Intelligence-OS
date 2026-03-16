from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status

from app.api.deps import extract_bearer_token, get_current_user
from app.schemas.auth import (
    AuthAccessRequestCreate,
    AuthAccessRequestReviewRequest,
    AuthAccessRequestReviewResponse,
    AuthAccessRequestResponse,
    AuthAccessRequestSummary,
    AuthLoginRequest,
    AuthLogoutRequest,
    AuthPasswordResetConfirmRequest,
    AuthPasswordResetRequest,
    AuthPasswordResetResponse,
    AuthRefreshRequest,
    AuthRegisterRequest,
    AuthSession,
    AuthUser,
)
from app.services.auth_service import auth_service
from app.services.audit_service import audit_service
from app.services.authorization_service import authorization_service
from app.services.rate_limit_service import rate_limit_service
from app.services.session_store_service import session_store_service


# Authentication endpoints provide the first real login flow for the frontend.
router = APIRouter()
AUTH_RATE_LIMIT = 5
AUTH_WINDOW_SECONDS = 60 * 5


@router.post("/login", response_model=AuthSession)
def login(payload: AuthLoginRequest, request: Request) -> AuthSession:
    """Validate credentials and return a token-like session payload."""
    client_ip = request.client.host if request.client else "unknown"
    normalized_email = payload.email.strip().lower()
    rate_limit_key = f"{client_ip}:{normalized_email}"

    allowed, retry_after = rate_limit_service.is_allowed(
        rate_limit_key,
        limit=AUTH_RATE_LIMIT,
        window_seconds=AUTH_WINDOW_SECONDS,
    )
    if not allowed:
        audit_service.record(
            event_type="auth.login.rate_limited",
            outcome="blocked",
            actor=normalized_email,
            ip_address=client_ip,
            detail=f"Too many login attempts. Retry after {retry_after} seconds.",
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many login attempts. Retry in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )

    session = auth_service.login(payload)
    if session is None:
        rate_limit_service.register_attempt(rate_limit_key, window_seconds=AUTH_WINDOW_SECONDS)
        audit_service.record(
            event_type="auth.login",
            outcome="failure",
            actor=normalized_email,
            ip_address=client_ip,
            detail="Invalid credentials.",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    rate_limit_service.reset(rate_limit_key)
    audit_service.record(
        event_type="auth.login",
        outcome="success",
        actor=normalized_email,
        ip_address=client_ip,
        detail=f"Authenticated as role {session.user.role}.",
    )
    return session


@router.post("/register", response_model=AuthSession, status_code=201)
def register(payload: AuthRegisterRequest, request: Request) -> AuthSession:
    """Create a starter self-serve account and return a signed-in session."""
    client_ip = request.client.host if request.client else "unknown"
    try:
        session = auth_service.register(payload)
    except ValueError as error:
        audit_service.record(
            event_type="auth.register",
            outcome="failure",
            actor=payload.email.strip().lower(),
            ip_address=client_ip,
            detail=str(error),
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    audit_service.record(
        event_type="auth.register",
        outcome="success",
        actor=session.user.email,
        ip_address=client_ip,
        detail="Self-serve account created.",
    )
    return session


@router.post("/request-admin-access", response_model=AuthAccessRequestResponse, status_code=201)
def request_admin_access(payload: AuthAccessRequestCreate, request: Request) -> AuthAccessRequestResponse:
    """Store a request for admin review from the login page."""
    client_ip = request.client.host if request.client else "unknown"
    response = auth_service.request_admin_access(payload)
    audit_service.record(
        event_type="auth.request_admin_access",
        outcome="success",
        actor=payload.email.strip().lower(),
        ip_address=client_ip,
        detail=f"Requested role {payload.requested_role}.",
    )
    return response


@router.get("/access-requests", response_model=list[AuthAccessRequestSummary])
def list_access_requests(
    status_filter: Literal["pending", "approved", "rejected"] | None = Query(default=None, alias="status"),
    current_user: AuthUser = Depends(get_current_user),
) -> list[AuthAccessRequestSummary]:
    """Return submitted access requests for admin review."""
    authorization_service.require_admin(current_user)
    return auth_service.list_access_requests(status_filter=status_filter)


@router.patch("/access-requests/{request_id}", response_model=AuthAccessRequestReviewResponse)
def review_access_request(
    request_id: str,
    payload: AuthAccessRequestReviewRequest,
    request: Request,
    current_user: AuthUser = Depends(get_current_user),
) -> AuthAccessRequestReviewResponse:
    """Approve or reject an access request as an admin."""
    authorization_service.require_admin(current_user)
    client_ip = request.client.host if request.client else "unknown"
    try:
        response = auth_service.review_access_request(request_id=request_id, status=payload.status)
    except ValueError as error:
        audit_service.record(
            event_type="auth.access_request.review",
            outcome="failure",
            actor=current_user.email,
            ip_address=client_ip,
            detail=str(error),
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    audit_service.record(
        event_type="auth.access_request.review",
        outcome="success",
        actor=current_user.email,
        ip_address=client_ip,
        detail=f"Marked {request_id} as {payload.status}.",
    )
    return response


@router.post("/password-reset/request", response_model=AuthPasswordResetResponse)
def request_password_reset(payload: AuthPasswordResetRequest, request: Request) -> AuthPasswordResetResponse:
    """Issue a one-time reset token for starter local testing."""
    client_ip = request.client.host if request.client else "unknown"
    response = auth_service.request_password_reset(payload)
    audit_service.record(
        event_type="auth.password_reset.request",
        outcome="success",
        actor=payload.email.strip().lower(),
        ip_address=client_ip,
        detail="Password reset token requested.",
    )
    return response


@router.post("/password-reset/confirm", response_model=AuthPasswordResetResponse)
def confirm_password_reset(payload: AuthPasswordResetConfirmRequest, request: Request) -> AuthPasswordResetResponse:
    """Reset a password with a one-time token."""
    client_ip = request.client.host if request.client else "unknown"
    try:
        response = auth_service.confirm_password_reset(payload)
    except ValueError as error:
        audit_service.record(
            event_type="auth.password_reset.confirm",
            outcome="failure",
            actor=payload.email.strip().lower(),
            ip_address=client_ip,
            detail=str(error),
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    audit_service.record(
        event_type="auth.password_reset.confirm",
        outcome="success",
        actor=payload.email.strip().lower(),
        ip_address=client_ip,
        detail="Password reset completed.",
    )
    return response


@router.get("/me", response_model=AuthUser)
def read_current_user(authorization: str | None = Header(default=None)) -> AuthUser:
    """Return the authenticated user for a valid JWT bearer token."""
    token = extract_bearer_token(authorization)
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token.")
    user = auth_service.get_current_user(token, expected_type="access")
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token.")
    return user


@router.post("/refresh", response_model=AuthSession)
def refresh_session(payload: AuthRefreshRequest, request: Request) -> AuthSession:
    """Issue a fresh access/refresh token pair from a valid refresh token."""
    client_ip = request.client.host if request.client else "unknown"
    session = auth_service.refresh_session(payload.refresh_token)
    if session is None:
        audit_service.record(
            event_type="auth.refresh",
            outcome="failure",
            actor=None,
            ip_address=client_ip,
            detail="Invalid or expired refresh token.",
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token.")
    audit_service.record(
        event_type="auth.refresh",
        outcome="success",
        actor=session.user.email,
        ip_address=client_ip,
        detail="Issued a new token pair.",
    )
    return session


@router.post("/logout", status_code=204)
def logout(
    payload: AuthLogoutRequest,
    request: Request,
    response: Response,
    authorization: str | None = Header(default=None),
) -> Response:
    """Revoke the current access token and optional refresh token."""
    client_ip = request.client.host if request.client else "unknown"
    access_token = extract_bearer_token(authorization)
    user = auth_service.get_current_user(access_token, expected_type="access") if access_token else None
    access_payload = auth_service.decode_token(access_token) if access_token else None
    refresh_payload = auth_service.decode_token(payload.refresh_token) if payload.refresh_token else None
    auth_service.revoke_token(access_token)
    auth_service.revoke_token(payload.refresh_token)
    if access_payload is not None:
        session_store_service.delete_session(access_payload.sid)
    elif refresh_payload is not None:
        session_store_service.delete_session(refresh_payload.sid)
    audit_service.record(
        event_type="auth.logout",
        outcome="success",
        actor=user.email if user else None,
        ip_address=client_ip,
        detail="Session tokens revoked.",
    )
    return response
