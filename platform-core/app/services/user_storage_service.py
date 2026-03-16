from __future__ import annotations

import logging
from contextlib import contextmanager, suppress

from sqlalchemy import inspect, select
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.models.auth_seed import AUTH_USERS
from app.models.platform_tables import UserRecord


logger = logging.getLogger("torilaure.identity.persistence")


# Developer: Ravi Kafley
class UserStorageService:
    """Persistent user repository for login and session resolution."""

    def __init__(self) -> None:
        self._available = False

    def initialize(self) -> None:
        try:
            inspector = inspect(engine)
            if "users" not in inspector.get_table_names():
                raise SQLAlchemyError("User table is missing. Run `alembic upgrade head`.")
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


user_storage_service = UserStorageService()
