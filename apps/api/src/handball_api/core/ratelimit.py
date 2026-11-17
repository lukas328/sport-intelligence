"""Fixed-window rate limiting for sensitive endpoints (auth)."""

from __future__ import annotations

import time
from typing import Protocol

from redis.asyncio import Redis
from redis.exceptions import RedisError

from handball_api.core.logging import get_logger
from handball_jobkit.redisconn import async_redis

log = get_logger("handball_api.ratelimit")


def parse_rate(rate: str) -> tuple[int, int]:
    count, _, seconds = rate.partition("/")
    return int(count), int(seconds)


class RateLimiter(Protocol):
    async def hit(self, key: str, limit: int, window_s: int) -> bool:
        """Count one hit; return False if the limit is exceeded."""
        ...


class MemoryRateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, tuple[int, float]] = {}

    async def hit(self, key: str, limit: int, window_s: int) -> bool:
        now = time.monotonic()
        count, start = self._hits.get(key, (0, now))
        if now - start >= window_s:
            count, start = 0, now
        count += 1
        self._hits[key] = (count, start)
        return count <= limit

    def reset(self) -> None:
        self._hits.clear()


class RedisRateLimiter:
    """Counts in Redis, shared by all API replicas.

    Fails open: if Redis is unreachable even after the client's retries, the request is allowed
    and a warning is logged (at most once per WARN_EVERY_S). The limiter is a brake on guessing
    and mail flooding, not a gate: passwords, TOTP codes and magic-link tokens are still checked
    against Postgres, and password hashing (argon2) keeps guessing slow. Failing closed would
    turn every Redis hiccup into "login does not work" for every coach (staging 11-2026: HTTP
    500 on login and the public team page until the next try). Nothing here stores auth state:
    sessions live in Postgres, so no auth decision depends on Redis.
    """

    WARN_EVERY_S = 60.0
    TIMEOUT_S = 2.0  # a hanging Redis must not hold the login for long

    def __init__(self, url: str, client: Redis | None = None) -> None:
        self._redis = (
            client if client is not None else async_redis(url, socket_timeout=self.TIMEOUT_S)
        )
        self._warned_at: float | None = None

    async def hit(self, key: str, limit: int, window_s: int) -> bool:
        bucket = f"rl:{key}:{int(time.time()) // window_s}"
        try:
            pipe = self._redis.pipeline()
            pipe.incr(bucket)
            pipe.expire(bucket, window_s)
            count, _ = await pipe.execute()
        except RedisError as exc:
            self._warn(exc)
            return True
        return int(count) <= limit

    def _warn(self, exc: Exception) -> None:
        now = time.monotonic()
        if self._warned_at is None or now - self._warned_at >= self.WARN_EVERY_S:
            self._warned_at = now
            log.warning("rate_limit_unavailable", error=str(exc), action="allowing requests")
