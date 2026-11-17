"""Redis drops connections (staging 11-2026): requests must not fail because of it."""

from __future__ import annotations

from typing import Any

import fakeredis
import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from redis.asyncio.retry import Retry as AsyncRetry
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError
from structlog.testing import capture_logs

from handball_api.core import jobs
from handball_api.core.jobs import RedisEventBus, RqJobQueue
from handball_api.core.ratelimit import RedisRateLimiter
from handball_api.routers.deps import rate_limit


class DownPipeline:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def incr(self, _key: str) -> None: ...

    def expire(self, _key: str, _s: int) -> None: ...

    async def execute(self) -> Any:
        self.calls.append("execute")
        raise RedisConnectionError("Connection closed by server.")


class DownRedis:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def pipeline(self) -> DownPipeline:
        return DownPipeline(self.calls)


def test_all_api_clients_retry_and_check_idle_connections() -> None:
    url = "redis://127.0.0.1:1/0"
    clients: dict[str, Any] = {
        "limiter": RedisRateLimiter(url)._redis,
        "events": RedisEventBus(url)._redis,
        "jobs": RqJobQueue(url)._conn,
    }
    for name, client in clients.items():
        kw = client.connection_pool.connection_kwargs
        assert kw["health_check_interval"] == 30, name
        assert kw["retry"].get_retries() >= 1, name
        assert RedisConnectionError in kw["retry"]._supported_errors, name
        assert kw["socket_timeout"] is not None, name  # request path: bounded
    assert isinstance(clients["limiter"].connection_pool.connection_kwargs["retry"], AsyncRetry)


async def test_rate_limiter_counts_with_redis() -> None:
    limiter = RedisRateLimiter("redis://ignored", client=fakeredis.FakeAsyncRedis())
    assert [await limiter.hit("login:1.2.3.4", 2, 60) for _ in range(3)] == [True, True, False]


async def test_rate_limiter_fails_open_and_warns_once() -> None:
    down = DownRedis()
    limiter = RedisRateLimiter("redis://ignored", client=down)  # type: ignore[arg-type]
    with capture_logs() as logs:
        assert await limiter.hit("login:1.2.3.4", 1, 60) is True
        assert await limiter.hit("login:1.2.3.4", 1, 60) is True
    assert down.calls == ["execute", "execute"]
    warnings = [e for e in logs if e["event"] == "rate_limit_unavailable"]
    assert len(warnings) == 1 and warnings[0]["log_level"] == "warning"


async def test_rate_limiter_warns_again_after_the_interval(monkeypatch: pytest.MonkeyPatch) -> None:
    limiter = RedisRateLimiter("redis://ignored", client=DownRedis())  # type: ignore[arg-type]
    monkeypatch.setattr(RedisRateLimiter, "WARN_EVERY_S", 0.0)
    with capture_logs() as logs:
        await limiter.hit("k", 1, 60)
        await limiter.hit("k", 1, 60)
    assert len([e for e in logs if e["event"] == "rate_limit_unavailable"]) == 2


class FlakyPublisher:
    def __init__(self, errors: list[Exception]) -> None:
        self.errors = errors
        self.calls = 0

    async def publish(self, *_: object) -> None:
        self.calls += 1
        if self.errors:
            raise self.errors.pop(0)


@pytest.fixture
def no_pause(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(jobs, "PUBLISH_RETRY_PAUSE_S", 0.0)


async def test_event_publish_retries_once_after_a_connection_error(no_pause: None) -> None:
    bus = RedisEventBus("redis://127.0.0.1:1/0")
    flaky = FlakyPublisher([RedisConnectionError("Error 111 connecting to hb-stg-redis:6379.")])
    bus._redis = flaky  # type: ignore[assignment]
    with capture_logs() as logs:
        await bus.publish("match:x", {"status": "running"})
    assert flaky.calls == 2
    assert not [e for e in logs if e["event"] == "event_publish_failed"]


async def test_event_publish_gives_up_quietly_after_the_second_try(no_pause: None) -> None:
    bus = RedisEventBus("redis://127.0.0.1:1/0")
    flaky = FlakyPublisher([RedisConnectionError("closed"), RedisConnectionError("closed")])
    bus._redis = flaky  # type: ignore[assignment]
    with capture_logs() as logs:
        await bus.publish("match:x", {"status": "running"})  # no exception
    assert flaky.calls == 2
    assert [e["attempts"] for e in logs if e["event"] == "event_publish_failed"] == [2]


async def test_event_publish_does_not_repeat_a_timeout(no_pause: None) -> None:
    bus = RedisEventBus("redis://127.0.0.1:1/0")
    flaky = FlakyPublisher([RedisTimeoutError("Timeout reading from socket")])
    bus._redis = flaky  # type: ignore[assignment]
    await bus.publish("match:x", {"status": "running"})
    assert flaky.calls == 1


async def test_rate_limited_route_answers_while_redis_is_down(app: FastAPI) -> None:
    """Login, magic link and the public team page answered 500 when Redis had dropped the
    connection; the limiter now lets the request through."""

    @app.post("/_test/limited", dependencies=[Depends(rate_limit("login"))])
    async def limited() -> dict[str, bool]:
        return {"ok": True}

    app.state.rate_limiter = RedisRateLimiter("redis://ignored", client=DownRedis())  # type: ignore[arg-type]
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as c:
        r = await c.post("/_test/limited")
    assert r.status_code == 200, r.text
