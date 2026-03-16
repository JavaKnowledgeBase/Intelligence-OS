from __future__ import annotations

import json
import logging
from collections import deque
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.exc import SQLAlchemyError

from app.models.security_tables import AuditEventRecord
from app.services.security_storage_service import security_storage_service


logger = logging.getLogger("torilaure.audit")


class AuditService:
    """Structured audit logging service with PostgreSQL persistence and in-memory fallback."""

    def __init__(self) -> None:
        self._events: deque[dict[str, Any]] = deque(maxlen=250)

    def record(
        self,
        *,
        event_type: str,
        outcome: str,
        actor: str | None,
        ip_address: str | None,
        detail: str,
    ) -> None:
        """Store and log an audit-safe event without secrets or raw credentials."""
        event = {
            "timestamp": datetime.now(UTC),
            "event_type": event_type,
            "outcome": outcome,
            "actor": actor,
            "ip_address": ip_address,
            "detail": detail,
        }
        self._events.appendleft(event)
        logger.info(json.dumps({**event, "timestamp": event["timestamp"].isoformat()}))

        try:
            for session in security_storage_service.session_scope():
                session.add(AuditEventRecord(**event))
        except SQLAlchemyError as error:
            logger.warning("Audit event persistence unavailable, retained in memory only: %s", error)

    def recent_events(self) -> list[dict[str, Any]]:
        """Return the most recent audit events for local inspection and testing."""
        return list(self._events)


audit_service = AuditService()

