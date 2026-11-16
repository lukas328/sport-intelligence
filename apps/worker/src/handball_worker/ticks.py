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

from handball_worker.config import WorkerSettings

log = structlog.get_logger("worker.ticks")
TICK_JOB_ID = "tick-scouting"
EVERY = timedelta(hours=1)
# the job watchdog: a job whose worker went silent is restarted (services/progress in the API)
WATCHDOG_JOB_ID = "tick-watchdog"
WATCHDOG_EVERY = timedelta(minutes=10)


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
            schedule(Redis.from_url(settings.redis_url))
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
            Queue("default", connection=Redis.from_url(settings.redis_url)).enqueue_in(
                WATCHDOG_EVERY, watchdog_tick, job_id=WATCHDOG_JOB_ID
            )
    return result


def schedule(conn: Redis, delay: timedelta = EVERY) -> None:
    """Idempotent: one pending tick at a time (fixed job id)."""
    q = Queue("default", connection=conn)
    q.enqueue_in(delay, scouting_tick, job_id=TICK_JOB_ID)


def ensure_scheduled(conn: Redis) -> None:
    q = Queue("default", connection=conn)
    if q.fetch_job(TICK_JOB_ID) is None:
        schedule(conn, timedelta(minutes=1))
    if q.fetch_job(WATCHDOG_JOB_ID) is None:
        q.enqueue_in(timedelta(minutes=2), watchdog_tick, job_id=WATCHDOG_JOB_ID)
