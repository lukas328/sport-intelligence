"""Fixed-window rate limiting for sensitive endpoints (auth)."""

from __future__ import annotations

import time
from typing import Protocol

from redis.asyncio import Redis


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
    def __init__(self, url: str) -> None:
        self._redis = Redis.from_url(url)

    async def hit(self, key: str, limit: int, window_s: int) -> bool:
        bucket = f"rl:{key}:{int(time.time()) // window_s}"
        pipe = self._redis.pipeline()
        pipe.incr(bucket)
        pipe.expire(bucket, window_s)
        count, _ = await pipe.execute()
        return int(count) <= limit
