"""Periodic work driven by the worker: an hourly tick that re-schedules itself (RQ scheduler).

Today: preparation reports 72 h before matches (4.6), invoice dunning (4.10) and the sync with
the official league data (docs/plans/federation-onboarding.md). The API
decides what is due; the worker only knocks.
"""

from __future__ import annotations

from datetime import timedelta

import httpx
import structlog
from redis import Redis
from rq import Queue

from handball_jobkit.redisconn import sync_redis
from handball_worker.config import WorkerSettings

log = structlog.get_logger("worker.ticks")
TICK_JOB_ID = "tick-scouting"
EVERY = timedelta(hours=1)
# The tick re-schedules itself under its own job id while it runs; when it then finishes, RQ
# saves it as finished and lets the job hash expire after `result_ttl` (default 500 s). That hash
# is the one the scheduler needs an hour later, so it has to outlive the gap between two ticks.
TICK_RESULT_TTL_S = int(3 * EVERY.total_seconds())
# the job watchdog: a job whose worker went silent is restarted (services/progress in the API)
WATCHDOG_JOB_ID = "tick-watchdog"
WATCHDOG_EVERY = timedelta(minutes=10)
WATCHDOG_RESULT_TTL_S = int(3 * WATCHDOG_EVERY.total_seconds())


def scouting_tick(client: httpx.Client | None = None, reschedule: bool = True) -> int:
    settings = WorkerSettings()
    created = 0
    try:
        http = client or httpx.Client(timeout=60)
        base = settings.api_internal_url.rstrip("/")
        headers = {"x-internal-token": settings.internal_token}
        r = http.post(f"{base}/internal/scouting/due", headers=headers)
        r.raise_for_status()
        created = int(r.json().get("created", 0))
        log.info("scouting_tick", created=created)
        # invoice reminders and final notices (addendum 01, 4.10), idempotent
        d = http.post(f"{base}/internal/billing/dunning", headers=headers)
        d.raise_for_status()
        log.info("dunning_tick", **d.json())
        o = http.post(f"{base}/internal/onboarding/run", headers=headers)
        o.raise_for_status()
        log.info("onboarding_tick", **o.json())
        ops = http.post(f"{base}/internal/ops/tick", headers=headers)
        ops.raise_for_status()
        log.info("ops_tick", retention=ops.json().get("retention"))
        # official league data: each linked team once a day, reports after the games
        off = http.post(f"{base}/internal/official/sync", headers=headers)
        off.raise_for_status()
        log.info("official_sync_tick", **off.json())
    except httpx.HTTPError as exc:
        log.warning("scouting_tick_failed", error=str(exc))
    finally:
        if reschedule:
            schedule(sync_redis(settings.redis_url))
    return created


def watchdog_tick(client: httpx.Client | None = None, reschedule: bool = True) -> dict[str, int]:
    """Every ten minutes: the API restarts processing jobs that stopped reporting."""
    settings = WorkerSettings()
    result: dict[str, int] = {}
    try:
        http = client or httpx.Client(timeout=60)
        base = settings.api_internal_url.rstrip("/")
        r = http.post(
            f"{base}/internal/watchdog", headers={"x-internal-token": settings.internal_token}
        )
        r.raise_for_status()
        result = r.json()
        if result.get("restarted") or result.get("failed"):
            log.warning("watchdog_tick", **result)
    except httpx.HTTPError as exc:
        log.warning("watchdog_tick_failed", error=str(exc))
    finally:
        if reschedule:
            schedule_watchdog(sync_redis(settings.redis_url))
    return result


def schedule_watchdog(conn: Redis, delay: timedelta = WATCHDOG_EVERY) -> None:
    """Idempotent like the tick: fixed job id, and its hash outlives the gap to the next run."""
    Queue("default", connection=conn).enqueue_in(
        delay, watchdog_tick, job_id=WATCHDOG_JOB_ID, result_ttl=WATCHDOG_RESULT_TTL_S
    )


def schedule(conn: Redis, delay: timedelta = EVERY) -> None:
    """Idempotent: one pending tick at a time (fixed job id)."""
    q = Queue("default", connection=conn)
    q.enqueue_in(delay, scouting_tick, job_id=TICK_JOB_ID, result_ttl=TICK_RESULT_TTL_S)


def ensure_scheduled(conn: Redis) -> None:
    """Schedule the tick unless it is waiting for its time or in the queue. Runs at worker start
    and on RQ's maintenance schedule: after a Redis restart (no persistence) or a tick that
    could not re-schedule itself, the chain starts again within minutes. A leftover job hash
    (finished or failed) does not count as scheduled."""
    q = Queue("default", connection=conn)
    waiting = set(q.get_job_ids())
    if TICK_JOB_ID not in q.scheduled_job_registry and TICK_JOB_ID not in waiting:
        schedule(conn, timedelta(minutes=1))
    if WATCHDOG_JOB_ID not in q.scheduled_job_registry and WATCHDOG_JOB_ID not in waiting:
        schedule_watchdog(conn, timedelta(minutes=2))
