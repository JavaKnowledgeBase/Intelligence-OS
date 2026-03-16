from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.exc import SQLAlchemyError

from app.models.security_tables import RevokedTokenRecord
from app.services.security_storage_service import security_storage_service


class RevokedTokenService:
    """Persistent JWT denylist backed by PostgreSQL with local fallback."""

    def __init__(self) -> None:
        self._local_revocations: set[str] = set()

    def is_revoked(self, jti: str) -> bool:
        if jti in self._local_revocations:
            return True
        try:
            for session in security_storage_service.session_scope():
                record = session.get(RevokedTokenRecord, jti)
                if record is not None and record.expires_at > datetime.now(UTC):
                    return True
        except SQLAlchemyError:
            return jti in self._local_revocations
        return False

    def revoke(self, *, jti: str, token_type: str, expires_at: datetime) -> None:
        self._local_revocations.add(jti)
        try:
            for session in security_storage_service.session_scope():
                session.merge(
                    RevokedTokenRecord(
                        jti=jti,
                        token_type=token_type,
                        expires_at=expires_at,
                    )
                )
        except SQLAlchemyError:
            return


revoked_token_service = RevokedTokenService()

