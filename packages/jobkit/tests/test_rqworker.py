"""The RQ worker keeps taking jobs through Redis restarts and dropped connections."""

from __future__ import annotations

from typing import Any

import fakeredis
import pytest
from redis import Redis
from redis.exceptions import ConnectionError as RedisConnectionError
from rq import Queue

from handball_jobkit import rqworker
from handball_jobkit.rqworker import ResilientWorker, run_worker


class Script:
    """Stands in for the worker class: each run does what the script says."""

    def __init__(self, outcomes: list[str]) -> None:
        self.outcomes = outcomes
        self.runs: list[dict[str, Any]] = []

    def __call__(self, queues: list[Queue], **kwargs: Any) -> Any:
        script = self

        class Fake:
            shutdown_requested = False

            def work(self, with_scheduler: bool = False) -> bool:
                script.runs.append({"queues": [q.name for q in queues], **kwargs})
                outcome = script.outcomes.pop(0)
                if outcome == "redis-down":
                    raise RedisConnectionError("Error 111 connecting to hb-stg-redis:6379.")
                if outcome == "shutdown":
                    self.shutdown_requested = True
                return False  # "quit" after an error RQ logged itself

        return Fake()


def test_worker_restarts_after_redis_failures_until_shutdown() -> None:
    script = Script(["quit", "redis-down", "redis-down", "shutdown"])
    slept: list[float] = []
    run_worker(
        fakeredis.FakeRedis(),
        ["pipeline", "default"],
        sleep=slept.append,
        worker_class=script,  # type: ignore[arg-type]
    )
    assert len(script.runs) == 4
    assert script.runs[0]["queues"] == ["pipeline", "default"]
    assert script.runs[0]["worker_ttl"] == rqworker.WORKER_TTL_S
    assert slept == [1.0, 2.0, 4.0]  # exponential backoff between restarts


def test_backoff_is_capped() -> None:
    script = Script(["redis-down"] * 10 + ["shutdown"])
    slept: list[float] = []
    run_worker(
        fakeredis.FakeRedis(),
        ["gpu"],
        sleep=slept.append,
        worker_class=script,  # type: ignore[arg-type]
    )
    assert max(slept) == rqworker.RESTART_BACKOFF_S[1]


def test_dequeue_wait_stays_below_the_proxy_idle_timeout() -> None:
    """RQ blocks in BLPOP for worker_ttl - 15 s. The proxy in front of Redis drops connections
    that are silent for a few minutes; the wait must stay well below that."""
    w = ResilientWorker(
        [Queue("gpu", connection=fakeredis.FakeRedis())], worker_ttl=rqworker.WORKER_TTL_S
    )
    assert w.dequeue_timeout <= 120
    assert w.connection_timeout > w.dequeue_timeout  # RQ's read timeout covers the BLPOP


def test_maintenance_hooks_run_and_redis_errors_do_not_stop_the_worker() -> None:
    conn = fakeredis.FakeRedis()
    seen: list[Redis] = []

    def ok(c: Redis) -> None:
        seen.append(c)

    def broken(_c: Redis) -> None:
        raise RedisConnectionError("Connection closed by server.")

    w = ResilientWorker(
        [Queue("default", connection=conn)], connection=conn, maintenance=[broken, ok]
    )
    w.run_maintenance_tasks()
    assert seen == [conn]


def test_shutdown_signal_is_remembered(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = fakeredis.FakeRedis()
    w = ResilientWorker([Queue("default", connection=conn)], connection=conn)
    monkeypatch.setattr(w, "_shutdown", lambda: None)
    monkeypatch.setattr("signal.signal", lambda *_a: None)
    w.request_stop(15, None)
    assert w.shutdown_requested


def test_a_killed_work_horse_is_reported_to_the_api(monkeypatch: pytest.MonkeyPatch) -> None:
    from handball_jobkit import rqworker
    from handball_jobkit.reporter import Reporter

    sent: list[tuple[str, dict[str, Any]]] = []

    def send(
        self: Reporter, body: dict[str, Any], force: bool = False, terminal: bool = False
    ) -> None:
        sent.append((self.url, body))

    monkeypatch.setattr(Reporter, "_send", send)
    job = "3f2b8c1e-0000-4000-8000-000000000001"
    assert rqworker.report_lost(job, 9) is True  # waitpid status of SIGKILL
    url, body = sent[0]
    assert url.endswith(f"/internal/jobs/{job}")
    assert body["status"] == "failed"
    assert body["error"] == "worker lost: work horse killed by signal 9 (likely out of memory)"
    assert rqworker.report_lost("tick-watchdog", 9) is False  # not a job of the API
    assert len(sent) == 1
    assert rqworker.lost_error(256).startswith("worker lost: work horse ended unexpectedly")


def test_burst_works_the_queue_once_and_returns() -> None:
    """The GPU job execution: take what is waiting, then end (one worker, no restart loop)."""
    runs: list[dict[str, Any]] = []

    class Burst:
        shutdown_requested = False

        def __init__(self, queues: list[Queue], **kwargs: Any) -> None:
            self.queues = [q.name for q in queues]

        def work(self, burst: bool = False, with_scheduler: bool = False) -> bool:
            runs.append({"queues": self.queues, "burst": burst})
            return False

    slept: list[float] = []
    conn = fakeredis.FakeRedis()
    run_worker(conn, ["gpu"], burst=True, sleep=slept.append, worker_class=Burst)  # type: ignore[arg-type]
    assert runs == [{"queues": ["gpu"], "burst": True}]
    assert slept == []
