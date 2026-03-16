from __future__ import annotations

import logging
from contextlib import suppress

from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import SessionLocal, engine


logger = logging.getLogger("torilaure.security.persistence")


class SecurityStorageService:
    """Bootstraps durable security storage in PostgreSQL."""

    def initialize(self) -> None:
        try:
            inspector = inspect(engine)
            required_tables = {"audit_events", "revoked_tokens"}
            if not required_tables.issubset(set(inspector.get_table_names())):
                raise SQLAlchemyError("Security tables are missing. Run `alembic upgrade head`.")
        except SQLAlchemyError as error:
            logger.warning("Security storage initialization fell back to in-memory mode: %s", error)

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


security_storage_service = SecurityStorageService()
