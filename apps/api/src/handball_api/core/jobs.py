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

from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import RedisError
from rq import Queue
from rq.job import Job

from handball_api.core.logging import get_logger
from handball_jobkit.redisconn import async_redis, sync_redis

log = get_logger("handball_api.jobs")

QUEUES = ("default", "pipeline", "gpu")
DEFAULT_TIMEOUT_S = 6 * 3600

# Redis clients come from handball_jobkit.redisconn: health check, keepalive and retry with
# backoff, because the proxy in front of Redis drops idle connections (Azure Container Apps).
# a subscriber that hears nothing pings this often, so its connection never counts as idle
SUBSCRIBE_PING_S = 60.0
PUBLISH_TIMEOUT_S = 2.0
PUBLISH_RETRY_PAUSE_S = 0.5


class JobQueue(Protocol):
    def enqueue(
        self,
        queue: str,
        func: str,
        job_id: str,
        kwargs: dict[str, Any],
        timeout_s: int | None = None,
    ) -> None: ...

    def depths(self) -> dict[str, int]: ...

    def exists(self, job_id: str) -> bool | None:
        """Whether the queue still knows the job (None: the queue cannot be asked)."""
        ...


@dataclass
class MemoryJobQueue:
    jobs: list[tuple[str, str, str, dict[str, Any]]] = field(default_factory=list)
    timeouts: dict[str, int] = field(default_factory=dict)  # job id -> seconds
    lost: set[str] = field(default_factory=set)  # tests: jobs a Redis restart has wiped out

    def enqueue(
        self,
        queue: str,
        func: str,
        job_id: str,
        kwargs: dict[str, Any],
        timeout_s: int | None = None,
    ) -> None:
        self.jobs.append((queue, func, job_id, kwargs))
        self.timeouts[job_id] = timeout_s or DEFAULT_TIMEOUT_S

    def depths(self) -> dict[str, int]:
        return {q: 0 for q in QUEUES}

    def exists(self, job_id: str) -> bool | None:
        return job_id not in self.lost and any(j[2] == job_id for j in self.jobs)


class RqJobQueue:
    def __init__(self, redis_url: str) -> None:
        # bounded (read and connect timeout): a hanging Redis must fail the request instead of
        # blocking a worker thread. No fail-open here: a job that never reaches the queue would
        # leave the match waiting forever, so the request fails and its transaction rolls back.
        self._conn = sync_redis(redis_url)

    def enqueue(
        self,
        queue: str,
        func: str,
        job_id: str,
        kwargs: dict[str, Any],
        timeout_s: int | None = None,
    ) -> None:
        """`timeout_s`: how long the worker may run the job (default six hours; a full game's
        analysis on a CPU worker takes longer, see services/videos.job_budget_s)."""
        Queue(queue, connection=self._conn).enqueue(
            func,
            kwargs=kwargs,
            job_id=job_id,
            job_timeout=timeout_s or DEFAULT_TIMEOUT_S,
            result_ttl=86400,
            failure_ttl=7 * 86400,
        )

    def depths(self) -> dict[str, int]:
        """Waiting jobs per queue (alerting: a growing GPU queue means missing capacity)."""
        return {q: len(Queue(q, connection=self._conn)) for q in QUEUES}

    def exists(self, job_id: str) -> bool | None:
        """Whether Redis still holds the job: Redis runs without persistence, so a restart (on
        staging with every deploy) wipes out the jobs that were only waiting. None when Redis
        cannot be asked (then nothing is concluded)."""
        try:
            return bool(Job.exists(job_id, connection=self._conn))
        except RedisError as exc:
            log.warning("job_exists_failed", job=job_id, error=str(exc))
            return None


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
        # short read timeout: publishing is best effort and runs inside the caller's request
        self._redis = async_redis(redis_url, socket_timeout=PUBLISH_TIMEOUT_S)

    async def publish(self, channel: str, event: dict[str, Any]) -> None:
        """Best effort: the state is already in Postgres and the browser gets a snapshot when it
        reconnects, so a Redis hiccup must not fail (and roll back) the caller's transaction.
        The client already reconnects and retries a dropped connection; if Redis is briefly gone
        (restart) that is over in a second, so a connection error gets one more try after a
        pause. A timeout does not: it has already cost its time."""
        data = json.dumps(event, default=str)
        for attempt in (1, 2):
            try:
                await self._redis.publish(channel, data)
                return
            except RedisConnectionError as e:
                if attempt == 1:
                    await asyncio.sleep(PUBLISH_RETRY_PAUSE_S)
                    continue
                log.warning("event_publish_failed", channel=channel, error=str(e), attempts=2)
            except RedisError as e:
                log.warning("event_publish_failed", channel=channel, error=str(e), attempts=1)
            return

    async def subscribe(self, channel: str) -> AsyncIterator[dict[str, Any]]:
        # blocking: the listener waits up to SUBSCRIBE_PING_S per read, no short read timeout
        client = async_redis(self._url, blocking=True)
        pubsub = client.pubsub()
        await pubsub.subscribe(channel)
        try:
            while True:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=SUBSCRIBE_PING_S
                )
                if message is None:
                    await pubsub.ping()
                elif message.get("type") == "message":
                    yield json.loads(message["data"])
        finally:
            await pubsub.unsubscribe(channel)
            await client.aclose()
