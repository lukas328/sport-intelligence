"""The court marked while the analysis runs: the worker reports the hall image early, points
marked on it before the court stage go to the running job, later ones replace it."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from handball_api.core.jobs import MemoryJobQueue

from .conftest import Api, setup_club
from .test_court_clicks import _lines
from .test_halls import PANORAMA, _court, _video
from .test_identity_sync import _finish, _tracks

pytestmark = pytest.mark.usefixtures("clean_db")


def _token(api: Api) -> dict[str, str]:
    return {"x-internal-token": api.app.state.settings.internal_token.get_secret_value()}


async def _report(api: Api, job: str, **body: Any) -> dict[str, Any]:
    r = await api.http.post(
        f"/internal/jobs/{job}", headers=_token(api), json={"status": "running", **body}
    )
    assert r.status_code == 200, r.text
    out: dict[str, Any] = r.json()
    return out


async def _running_with_hall(api: Api, ids: dict[str, Any]) -> tuple[str, str]:
    """A video whose first analysis runs and has shared its hall image (motion pass done)."""
    vid, job, _ = await _video(api, ids)
    stages = {"download": {"status": "done"}, "observe": {"status": "running"}}
    await _report(api, job, progress=0.1, stage="observe", stages=stages)
    await _report(
        api, job, progress=0.1, stage="observe", view={"camera": "moving", "panorama": PANORAMA}
    )
    return vid, job


async def test_the_hall_image_is_there_while_the_analysis_runs(
    make_api: Callable[[], Api],
) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    vid, _ = await _running_with_hall(api, ids)
    a = (await api.get(f"/v1/orgs/{org}/videos/{vid}/analysis")).json()
    assert a["status"] == "running"
    assert a["panorama"] == PANORAMA and a["camera"] == "moving"
    r = await api.post(
        f"/v1/orgs/{org}/videos/{vid}/calibration/clicks/check",
        json={"space": "panorama", "lines": _lines()},
    )
    assert r.status_code == 200, r.text


async def test_points_marked_before_the_court_stage_go_to_the_running_job(
    make_api: Callable[[], Api],
) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    jobs: MemoryJobQueue = api.app.state.jobs
    vid, job = await _running_with_hall(api, ids)
    queued = len(jobs.jobs)
    r = await api.post(
        f"/v1/orgs/{org}/videos/{vid}/calibration/clicks",
        json={"space": "panorama", "lines": _lines()},
    )
    assert r.status_code == 202, r.text
    assert r.json()["job_id"] == job and len(jobs.jobs) == queued  # no second run
    a = (await api.get(f"/v1/orgs/{org}/videos/{vid}/analysis")).json()
    assert a["status"] == "running" and a["calibration_state"] == "updating"

    # the worker reaches its court stage: the answer carries the points
    stages = {"observe": {"status": "done"}, "calibration": {"status": "running"}}
    answer = await _report(api, job, progress=0.75, stage="calibration", stages=stages)
    court = answer["court_points"]
    assert court["space"] == "panorama" and 4 <= len(court["points"]) <= 40

    await _finish(
        api,
        job,
        {"calibration": _court("user_correction"), "tracks": _tracks(), "panorama": PANORAMA},
    )
    a = (await api.get(f"/v1/orgs/{org}/videos/{vid}/analysis")).json()
    assert a["status"] == "ready" and a["calibration"]["source"] == "user_correction"
    assert a["calibration_state"] == "confirmed"
    assert len(jobs.jobs) == queued  # still the one run
    # later runs (reprocess) keep the clicked court
    r = await api.post(f"/v1/orgs/{org}/videos/{vid}/analysis")
    assert r.status_code in (200, 202), r.text
    assert jobs.jobs[-1][3]["calibration_points"] == court["points"]


async def test_a_run_that_did_not_take_the_points_is_followed_by_one_with_them(
    make_api: Callable[[], Api],
) -> None:
    """An older worker (or the classical path) never asks: its automatic court lands, and a run
    with the marked points follows on its stored observations."""
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    jobs: MemoryJobQueue = api.app.state.jobs
    vid, job = await _running_with_hall(api, ids)
    await api.post(
        f"/v1/orgs/{org}/videos/{vid}/calibration/clicks",
        json={"space": "panorama", "lines": _lines()},
    )
    queued = len(jobs.jobs)
    await _finish(
        api, job, {"calibration": _court("heuristic"), "tracks": _tracks(), "panorama": PANORAMA}
    )
    assert len(jobs.jobs) == queued + 1
    _, func, rerun, payload = jobs.jobs[-1]
    assert func == "handball_gpu_worker.analysis.run_analysis" and rerun != job
    assert payload["calibration_space"] == "panorama" and payload["calibration_points"]
    assert await _state(api, org, vid) == "updating"
    await _finish(
        api,
        rerun,
        {"calibration": _court("user_correction"), "tracks": _tracks(), "panorama": PANORAMA},
    )
    assert await _state(api, org, vid) == "confirmed"


async def test_points_marked_after_the_court_stage_replace_the_running_job(
    make_api: Callable[[], Api],
) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    jobs: MemoryJobQueue = api.app.state.jobs
    vid, job = await _running_with_hall(api, ids)
    stages = {"observe": {"status": "done"}, "calibration": {"status": "running"}}
    answer = await _report(api, job, progress=0.75, stage="calibration", stages=stages)
    assert answer["court_points"] is None
    r = await api.post(
        f"/v1/orgs/{org}/videos/{vid}/calibration/clicks",
        json={"space": "panorama", "lines": _lines()},
    )
    assert r.status_code == 202, r.text
    click_job = r.json()["job_id"]
    assert click_job != job and jobs.jobs[-1][2] == click_job
    assert jobs.jobs[-1][3]["calibration_points"]

    # the replaced run ends later with its automatic court: ignored
    await _finish(
        api, job, {"calibration": _court("heuristic"), "tracks": _tracks(), "panorama": PANORAMA}
    )
    a = (await api.get(f"/v1/orgs/{org}/videos/{vid}/analysis")).json()
    assert a["calibration"] is None and a["status"] == "running"
    assert a["calibration_state"] == "updating"
    await _finish(
        api,
        click_job,
        {"calibration": _court("user_correction"), "tracks": _tracks(), "panorama": PANORAMA},
    )
    a = (await api.get(f"/v1/orgs/{org}/videos/{vid}/analysis")).json()
    assert a["calibration"]["source"] == "user_correction" and a["status"] == "ready"


async def _state(api: Api, org: str, vid: str) -> str:
    a = (await api.get(f"/v1/orgs/{org}/videos/{vid}/analysis")).json()
    return str(a["calibration_state"])
