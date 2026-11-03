"""Operator backoffice (M8)."""

from __future__ import annotations

from collections.abc import Callable, Iterator

import pytest
from fastapi import FastAPI

from handball_api.core.jobs import MemoryJobQueue

from .conftest import Api, setup_club
from .test_matches import new_match, upload

pytestmark = pytest.mark.usefixtures("clean_db")


@pytest.fixture
def operators(db_app: FastAPI) -> Iterator[None]:
    s = db_app.state.settings
    old = list(s.operator_emails)
    s.operator_emails = ["ops@handball-ops.ch"]
    yield
    s.operator_emails = old


async def test_backoffice(make_api: Callable[[], Api], operators: None) -> None:
    coach = make_api()
    ids = await setup_club(coach)
    m = await new_match(coach, ids)
    await upload(coach, ids, m["id"], b"v" * 100)
    jobs: MemoryJobQueue = coach.app.state.jobs
    token = {"x-internal-token": coach.app.state.settings.internal_token.get_secret_value()}
    failed_id = jobs.jobs[-1][2]
    await coach.http.post(
        f"/internal/jobs/{failed_id}",
        headers=token,
        json={"status": "failed", "progress": 0.1, "error": "ffmpeg: broken file"},
    )
    # invisible to everybody else
    assert (await coach.get("/v1/ops/me")).status_code == 404
    assert (await make_api().get("/v1/ops/overview")).status_code == 401

    op = make_api()
    assert (await op.register("ops@handball-ops.ch")).status_code == 201
    assert (await op.get("/v1/ops/me")).json() == {"operator": True}
    by_domain = make_api()
    await by_domain.register("lea@ops-domain.ch")
    assert (await by_domain.get("/v1/ops/me")).status_code == 404
    op.app.state.settings.operator_emails = ["ops@handball-ops.ch", "@ops-domain.ch"]
    assert (await by_domain.get("/v1/ops/me")).status_code == 200
    ov = (await op.get("/v1/ops/overview")).json()
    assert ov["organizations"] >= 1 and ov["matches"] == 1 and ov["videos"] == 1
    assert ov["failed_jobs"][0]["error"] == "ffmpeg: broken file"
    assert ov["failed_jobs"][0]["organization"] == "HC Test"
    assert {"kind": "ingest", "status": "failed", "count": 1} in ov["jobs_24h"]

    orgs = (await op.get("/v1/ops/organizations", params={"q": "test"})).json()
    assert [o["name"] for o in orgs] == ["HC Test"]
    assert orgs[0]["matches"] == 1 and orgs[0]["storage_bytes"] == 100

    r = await op.post(
        f"/v1/ops/organizations/{ids['org']}/trial", json={"plan": "club", "days": 14}
    )
    assert r.status_code == 200 and r.json()["plan"] == "club"
    billing = (await coach.get(f"/v1/orgs/{ids['org']}/billing")).json()
    assert (billing["plan"], billing["effective_plan"]) == ("club", "club")

    failed = (await op.get("/v1/ops/jobs/failed")).json()
    r = await op.post(f"/v1/ops/jobs/{failed[0]['id']}/retry")
    assert r.status_code == 200 and r.json()["kind"] == "ingest"
    assert jobs.jobs[-1][1] == "handball_worker.ingest.run_ingest"
    assert (await op.post(f"/v1/ops/jobs/{failed[0]['id']}/retry")).status_code == 409
    ok_job = r.json()["job_id"]
    assert (await op.post(f"/v1/ops/jobs/{ok_job}/retry")).status_code == 409
