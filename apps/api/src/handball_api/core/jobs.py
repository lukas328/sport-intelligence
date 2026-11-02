"""Job queue and event bus ports (RQ/Redis adapters, memory adapters for tests).

The API enqueues worker jobs by function path only, so it never imports worker code (ADR 001).
Job progress events are published per match and streamed to browsers via SSE.
"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Protocol

from redis import Redis
from redis.asyncio import Redis as AsyncRedis
from rq import Queue


class JobQueue(Protocol):
    def enqueue(self, queue: str, func: str, job_id: str, kwargs: dict[str, Any]) -> None: ...


@dataclass
class MemoryJobQueue:
    jobs: list[tuple[str, str, str, dict[str, Any]]] = field(default_factory=list)

    def enqueue(self, queue: str, func: str, job_id: str, kwargs: dict[str, Any]) -> None:
        self.jobs.append((queue, func, job_id, kwargs))


class RqJobQueue:
    def __init__(self, redis_url: str) -> None:
        self._conn = Redis.from_url(redis_url)

    def enqueue(self, queue: str, func: str, job_id: str, kwargs: dict[str, Any]) -> None:
        Queue(queue, connection=self._conn).enqueue(
            func,
            kwargs=kwargs,
            job_id=job_id,
            job_timeout=6 * 3600,
            result_ttl=86400,
            failure_ttl=7 * 86400,
        )


class EventBus(Protocol):
    async def publish(self, channel: str, event: dict[str, Any]) -> None: ...

    def subscribe(self, channel: str) -> AsyncIterator[dict[str, Any]]: ...


class MemoryEventBus:
    def __init__(self) -> None:
        self._subs: dict[str, list[asyncio.Queue[dict[str, Any]]]] = defaultdict(list)
        self.published: list[tuple[str, dict[str, Any]]] = []

    async def publish(self, channel: str, event: dict[str, Any]) -> None:
        self.published.append((channel, event))
        for q in self._subs[channel]:
            q.put_nowait(event)

    async def subscribe(self, channel: str) -> AsyncIterator[dict[str, Any]]:
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._subs[channel].append(q)
        try:
            while True:
                yield await q.get()
        finally:
            self._subs[channel].remove(q)


class RedisEventBus:
    def __init__(self, redis_url: str) -> None:
        self._url = redis_url
        self._redis = AsyncRedis.from_url(redis_url)

    async def publish(self, channel: str, event: dict[str, Any]) -> None:
        await self._redis.publish(channel, json.dumps(event, default=str))

    async def subscribe(self, channel: str) -> AsyncIterator[dict[str, Any]]:
        client = AsyncRedis.from_url(self._url)
        pubsub = client.pubsub()
        await pubsub.subscribe(channel)
        try:
            async for message in pubsub.listen():
                if message.get("type") == "message":
                    yield json.loads(message["data"])
        finally:
            await pubsub.unsubscribe(channel)
            await client.aclose()
