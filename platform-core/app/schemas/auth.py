from pydantic import BaseModel, EmailStr


class AuthLoginRequest(BaseModel):
    """Credentials payload for email/password login."""

    email: EmailStr
    password: str


class AuthUser(BaseModel):
    """Authenticated user summary stored by the frontend session."""

    id: str
    email: EmailStr
    full_name: str
    role: str
    tenant_id: str


class AuthSession(BaseModel):
    """Token-like session response returned after successful login."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: AuthUser


class AuthTokenPayload(BaseModel):
    """Decoded JWT claims used for authenticated request validation."""

    sub: str
    email: EmailStr
    role: str
    full_name: str
    tenant_id: str
    token_type: str
    jti: str
    sid: str
    exp: int
    iat: int


class AuthRefreshRequest(BaseModel):
    """Refresh token payload for issuing a new access token pair."""

    refresh_token: str


class AuthLogoutRequest(BaseModel):
    """Optional refresh token payload used to revoke the current session."""

    refresh_token: str | None = None
