from __future__ import annotations

import hashlib
import hmac
import re
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt

from app.core.config import settings
from app.models.auth_seed import AUTH_USERS
from app.schemas.auth import (
    AuthAccessRequestCreate,
    AuthAccessRequestReviewResponse,
    AuthAccessRequestResponse,
    AuthAccessRequestSummary,
    AuthLoginRequest,
    AuthPasswordResetConfirmRequest,
    AuthPasswordResetRequest,
    AuthPasswordResetResponse,
    AuthRegisterRequest,
    AuthSession,
    AuthTokenPayload,
    AuthUser,
)
from app.services.revoked_token_service import revoked_token_service
from app.services.session_store_service import session_store_service
from app.services.user_storage_service import user_storage_service


class AuthService:
    """Authentication service backed by persistent user storage with hashed password verification."""

    def __init__(self) -> None:
        self._users = AUTH_USERS

    def _find_user_by_email(self, email: str) -> dict[str, str] | None:
        if user_storage_service.is_available():
            stored_user = user_storage_service.find_by_email(email)
            if stored_user is not None:
                return stored_user
        normalized_email = email.strip().lower()
        for user in self._users:
            if user["email"].lower() == normalized_email:
                return user
        return None

    def _find_user_by_id(self, user_id: str) -> dict[str, str] | None:
        if user_storage_service.is_available():
            stored_user = user_storage_service.find_by_id(user_id)
            if stored_user is not None:
                return stored_user
        for user in self._users:
            if user["id"] == user_id:
                return user
        return None

    def _verify_password(self, password: str, stored_hash: str) -> bool:
        """Verify a password against a salted scrypt hash record."""
        salt_hex, expected_hash = stored_hash.split(":", maxsplit=1)
        candidate_hash = hashlib.scrypt(
            password.encode("utf-8"),
            salt=bytes.fromhex(salt_hex),
            n=2**14,
            r=8,
            p=1,
        ).hex()
        return hmac.compare_digest(candidate_hash, expected_hash)

    def _hash_password(self, password: str) -> str:
        salt = uuid4().hex[:32]
        password_hash = hashlib.scrypt(
            password.encode("utf-8"),
            salt=bytes.fromhex(salt),
            n=2**14,
            r=8,
            p=1,
        ).hex()
        return f"{salt}:{password_hash}"

    def _validate_password_strength(self, password: str) -> None:
        if len(password) < 10:
            raise ValueError("Password must be at least 10 characters long.")
        if not re.search(r"[A-Z]", password):
            raise ValueError("Password must include at least one uppercase letter.")
        if not re.search(r"[a-z]", password):
            raise ValueError("Password must include at least one lowercase letter.")
        if not re.search(r"\d", password):
            raise ValueError("Password must include at least one number.")

    def _build_user(self, user: dict[str, str]) -> AuthUser:
        return AuthUser(
            id=user["id"],
            email=user["email"],
            full_name=user["full_name"],
            role=user["role"],
            tenant_id=user["tenant_id"],
        )

    def _create_token(
        self,
        user: AuthUser,
        *,
        token_type: str,
        expires_in_seconds: int,
        session_id: str,
        token_id: str | None = None,
    ) -> str:
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=expires_in_seconds)
        jti = token_id or uuid4().hex
        payload = {
            "sub": user.id,
            "email": user.email,
            "role": user.role,
            "full_name": user.full_name,
            "tenant_id": user.tenant_id,
            "token_type": token_type,
            "jti": jti,
            "sid": session_id,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
        }
        return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    def decode_token(self, token: str) -> AuthTokenPayload | None:
        """Decode and validate a JWT token."""
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
        except jwt.PyJWTError:
            return None
        decoded = AuthTokenPayload(**payload)
        if revoked_token_service.is_revoked(decoded.jti):
            return None
        return decoded

    def revoke_token(self, token: str | None) -> None:
        """Revoke a token by storing its JWT ID in the in-memory denylist."""
        if not token:
            return
        payload = self.decode_token(token)
        if payload is None:
            return
        revoked_token_service.revoke(
            jti=payload.jti,
            token_type=payload.token_type,
            expires_at=datetime.fromtimestamp(payload.exp, tz=UTC),
        )

    def get_current_user(self, token: str, *, expected_type: str = "access") -> AuthUser | None:
        """Resolve the current user from a validated JWT."""
        payload = self.decode_token(token)
        if payload is None or payload.token_type != expected_type:
            return None
        if not session_store_service.is_active(session_id=payload.sid):
            return None
        user = self._find_user_by_id(payload.sub)
        if user is None:
            return None
        return self._build_user(user)

    def refresh_session(self, refresh_token: str) -> AuthSession | None:
        """Issue a new access/refresh token pair from a valid refresh token."""
        payload = self.decode_token(refresh_token)
        if payload is None or payload.token_type != "refresh":
            return None
        if not session_store_service.is_active(session_id=payload.sid, refresh_jti=payload.jti):
            return None
        user = self.get_current_user(refresh_token, expected_type="refresh")
        if user is None:
            return None
        next_refresh_jti = uuid4().hex
        next_refresh_expires_at = datetime.now(UTC) + timedelta(seconds=settings.refresh_token_expire_seconds)
        self.revoke_token(refresh_token)
        session_store_service.rotate_refresh_token(
            session_id=payload.sid,
            refresh_jti=next_refresh_jti,
            refresh_expires_at=next_refresh_expires_at,
        )
        return AuthSession(
            access_token=self._create_token(
                user,
                token_type="access",
                expires_in_seconds=settings.access_token_expire_seconds,
                session_id=payload.sid,
            ),
            refresh_token=self._create_token(
                user,
                token_type="refresh",
                expires_in_seconds=settings.refresh_token_expire_seconds,
                session_id=payload.sid,
                token_id=next_refresh_jti,
            ),
            expires_in=settings.access_token_expire_seconds,
            user=user,
        )

    def login(self, payload: AuthLoginRequest) -> AuthSession | None:
        """Validate credentials against the seed user set."""
        user = self._find_user_by_email(payload.email)
        if user is None:
            return None
        if not self._verify_password(payload.password, user["password_hash"]):
            return None
        auth_user = self._build_user(user)
        session_id = uuid4().hex
        refresh_jti = uuid4().hex
        refresh_expires_at = datetime.now(UTC) + timedelta(seconds=settings.refresh_token_expire_seconds)
        session_store_service.create_session(
            session_id=session_id,
            user_id=auth_user.id,
            refresh_jti=refresh_jti,
            refresh_expires_at=refresh_expires_at,
        )
        return AuthSession(
            access_token=self._create_token(
                auth_user,
                token_type="access",
                expires_in_seconds=settings.access_token_expire_seconds,
                session_id=session_id,
            ),
            refresh_token=self._create_token(
                auth_user,
                token_type="refresh",
                expires_in_seconds=settings.refresh_token_expire_seconds,
                session_id=session_id,
                token_id=refresh_jti,
            ),
            expires_in=settings.access_token_expire_seconds,
            user=auth_user,
        )

    def register(self, payload: AuthRegisterRequest) -> AuthSession:
        """Create a starter self-serve account and immediately sign the user in."""
        self._validate_password_strength(payload.password)
        tenant_slug = re.sub(r"[^a-z0-9]+", "-", payload.company_name.strip().lower()).strip("-") or "workspace"
        user = user_storage_service.create_user(
            payload,
            password_hash=self._hash_password(payload.password),
            tenant_id=f"tenant-{tenant_slug}",
        )
        return self.login(AuthLoginRequest(email=user["email"], password=payload.password))  # type: ignore[arg-type]

    def request_admin_access(self, payload: AuthAccessRequestCreate) -> AuthAccessRequestResponse:
        """Persist an elevated access request for later review."""
        return user_storage_service.create_access_request(payload)

    def list_access_requests(self, *, status_filter: str | None = None) -> list[AuthAccessRequestSummary]:
        """Return access requests for admin review."""
        return user_storage_service.list_access_requests(status_filter=status_filter)

    def review_access_request(self, *, request_id: str, status: str) -> AuthAccessRequestReviewResponse:
        """Approve or reject an access request and elevate an existing user when possible."""
        review = user_storage_service.review_access_request(request_id=request_id, status=status)
        if review is None:
            raise ValueError("Access request not found.")

        granted_user_id: str | None = None
        message = f"Access request marked as {status}."
        if status == "approved":
            existing_user = user_storage_service.update_user_role(email=review.email, role=review.requested_role)
            if existing_user is not None:
                granted_user_id = existing_user["id"]
                message = f"Access request approved and role updated to {review.requested_role}."
            else:
                message = "Access request approved. No existing user account matched that email yet."

        return AuthAccessRequestReviewResponse(
            request_id=review.request_id,
            status=review.status,
            message=message,
            granted_user_id=granted_user_id,
        )

    def request_password_reset(self, payload: AuthPasswordResetRequest) -> AuthPasswordResetResponse:
        """Create a one-time password reset token for a known user."""
        user = self._find_user_by_email(payload.email)
        if user is None:
            return AuthPasswordResetResponse(message="If the account exists, a reset token has been issued for testing.")
        reset_token = uuid4().hex
        expires_at = datetime.now(UTC) + timedelta(minutes=15)
        return user_storage_service.create_password_reset(user=user, reset_token=reset_token, expires_at=expires_at)

    def confirm_password_reset(self, payload: AuthPasswordResetConfirmRequest) -> AuthPasswordResetResponse:
        """Reset a known account password using a one-time token."""
        self._validate_password_strength(payload.new_password)
        if not user_storage_service.consume_password_reset(email=payload.email, reset_token=payload.reset_token):
            raise ValueError("Invalid or expired reset token.")
        if not user_storage_service.update_password(
            email=payload.email,
            new_password_hash=self._hash_password(payload.new_password),
        ):
            raise ValueError("Unable to update password for that account.")
        return AuthPasswordResetResponse(message="Password updated successfully. You can sign in with the new password.")


auth_service = AuthService()
