from fastapi import APIRouter, Header, HTTPException, Request, Response, status

from app.api.deps import extract_bearer_token
from app.schemas.auth import AuthLoginRequest, AuthLogoutRequest, AuthRefreshRequest, AuthSession, AuthUser
from app.services.auth_service import auth_service
from app.services.audit_service import audit_service
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
