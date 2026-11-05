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


def schedule(conn: Redis, delay: timedelta = EVERY) -> None:
    """Idempotent: one pending tick at a time (fixed job id)."""
    q = Queue("default", connection=conn)
    q.enqueue_in(delay, scouting_tick, job_id=TICK_JOB_ID)


def ensure_scheduled(conn: Redis) -> None:
    q = Queue("default", connection=conn)
    if q.fetch_job(TICK_JOB_ID) is None:
        schedule(conn, timedelta(minutes=1))
