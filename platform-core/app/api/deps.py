from fastapi import Header, HTTPException, status

from app.schemas.auth import AuthUser
from app.services.auth_service import auth_service


def extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token


def get_current_user(authorization: str | None = Header(default=None)) -> AuthUser:
    """Resolve the current authenticated user from a bearer token."""
    token = extract_bearer_token(authorization)
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token.")
    user = auth_service.get_current_user(token, expected_type="access")
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token.")
    return user

