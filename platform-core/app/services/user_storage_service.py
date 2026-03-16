from __future__ import annotations

import logging
from contextlib import contextmanager, suppress
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import inspect, select
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.models.auth_seed import AUTH_USERS
from app.models.platform_tables import AccessRequestRecord, PasswordResetRecord, UserRecord
from app.schemas.auth import (
    AuthAccessRequestCreate,
    AuthAccessRequestResponse,
    AuthAccessRequestSummary,
    AuthPasswordResetResponse,
    AuthRegisterRequest,
)


logger = logging.getLogger("torilaure.identity.persistence")


# Developer: Ravi Kafley
class UserStorageService:
    """Persistent user repository for login and session resolution."""

    def __init__(self) -> None:
        self._available = False

    def initialize(self) -> None:
        try:
            inspector = inspect(engine)
            required_tables = {"users", "access_requests", "password_reset_requests"}
            if not required_tables.issubset(set(inspector.get_table_names())):
                raise SQLAlchemyError("Identity tables are missing. Run `alembic upgrade head`.")
            if settings.bootstrap_auth_users:
                with self.session_scope() as session:
                    self._seed_if_empty(session)
            self._available = True
        except SQLAlchemyError as error:
            self._available = False
            logger.warning("User storage initialization fell back to in-memory mode: %s", error)

    def is_available(self) -> bool:
        return self._available

    @contextmanager
    def session_scope(self):
        session = SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            with suppress(Exception):
                session.rollback()
            raise
        finally:
            session.close()

    def find_by_email(self, email: str) -> dict[str, str] | None:
        normalized_email = email.strip().lower()
        with self.session_scope() as session:
            record = session.scalar(select(UserRecord).where(UserRecord.email == normalized_email))
            if record is None or not record.is_active:
                return None
            return self._to_user_dict(record)

    def find_by_id(self, user_id: str) -> dict[str, str] | None:
        with self.session_scope() as session:
            record = session.scalar(select(UserRecord).where(UserRecord.id == user_id))
            if record is None or not record.is_active:
                return None
            return self._to_user_dict(record)

    def list_users(self) -> list[dict[str, str]]:
        with self.session_scope() as session:
            records = session.scalars(select(UserRecord).order_by(UserRecord.email.asc())).all()
            return [self._to_user_dict(record) for record in records if record.is_active]

    def list_tenant_users(self, tenant_id: str) -> list[dict[str, str]]:
        with self.session_scope() as session:
            records = session.scalars(
                select(UserRecord)
                .where(UserRecord.tenant_id == tenant_id, UserRecord.is_active.is_(True))
                .order_by(UserRecord.full_name.asc(), UserRecord.email.asc())
            ).all()
            return [self._to_user_dict(record) for record in records]

    def create_user(
        self,
        payload: AuthRegisterRequest,
        *,
        password_hash: str,
        tenant_id: str,
        role: str = "investor",
    ) -> dict[str, str]:
        normalized_email = payload.email.strip().lower()
        with self.session_scope() as session:
            existing = session.scalar(select(UserRecord).where(UserRecord.email == normalized_email))
            if existing is not None:
                raise ValueError("An account with that email already exists.")
            record = UserRecord(
                id=f"user-{uuid4().hex[:12]}",
                email=normalized_email,
                password_hash=password_hash,
                full_name=payload.full_name.strip(),
                role=role,
                tenant_id=tenant_id,
                is_active=True,
            )
            session.add(record)
            session.flush()
            session.refresh(record)
            return self._to_user_dict(record)

    def update_password(self, *, email: str, new_password_hash: str) -> bool:
        normalized_email = email.strip().lower()
        with self.session_scope() as session:
            record = session.scalar(select(UserRecord).where(UserRecord.email == normalized_email))
            if record is None or not record.is_active:
                return False
            record.password_hash = new_password_hash
            session.flush()
            return True

    def update_user_role(self, *, email: str, role: str) -> dict[str, str] | None:
        normalized_email = email.strip().lower()
        with self.session_scope() as session:
            record = session.scalar(select(UserRecord).where(UserRecord.email == normalized_email))
            if record is None or not record.is_active:
                return None
            record.role = role.strip().lower()
            session.flush()
            session.refresh(record)
            return self._to_user_dict(record)

    def create_access_request(self, payload: AuthAccessRequestCreate) -> AuthAccessRequestResponse:
        with self.session_scope() as session:
            record = AccessRequestRecord(
                id=f"access-{uuid4().hex[:12]}",
                email=payload.email.strip().lower(),
                full_name=payload.full_name.strip(),
                company_name=payload.company_name.strip(),
                requested_role=payload.requested_role.strip().lower(),
                reason=payload.reason.strip(),
                status="pending",
            )
            session.add(record)
            session.flush()
            session.refresh(record)
            return AuthAccessRequestResponse(
                request_id=record.id,
                status=record.status,
                message="Admin access request submitted for review.",
            )

    def list_access_requests(self, *, status_filter: str | None = None) -> list[AuthAccessRequestSummary]:
        with self.session_scope() as session:
            query = select(AccessRequestRecord).order_by(AccessRequestRecord.created_at.desc())
            if status_filter is not None:
                query = query.where(AccessRequestRecord.status == status_filter)
            records = session.scalars(query).all()
            return [self._to_access_request_summary(record) for record in records]

    def review_access_request(self, *, request_id: str, status: str) -> AuthAccessRequestSummary | None:
        with self.session_scope() as session:
            record = session.scalar(select(AccessRequestRecord).where(AccessRequestRecord.id == request_id))
            if record is None:
                return None
            record.status = status
            session.flush()
            session.refresh(record)
            return self._to_access_request_summary(record)

    def create_password_reset(self, *, user: dict[str, str], reset_token: str, expires_at: datetime) -> AuthPasswordResetResponse:
        with self.session_scope() as session:
            existing_records = session.scalars(
                select(PasswordResetRecord).where(
                    PasswordResetRecord.email == user["email"],
                    PasswordResetRecord.consumed_at.is_(None),
                )
            ).all()
            for record in existing_records:
                record.consumed_at = datetime.now(UTC)

            record = PasswordResetRecord(
                id=f"reset-{uuid4().hex[:12]}",
                user_id=user["id"],
                email=user["email"],
                reset_token=reset_token,
                expires_at=expires_at,
            )
            session.add(record)
            session.flush()
            return AuthPasswordResetResponse(
                message="Password reset token generated for testing.",
                reset_token=reset_token,
            )

    def consume_password_reset(self, *, email: str, reset_token: str) -> bool:
        normalized_email = email.strip().lower()
        with self.session_scope() as session:
            record = session.scalar(
                select(PasswordResetRecord).where(
                    PasswordResetRecord.email == normalized_email,
                    PasswordResetRecord.reset_token == reset_token,
                    PasswordResetRecord.consumed_at.is_(None),
                )
            )
            if record is None:
                return False
            expires_at = record.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=UTC)
            if expires_at <= datetime.now(UTC):
                return False
            record.consumed_at = datetime.now(UTC)
            session.flush()
            return True

    def _seed_if_empty(self, session) -> None:
        if session.scalar(select(UserRecord.id).limit(1)) is None:
            for item in AUTH_USERS:
                session.add(UserRecord(**item))

    def _to_user_dict(self, record: UserRecord) -> dict[str, str]:
        return {
            "id": record.id,
            "email": record.email,
            "password_hash": record.password_hash,
            "full_name": record.full_name,
            "role": record.role,
            "tenant_id": record.tenant_id,
        }

    def _to_access_request_summary(self, record: AccessRequestRecord) -> AuthAccessRequestSummary:
        return AuthAccessRequestSummary(
            request_id=record.id,
            email=record.email,
            full_name=record.full_name,
            company_name=record.company_name,
            requested_role=record.requested_role,
            reason=record.reason,
            status=record.status,
            created_at=record.created_at,
        )


user_storage_service = UserStorageService()
