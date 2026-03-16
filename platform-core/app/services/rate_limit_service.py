from __future__ import annotations

from collections import deque
from datetime import UTC, datetime, timedelta

from redis.exceptions import RedisError

from app.core.redis_client import redis_client


class RateLimitService:
    """Redis-backed rate limiter with in-memory fallback for local resilience."""

    def __init__(self) -> None:
        self._attempts: dict[str, deque[datetime]] = {}

    def is_allowed(self, key: str, *, limit: int, window_seconds: int) -> tuple[bool, int]:
        """Return whether the caller is allowed and how many seconds remain if blocked."""
        redis_key = f"rate_limit:{key}"
        try:
            current = redis_client.get(redis_key)
            if current is not None and int(current) >= limit:
                ttl = redis_client.ttl(redis_key)
                return False, max(1, ttl if ttl > 0 else window_seconds)
            return True, 0
        except RedisError:
            return self._is_allowed_memory(key, limit=limit, window_seconds=window_seconds)

    def _is_allowed_memory(self, key: str, *, limit: int, window_seconds: int) -> tuple[bool, int]:
        now = datetime.now(UTC)
        window_start = now - timedelta(seconds=window_seconds)
        attempts = self._attempts.setdefault(key, deque())

        while attempts and attempts[0] < window_start:
            attempts.popleft()

        if len(attempts) >= limit:
            retry_after = max(1, int((attempts[0] + timedelta(seconds=window_seconds) - now).total_seconds()))
            return False, retry_after
        return True, 0

    def register_attempt(self, key: str, *, window_seconds: int = 300) -> None:
        """Record a new attempt for the given rate-limit key."""
        redis_key = f"rate_limit:{key}"
        try:
            current = redis_client.incr(redis_key)
            if current == 1:
                redis_client.expire(redis_key, window_seconds)
            return
        except RedisError:
            attempts = self._attempts.setdefault(key, deque())
            attempts.append(datetime.now(UTC))

    def reset(self, key: str) -> None:
        """Clear tracked attempts after a successful authentication event."""
        try:
            redis_client.delete(f"rate_limit:{key}")
        except RedisError:
            self._attempts.pop(key, None)


rate_limit_service = RateLimitService()

