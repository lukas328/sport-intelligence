from __future__ import annotations

import httpx

from handball_worker.ticks import scouting_tick


def test_scouting_tick_posts_and_survives_errors() -> None:
    seen: list[httpx.Request] = []

    def ok(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path.endswith("dunning"):
            return httpx.Response(200, json={"reminders": 0, "dunning": 0, "lapsed": 0})
        if request.url.path.endswith("onboarding/run"):
            return httpx.Response(200, json={"sent": 1})
        if request.url.path.endswith("ops/tick"):
            return httpx.Response(
                200, json={"status": [], "retention": {"notified": 0, "purged": 0}}
            )
        return httpx.Response(200, json={"created": 2})

    assert scouting_tick(httpx.Client(transport=httpx.MockTransport(ok)), reschedule=False) == 2
    assert [r.url.path for r in seen] == [
        "/internal/scouting/due",
        "/internal/billing/dunning",
        "/internal/onboarding/run",
        "/internal/ops/tick",
        "/internal/official/sync",
    ]
    assert seen[0].headers["x-internal-token"]

    def down(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    assert scouting_tick(httpx.Client(transport=httpx.MockTransport(down)), reschedule=False) == 0


def test_tick_is_scheduled_once_and_comes_back_after_a_lost_schedule() -> None:
    """The hourly tick lives only in Redis. ensure_scheduled runs at worker start and on RQ's
    maintenance schedule; it must add the tick when it is gone (Redis restart, a leftover
    finished job hash) and leave a pending one alone."""
    import fakeredis
    from rq import Queue

    from handball_worker.ticks import TICK_JOB_ID, ensure_scheduled, schedule

    conn = fakeredis.FakeRedis()
    q = Queue("default", connection=conn)
    ensure_scheduled(conn)
    assert TICK_JOB_ID in q.scheduled_job_registry
    first = q.scheduled_job_registry.get_scheduled_time(TICK_JOB_ID)
    ensure_scheduled(conn)  # pending: untouched
    assert q.scheduled_job_registry.get_scheduled_time(TICK_JOB_ID) == first

    # the job hash survives, the schedule does not (the old check looked at the hash only)
    q.scheduled_job_registry.remove(TICK_JOB_ID)
    assert q.fetch_job(TICK_JOB_ID) is not None
    ensure_scheduled(conn)
    assert TICK_JOB_ID in q.scheduled_job_registry

    conn.flushall()  # Redis restarted without persistence
    ensure_scheduled(conn)
    assert TICK_JOB_ID in q.scheduled_job_registry

    # the job hash must outlive the hour until the next tick (RQ expires finished jobs)
    schedule(conn)
    job = q.fetch_job(TICK_JOB_ID)
    assert job is not None and job.result_ttl is not None and job.result_ttl > 3600
