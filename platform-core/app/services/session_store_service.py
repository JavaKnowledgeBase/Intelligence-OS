from __future__ import annotations

import json
from datetime import UTC, datetime

from redis.exceptions import RedisError

from app.core.redis_client import redis_client


class SessionStoreService:
    """Redis-backed session registry for refresh rotation and logout invalidation."""

    def __init__(self) -> None:
        self._local_sessions: dict[str, dict[str, str | int | bool]] = {}

    def create_session(
        self,
        *,
        session_id: str,
        user_id: str,
        refresh_jti: str,
        refresh_expires_at: datetime,
    ) -> None:
        payload = {
            "user_id": user_id,
            "refresh_jti": refresh_jti,
            "refresh_expires_at": int(refresh_expires_at.timestamp()),
            "revoked": False,
        }
        ttl_seconds = max(1, int((refresh_expires_at - datetime.now(UTC)).total_seconds()))
        try:
            redis_client.setex(self._key(session_id), ttl_seconds, json.dumps(payload))
            return
        except RedisError:
            self._local_sessions[session_id] = payload

    def get_session(self, session_id: str) -> dict[str, str | int | bool] | None:
        try:
            raw_value = redis_client.get(self._key(session_id))
            if raw_value is None:
                return None
            payload = json.loads(raw_value)
            if self._is_expired(payload):
                redis_client.delete(self._key(session_id))
                return None
            return payload
        except RedisError:
            payload = self._local_sessions.get(session_id)
            if payload is None:
                return None
            if self._is_expired(payload):
                self._local_sessions.pop(session_id, None)
                return None
            return payload

    def rotate_refresh_token(self, *, session_id: str, refresh_jti: str, refresh_expires_at: datetime) -> bool:
        session = self.get_session(session_id)
        if session is None or bool(session.get("revoked")):
            return False
        session["refresh_jti"] = refresh_jti
        session["refresh_expires_at"] = int(refresh_expires_at.timestamp())
        ttl_seconds = max(1, int((refresh_expires_at - datetime.now(UTC)).total_seconds()))
        try:
            redis_client.setex(self._key(session_id), ttl_seconds, json.dumps(session))
            return True
        except RedisError:
            self._local_sessions[session_id] = session
            return True

    def revoke_session(self, session_id: str) -> None:
        session = self.get_session(session_id)
        if session is None:
            return
        session["revoked"] = True
        expires_at = datetime.fromtimestamp(int(session["refresh_expires_at"]), tz=UTC)
        ttl_seconds = max(1, int((expires_at - datetime.now(UTC)).total_seconds()))
        try:
            redis_client.setex(self._key(session_id), ttl_seconds, json.dumps(session))
            return
        except RedisError:
            self._local_sessions[session_id] = session

    def delete_session(self, session_id: str) -> None:
        try:
            redis_client.delete(self._key(session_id))
        except RedisError:
            self._local_sessions.pop(session_id, None)

    def is_active(self, *, session_id: str, refresh_jti: str | None = None) -> bool:
        session = self.get_session(session_id)
        if session is None or bool(session.get("revoked")):
            return False
        if refresh_jti is not None and session.get("refresh_jti") != refresh_jti:
            return False
        return True

    def _is_expired(self, session: dict[str, str | int | bool]) -> bool:
        expires_at = datetime.fromtimestamp(int(session["refresh_expires_at"]), tz=UTC)
        return expires_at <= datetime.now(UTC)

    def _key(self, session_id: str) -> str:
        return f"session:{session_id}"


session_store_service = SessionStoreService()
