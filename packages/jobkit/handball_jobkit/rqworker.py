"""Run an RQ worker that keeps taking jobs through Redis restarts and dropped connections.

RQ's own loop already waits and retries when the dequeue (BLPOP) hits a connection error. Any
other Redis error in the loop (heartbeat, maintenance, job bookkeeping) or a Redis timeout makes
`Worker.work()` log "quitting" and return, and the process would just end. `run_worker` starts
a fresh worker instead (new name, so the old registration cannot clash), with backoff, until a
shutdown signal asks it to stop.

The dequeue waits at most `worker_ttl - 15` seconds per BLPOP. With RQ's default of 420 s the
connection sits silent for almost seven minutes, longer than the idle timeout of the proxy in
front of Redis, which then cuts it ("could not connect to Redis instance: Connection closed by
server" every few minutes). A shorter `worker_ttl` keeps every BLPOP well inside that timeout;
the price is one cheap heartbeat per minute or so.

A work horse the system kills (out of memory: "Work-horse terminated unexpectedly; waitpid
returned 9") cannot report its end, and the API would show the job running until its watchdog
noticed the silence (30 to 40 minutes). `ResilientWorker.handle_work_horse_killed` reports it at
once as failed with WORKER_LOST; the API restarts the job once and ends it the second time
(services/progress.restart_or_fail).
"""

from __future__ import annotations

import os
import time
import uuid
from collections.abc import Callable, Sequence
from typing import Any

import structlog
from redis import Redis
from redis.exceptions import RedisError
from rq import Queue, Worker

from handball_jobkit.reporter import Reporter, ReportError
from handball_jobkit.settings import JobSettings

log = structlog.get_logger("worker.rq")

WORKER_TTL_S = 90  # BLPOP waits 75 s, read timeout 85 s (RQ derives both from the TTL)
RESTART_BACKOFF_S = (1.0, 60.0)  # first wait, cap
HEALTHY_RUN_S = 300.0  # a worker that ran this long resets the backoff
# the API matches this prefix (services/progress.WORKER_LOST): keep both the same
WORKER_LOST = "worker lost"


def lost_error(ret_val: int) -> str:
    """The error a killed work horse is reported with (signal 9: most likely out of memory)."""
    if os.WIFSIGNALED(ret_val):
        sig = os.WTERMSIG(ret_val)
        why = " (likely out of memory)" if sig == 9 else ""
        return f"{WORKER_LOST}: work horse killed by signal {sig}{why}"
    return f"{WORKER_LOST}: work horse ended unexpectedly (status {ret_val})"


def report_lost(job_id: str, ret_val: int, settings: JobSettings | None = None) -> bool:
    """Tell the API that the job's work horse is gone; False for jobs the API does not track
    (not a job id of the API, e.g. the ticks) or when the API cannot be reached."""
    try:
        uuid.UUID(job_id)
    except ValueError:
        return False
    s = settings or JobSettings()
    rep = Reporter(s.api_internal_url, s.internal_token, job_id, {"lost": 1.0}, heartbeat_s=None)
    try:
        rep._send(
            {"status": "failed", "progress": 0.0, "error": lost_error(ret_val)}, terminal=True
        )
    except ReportError as exc:
        log.warning("worker_lost_report_failed", job=job_id, error=str(exc))
        return False
    finally:
        rep.client.close()
    log.warning("worker_lost_reported", job=job_id, status=ret_val)
    return True


class ResilientWorker(Worker):
    """Remembers a shutdown signal (RQ handles idle and busy shutdowns differently and only
    marks the busy case) and runs extra maintenance hooks on RQ's maintenance schedule (at
    start and every ten minutes)."""

    def __init__(
        self,
        *args: Any,
        maintenance: Sequence[Callable[[Redis], None]] = (),
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.shutdown_requested = False
        self._maintenance = tuple(maintenance)

    def request_stop(self, signum: Any, frame: Any) -> None:
        self.shutdown_requested = True
        super().request_stop(signum, frame)  # type: ignore[no-untyped-call]

    def handle_work_horse_killed(self, job: Any, retpid: int, ret_val: int, rusage: Any) -> None:
        super().handle_work_horse_killed(job, retpid, ret_val, rusage)  # type: ignore[no-untyped-call]
        try:
            report_lost(str(job.id), ret_val)
        except Exception as exc:  # the worker must go on with the next job
            log.warning("worker_lost_report_failed", job=str(job.id), error=str(exc))

    def run_maintenance_tasks(self) -> None:
        super().run_maintenance_tasks()  # type: ignore[no-untyped-call]
        for hook in self._maintenance:
            try:
                hook(self.connection)
            except RedisError as exc:
                log.warning("worker_maintenance_failed", hook=hook.__name__, error=str(exc))


def run_worker(
    conn: Redis,
    queue_names: Sequence[str],
    *,
    with_scheduler: bool = False,
    maintenance: Sequence[Callable[[Redis], None]] = (),
    sleep: Callable[[float], None] = time.sleep,
    worker_class: type[ResilientWorker] = ResilientWorker,
) -> None:
    """Work `queue_names` until a shutdown signal; restart the worker after Redis failures."""
    first, cap = RESTART_BACKOFF_S
    delay = first
    while True:
        started = time.monotonic()
        worker: ResilientWorker | None = None
        try:
            worker = worker_class(
                [Queue(name, connection=conn) for name in queue_names],
                connection=conn,
                worker_ttl=WORKER_TTL_S,
                maintenance=maintenance,
            )
            worker.work(with_scheduler=with_scheduler)
            if worker.shutdown_requested:
                return
            log.warning("worker_stopped_unexpectedly", queues=list(queue_names))
        except RedisError as exc:
            # registration or teardown failed: Redis is down or restarting
            log.warning("worker_redis_unavailable", queues=list(queue_names), error=str(exc))
        if worker is not None and worker.shutdown_requested:
            return
        if time.monotonic() - started >= HEALTHY_RUN_S:
            delay = first
        log.info("worker_restart", in_s=round(delay, 1))
        try:
            sleep(delay)
        except Exception:
            # RQ's signal handlers stay installed after work() returns: a shutdown signal
            # during the wait lands in the old worker and may raise StopRequested here
            if worker is not None and worker.shutdown_requested:
                return
            raise
        delay = min(delay * 2, cap)
