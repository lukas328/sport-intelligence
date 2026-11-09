"""Operations and measurement (addendum 01, 4.12)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import asyncpg
import httpx
import pytest

from handball_api.core.db import enable_system_access, open_session
from handball_api.core.jobs import MemoryJobQueue
from handball_api.services import monitoring
from handball_api.services.context import Ctx

from .conftest import Api, setup_club
from .test_identity_sync import _ingest
from .test_matches import new_match, upload

pytestmark = pytest.mark.usefixtures("clean_db")


def test_quality_alert() -> None:
    def week(i: int, corr: float, conf: float) -> dict[str, object]:
        return {
            "week": f"2026-W{i:02d}",
            "events": 100,
            "mean_confidence": conf,
            "correction_rate": corr,
        }

    steady = [week(i, 0.05, 0.8) for i in range(40, 45)]
    assert monitoring.quality_alert(steady) is None
    worse = [*steady, week(45, 0.2, 0.78)]
    assert monitoring.quality_alert(worse)["key"] == "ai_corrections"  # type: ignore[index]
    drop = [*steady, week(45, 0.06, 0.62)]
    assert monitoring.quality_alert(drop)["key"] == "ai_confidence"  # type: ignore[index]
    assert monitoring.quality_alert(steady[:2]) is None


async def test_metrics_quality_status_and_retention(
    make_api: Callable[[], Api], owner_conn: asyncpg.Connection
) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    m = await new_match(api, ids)
    vid = (await upload(api, ids, m["id"], b"v" * 100))["id"]
    jobs: MemoryJobQueue = api.app.state.jobs
    await _ingest(api, jobs.jobs[-1][2], jobs.jobs[-1][3]["prefix"])
    # an analysis that took 50 min and cost CHF 2.40 (over both budgets)
    now = datetime.now(UTC)
    await owner_conn.execute(
        "UPDATE processing_jobs SET status = 'succeeded', started_at = $1, finished_at = $2, "
        "cost_chf = 2.4 WHERE kind = 'analysis'",
        now - timedelta(minutes=55),
        now - timedelta(minutes=5),
    )
    # automatic events and corrections of them
    ev = f"/v1/orgs/{org}/matches/{m['id']}/events"
    for i in range(3):
        await api.post(
            ev, json={"type": "shot", "side": "own", "outcome": "goal", "t_ms": 1000 * i}
        )
    await owner_conn.execute("UPDATE events SET source = 'heuristic', confidence = 0.55")
    first = (await api.get(ev)).json()[0]
    await api.patch(f"/v1/orgs/{org}/events/{first['id']}", json={"outcome": "save"})

    async with open_session() as db:
        ctx = Ctx(
            db=db,
            settings=api.app.state.settings,
            email=api.app.state.email,
            storage=api.app.state.storage,
        )
        await enable_system_access(db, reason="test")
        metrics = await monitoring.ops_metrics(ctx)
        assert metrics["analysis_p95_min"] == 50.0 and metrics["cost_chf_per_match"] == 2.4
        keys = {a["key"] for a in await monitoring.alerts(ctx)}
        assert {"analysis_duration", "cost_per_match"} <= keys
        weeks = await monitoring.quality_weeks(ctx)
        assert weeks[-1]["events"] == 3 and weeks[-1]["correction_rate"] == round(1 / 3, 3)
        assert weeks[-1]["low_confidence_share"] == 1.0

        sent: list[httpx.Request] = []

        async def handler(request: httpx.Request) -> httpx.Response:
            sent.append(request)
            return httpx.Response(200)

        ctx.settings.status_page_push_url = "https://status.example.test/api/components"
        try:
            report = await monitoring.push_status(
                ctx, httpx.AsyncClient(transport=httpx.MockTransport(handler))
            )
        finally:
            ctx.settings.status_page_push_url = None
        assert sent and {c["component"] for c in report} >= {"database"}

        # storage policy: notice 7 days before, then the original goes, compressed versions stay
        later = now + timedelta(days=84)
        assert await monitoring.retention(ctx, later) == {"notified": 1, "purged": 0}
        assert await monitoring.retention(ctx, later + timedelta(days=7)) == {
            "notified": 0,
            "purged": 1,
        }
        await db.commit()
    notes = (await api.get(f"/v1/orgs/{org}/me/notifications")).json()["items"]
    assert any(n["kind"] == "originals_purge" for n in notes)
    row = await owner_conn.fetchrow(
        "SELECT original_purged_at, proxy_key FROM video_assets WHERE id = $1::uuid", vid
    )
    assert row["original_purged_at"] is not None and row["proxy_key"]
    token = {"x-internal-token": api.app.state.settings.internal_token.get_secret_value()}
    stats = (await api.http.get("/internal/stats", headers=token)).json()
    assert "alerts" in stats and stats["metrics"]["analyses_7d"] == 1


async def test_abandoned_uploads_are_aborted_and_marked_failed(
    make_api: Callable[[], Api], owner_conn: asyncpg.Connection
) -> None:
    api = make_api()
    ids = await setup_club(api)
    m = await new_match(api, ids)
    r = await api.post(
        f"/v1/orgs/{ids['org']}/matches/{m['id']}/videos",
        json={
            "filename": "spiel.mp4",
            "size_bytes": 100,
            "content_type": "video/mp4",
            "role": "main",
        },
    )
    vid = r.json()["video"]["id"]
    async with open_session() as db:
        ctx = Ctx(
            db=db,
            settings=api.app.state.settings,
            email=api.app.state.email,
            storage=api.app.state.storage,
        )
        await enable_system_access(db, reason="test")
        # fresh uploads stay, three days without progress end them
        assert await monitoring.abandoned_uploads(ctx) == 0
        assert await monitoring.abandoned_uploads(ctx, datetime.now(UTC) + timedelta(days=4)) == 1
        await db.commit()
    row = await owner_conn.fetchrow(
        "SELECT status, error, upload_id FROM video_assets WHERE id = $1::uuid", vid
    )
    assert (
        row["status"] == "failed"
        and row["error"] == "upload abandoned"
        and row["upload_id"] is None
    )
