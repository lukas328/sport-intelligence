"""Redis clients that survive dropped connections (one place for the options, API and workers).

In Azure Container Apps Redis runs as its own app behind a TCP ingress. That proxy drops idle
connections without telling either side, and Redis itself restarts now and then. A pooled
connection then fails on its next use with "Connection closed by server" or "Connection refused".
Every client therefore gets:

- `health_check_interval`: a connection idle for longer than this is pinged before it is used
  and replaced if the ping fails. Pub/sub connections send the ping while they wait, so their
  connection never looks idle to the proxy.
- TCP keepalive with short timers (the Linux default only probes after two hours), so a dead
  peer is noticed within about a minute and stateful middleboxes keep the flow.
- `retry` on ConnectionError and TimeoutError with exponential backoff and jitter: redis-py
  reconnects and repeats the command, so a dropped idle connection costs one reconnect instead
  of an error. Without an explicit `retry`, `Redis.from_url` does not retry at all.
- a connect timeout, and a read timeout where it is safe (`blocking=False`). Clients that block
  on purpose (RQ's BLPOP dequeue, pub/sub listeners) must not get a short read timeout: RQ sets
  its own `socket_timeout` just above its BLPOP timeout and keeps a longer one if given.
"""

from __future__ import annotations

import socket
from typing import Any

from redis import Redis
from redis.asyncio import Redis as AsyncRedis
from redis.asyncio.retry import Retry as AsyncRetry
from redis.backoff import ExponentialWithJitterBackoff
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError
from redis.retry import Retry

HEALTH_CHECK_INTERVAL_S = 30
CONNECT_TIMEOUT_S = 5.0
SOCKET_TIMEOUT_S = 5.0
RETRIES = 3  # attempts after the first one
BACKOFF_BASE_S = 0.1
BACKOFF_CAP_S = 2.0
RETRY_ON: tuple[type[Exception], ...] = (RedisConnectionError, RedisTimeoutError)
# first probe after 30 s idle, then every 10 s, give up after 3 missed probes
KEEPALIVE_IDLE_S, KEEPALIVE_INTERVAL_S, KEEPALIVE_COUNT = 30, 10, 3


def keepalive_options() -> dict[int, int]:
    """TCP keepalive timers for the platform (Linux names; macOS calls the idle timer
    TCP_KEEPALIVE). Empty if the platform offers none, then the OS defaults apply."""
    opts: dict[int, int] = {}
    idle = getattr(socket, "TCP_KEEPIDLE", None) or getattr(socket, "TCP_KEEPALIVE", None)
    for name, value in (
        (idle, KEEPALIVE_IDLE_S),
        (getattr(socket, "TCP_KEEPINTVL", None), KEEPALIVE_INTERVAL_S),
        (getattr(socket, "TCP_KEEPCNT", None), KEEPALIVE_COUNT),
    ):
        if name is not None:
            opts[name] = value
    return opts


def _backoff() -> ExponentialWithJitterBackoff:
    return ExponentialWithJitterBackoff(base=BACKOFF_BASE_S, cap=BACKOFF_CAP_S)


def redis_options(
    *, blocking: bool = False, socket_timeout: float = SOCKET_TIMEOUT_S, asyncio: bool = False
) -> dict[str, Any]:
    """Keyword arguments for `Redis.from_url` (or `redis.asyncio.Redis.from_url` with
    `asyncio=True`; the async client needs its own Retry class)."""
    retry = AsyncRetry(_backoff(), RETRIES) if asyncio else Retry(_backoff(), RETRIES)
    opts: dict[str, Any] = {
        "health_check_interval": HEALTH_CHECK_INTERVAL_S,
        "socket_keepalive": True,
        "socket_keepalive_options": keepalive_options(),
        "socket_connect_timeout": CONNECT_TIMEOUT_S,
        "retry": retry,
        "retry_on_error": list(RETRY_ON),
    }
    if not blocking:
        opts["socket_timeout"] = socket_timeout
    return opts


def sync_redis(url: str, *, blocking: bool = False, **overrides: Any) -> Redis:
    """A resilient synchronous client (`blocking=True` for RQ workers: no read timeout)."""
    return Redis.from_url(url, **{**redis_options(blocking=blocking), **overrides})


def async_redis(url: str, *, blocking: bool = False, **overrides: Any) -> AsyncRedis:
    """A resilient asyncio client (`blocking=True` for pub/sub listeners)."""
    return AsyncRedis.from_url(
        url, **{**redis_options(blocking=blocking, asyncio=True), **overrides}
    )
