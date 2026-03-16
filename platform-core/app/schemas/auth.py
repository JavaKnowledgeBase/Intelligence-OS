from datetime import datetime
from typing import Literal

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


class AuthRegisterRequest(BaseModel):
    """Self-serve account creation payload for the starter template."""

    full_name: str
    email: EmailStr
    password: str
    company_name: str


class AuthAccessRequestCreate(BaseModel):
    """Request elevated admin access from the login page."""

    full_name: str
    email: EmailStr
    company_name: str
    requested_role: str = "admin"
    reason: str


class AuthAccessRequestResponse(BaseModel):
    """Stored admin-access request summary returned to the UI."""

    request_id: str
    status: str
    message: str


class AuthAccessRequestSummary(BaseModel):
    """Admin-facing summary of an elevated access request."""

    request_id: str
    email: EmailStr
    full_name: str
    company_name: str
    requested_role: str
    reason: str
    status: str
    created_at: datetime | None = None


class AuthAccessRequestReviewRequest(BaseModel):
    """Review payload for approving or rejecting an access request."""

    status: Literal["approved", "rejected"]


class AuthAccessRequestReviewResponse(BaseModel):
    """Review result returned after an admin processes an access request."""

    request_id: str
    status: str
    message: str
    granted_user_id: str | None = None


class AuthPasswordResetRequest(BaseModel):
    """Request a one-time password reset token for a known email."""

    email: EmailStr


class AuthPasswordResetConfirmRequest(BaseModel):
    """Reset a password using the issued one-time token."""

    email: EmailStr
    reset_token: str
    new_password: str


class AuthPasswordResetResponse(BaseModel):
    """Password-reset response payload used by the starter UI."""

    message: str
    reset_token: str | None = None
