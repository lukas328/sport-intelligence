"""Redis clients that reconnect on their own: a dropped idle connection costs no error."""

from __future__ import annotations

from typing import Any

import fakeredis
import pytest
import redis
import redis.asyncio
from redis.asyncio.retry import Retry as AsyncRetry
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError
from redis.retry import Retry

from handball_jobkit import redisconn
from handball_jobkit.redisconn import async_redis, redis_options, sync_redis


def test_sync_client_retries_with_backoff_and_checks_idle_connections() -> None:
    kw = sync_redis("redis://127.0.0.1:1/0").connection_pool.connection_kwargs
    assert kw["health_check_interval"] == 30
    assert kw["socket_keepalive"] is True
    assert kw["socket_connect_timeout"] == redisconn.CONNECT_TIMEOUT_S
    assert kw["socket_timeout"] == redisconn.SOCKET_TIMEOUT_S
    retry = kw["retry"]
    assert isinstance(retry, Retry)
    assert retry.get_retries() == redisconn.RETRIES >= 1
    assert {RedisConnectionError, RedisTimeoutError} <= set(retry._supported_errors)


def test_blocking_client_has_no_read_timeout() -> None:
    """RQ's BLPOP and pub/sub listeners wait on purpose: RQ sets its own read timeout above
    its BLPOP timeout, so the client must not cut the wait short."""
    kw = sync_redis("redis://127.0.0.1:1/0", blocking=True).connection_pool.connection_kwargs
    assert kw.get("socket_timeout") is None
    assert kw["socket_connect_timeout"] == redisconn.CONNECT_TIMEOUT_S
    assert kw["health_check_interval"] == 30


def test_async_client_uses_the_async_retry() -> None:
    kw = async_redis("redis://127.0.0.1:1/0").connection_pool.connection_kwargs
    assert isinstance(kw["retry"], AsyncRetry)
    assert kw["health_check_interval"] == 30


def test_overrides_win() -> None:
    kw = sync_redis("redis://127.0.0.1:1/0", socket_timeout=1.5).connection_pool.connection_kwargs
    assert kw["socket_timeout"] == 1.5


def _fake_pool_opts(opts: dict[str, Any]) -> dict[str, Any]:
    # fakeredis has no socket (and FakeRedis() drops retry options): build the pool ourselves
    # with what decides the reconnect behaviour (its async connection fails redis-py's health
    # check ping, so the health check stays out here; its presence is checked above)
    keep = ("retry", "retry_on_error")
    return {"server": fakeredis.FakeServer(), **{k: v for k, v in opts.items() if k in keep}}


def test_a_dropped_connection_is_reestablished_transparently(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from fakeredis._clients._sync import FakeRedisConnection

    pool = redis.ConnectionPool(
        connection_class=FakeRedisConnection, **_fake_pool_opts(redis_options())
    )
    client = redis.Redis(connection_pool=pool)
    client.ping()  # pooled connection, then the proxy drops it while idle
    real = FakeRedisConnection.send_packed_command
    calls = {"n": 0}

    def dropped_once(self: Any, *a: Any, **k: Any) -> Any:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RedisConnectionError("Connection closed by server.")
        return real(self, *a, **k)  # type: ignore[no-untyped-call]

    monkeypatch.setattr(FakeRedisConnection, "send_packed_command", dropped_once)
    monkeypatch.setattr("time.sleep", lambda _s: None)
    assert client.incr("k") == 1  # no exception: reconnected and repeated
    assert calls["n"] >= 2


async def test_async_dropped_connection_is_reestablished_transparently(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from fakeredis._clients._async import FakeAsyncRedisConnection

    pool = redis.asyncio.ConnectionPool(
        connection_class=FakeAsyncRedisConnection, **_fake_pool_opts(redis_options(asyncio=True))
    )
    client = redis.asyncio.Redis(connection_pool=pool)
    await client.ping()
    real = FakeAsyncRedisConnection.send_packed_command
    calls = {"n": 0}

    async def dropped_once(self: Any, *a: Any, **k: Any) -> Any:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RedisConnectionError("Error UNKNOWN while writing to socket. Connection lost.")
        return await real(self, *a, **k)

    monkeypatch.setattr(FakeAsyncRedisConnection, "send_packed_command", dropped_once)
    assert await client.incr("k") == 1
    assert calls["n"] >= 2
