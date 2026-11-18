"""The court from clicked lines (services/court_clicks): check, submit, carried to the hall."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np
import pytest

from handball_api.core.jobs import MemoryJobQueue
from handball_court import clicks

from .conftest import Api, setup_club
from .test_halls import PANORAMA, _court, _video
from .test_identity_sync import _finish, _tracks

pytestmark = pytest.mark.usefixtures("clean_db")

# court -> hall image of a camera beside the near sideline, the left half in view
H = np.array([[60.0, 30.0, 300.0], [-3.0, -21.0, 840.0], [0.004, 0.035, 1.0]])


def _on(name: str, ts: list[float]) -> list[list[float]]:
    c = clicks._DENSE[name]
    pts = clicks._project(H, c[[int(t * (len(c) - 1)) for t in ts]])
    return [[round(float(x), 2), round(float(y), 2)] for x, y in pts]


def _lines() -> dict[str, list[list[float]]]:
    return {
        "side_near": _on("side_near", [0.05, 0.15, 0.3]),
        "side_far": _on("side_far", [0.05, 0.2, 0.35]),
        "goal_left": _on("goal_left", [0.3, 0.7]),
        "six_left": _on("six_left", [0.2, 0.5, 0.8]),
    }


async def _needs_court(api: Api, ids: dict[str, Any], **match: Any) -> str:
    """A video whose automatic court failed: the hall image is there to click on."""
    vid, job, _ = await _video(api, ids, **match)
    await _finish(
        api,
        job,
        {"needs_calibration": True, "calibration": None, "tracks": [], "panorama": PANORAMA},
    )
    return vid


async def test_the_court_model_lists_the_clickable_lines(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    r = await api.get(f"/v1/orgs/{ids['org']}/calibration/court-model")
    assert r.status_code == 200, r.text
    model = r.json()
    assert set(model["lines"]) == set(clicks.LINES)
    assert model["lines"]["centre"] == {"kind": "line", "court": [[20.0, 0.0], [20.0, 20.0]]}
    assert model["lines"]["nine_right"]["kind"] == "arc"
    assert model["points"]["corner_tl"] == list(clicks.KEYPOINTS["corner_tl"])


async def test_checking_clicks_gives_the_court_and_stores_nothing(
    make_api: Callable[[], Api],
) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    jobs: MemoryJobQueue = api.app.state.jobs
    vid, job, _ = await _video(api, ids)
    url = f"/v1/orgs/{org}/videos/{vid}/calibration/clicks/check"
    # before the analysis there is no hall image to click on
    r = await api.post(url, json={"lines": _lines()})
    assert r.status_code == 409 and r.json()["type"].endswith(":no-hall-image")
    await _finish(
        api,
        job,
        {"needs_calibration": True, "calibration": None, "tracks": [], "panorama": PANORAMA},
    )
    queued = len(jobs.jobs)

    r = await api.post(url, json={"space": "panorama", "lines": _lines()})
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["image_size"] == [PANORAMA["width"], PANORAMA["height"]]
    assert out["residual_px"]["median"] < 1.0 and out["dropped"] == []
    grid = np.array([(x, y) for x in range(0, 13, 2) for y in range(0, 21, 4)], float)
    got = clicks._project(np.array(out["homography"]), grid)
    assert np.abs(got - clicks._project(H, grid)).max() < 2.0
    assert len(jobs.jobs) == queued  # no analysis started
    a = (await api.get(f"/v1/orgs/{org}/videos/{vid}/analysis")).json()
    assert a["court_clicks"] is None and a["needs_calibration"] is True


@pytest.mark.parametrize(
    ("body", "code"),
    [
        ({"lines": {"side_near": [[10, 10], [20, 12]]}}, "clicks-too-few"),
        ({"points": {"middle_of_nowhere": [1, 1]}}, "clicks-unknown"),
        (
            {  # the 9 m clicks put on the 6 m line and the other way round
                "lines": {
                    **{k: v for k, v in _lines().items() if k != "six_left"},
                    "nine_left": _on("six_left", [0.2, 0.4, 0.6, 0.8]),
                    "six_left": _on("nine_left", [0.2, 0.4, 0.6, 0.8]),
                }
            },
            "clicks-disagree",
        ),
    ],
    ids=["too-few", "unknown", "disagree"],
)
async def test_clicks_that_give_no_court_are_refused_with_a_code(
    make_api: Callable[[], Api], body: dict[str, Any], code: str
) -> None:
    api = make_api()
    ids = await setup_club(api)
    vid = await _needs_court(api, ids)
    for path in ("clicks/check", "clicks"):
        r = await api.post(f"/v1/orgs/{ids['org']}/videos/{vid}/calibration/{path}", json=body)
        assert r.status_code == 422, r.text
        assert r.json()["type"].endswith(":" + code)


async def test_the_clicked_court_reruns_the_analysis_and_serves_the_hall(
    make_api: Callable[[], Api],
) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    jobs: MemoryJobQueue = api.app.state.jobs
    first = await _needs_court(api, ids, venue="Sporthalle Moosgarten")
    lines = _lines()
    near = _on("side_near", [0.22])[0]
    stray = [near[0], near[1] - 30.0]  # snapped to a neighbouring line: left out
    lines["side_near"].append(stray)
    r = await api.post(
        f"/v1/orgs/{org}/videos/{first}/calibration/clicks",
        json={"space": "panorama", "lines": lines},
    )
    assert r.status_code == 202, r.text
    out = r.json()
    assert out["dropped"] == [{"kind": "line", "name": "side_near", "index": 3}]
    _, func, job, payload = jobs.jobs[-1]
    assert func == "handball_gpu_worker.analysis.run_analysis" and job == out["job_id"]
    assert payload["calibration_space"] == "panorama"
    pairs = payload["calibration_points"]
    assert 4 <= len(pairs) <= 40
    # the pairs carry the clicked court: each image point is its court point through it
    court = np.array([p["court"] for p in pairs])
    image = np.array([p["image"] for p in pairs])
    assert np.abs(clicks._project(np.array(out["homography"]), court) - image).max() < 0.1
    assert np.abs(clicks._project(H, court) - image).max() < 3.0
    # the dropped click is not among the pairs
    assert not any(np.allclose(p["image"], stray, atol=1) for p in pairs)

    await _finish(
        api,
        job,
        {"calibration": _court("user_correction"), "tracks": _tracks(), "panorama": PANORAMA},
    )
    a = (await api.get(f"/v1/orgs/{org}/videos/{first}/analysis")).json()
    assert a["calibration"]["source"] == "user_correction" and not a["needs_calibration"]
    assert a["court_clicks"]["lines"]["six_left"] == lines["six_left"]
    assert a["court_clicks"]["space"] == "panorama"

    # the next game in the same hall gets this court to carry over
    _, _, payload2 = await _video(
        api, ids, venue="Sporthalle Moosgarten", kickoff_at="2026-11-14T18:00:00+01:00"
    )
    assert [ref["video_id"] for ref in payload2["hall_references"]] == [first]


async def _state(api: Api, org: str, vid: str) -> str:
    a = (await api.get(f"/v1/orgs/{org}/videos/{vid}/analysis")).json()
    return str(a["calibration_state"])


async def test_calibration_state_follows_the_court_from_missing_to_confirmed(
    make_api: Callable[[], Api],
) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    jobs: MemoryJobQueue = api.app.state.jobs
    vid = await _needs_court(api, ids)
    assert await _state(api, org, vid) == "missing"
    r = await api.post(
        f"/v1/orgs/{org}/videos/{vid}/calibration/clicks",
        json={"space": "panorama", "lines": _lines()},
    )
    assert r.status_code == 202, r.text
    assert await _state(api, org, vid) == "updating"
    await _finish(
        api,
        jobs.jobs[-1][2],
        {"calibration": _court("user_correction"), "tracks": _tracks(), "panorama": PANORAMA},
    )
    assert await _state(api, org, vid) == "confirmed"


async def test_a_failed_run_after_clicks_is_not_updating_forever(
    make_api: Callable[[], Api],
) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    jobs: MemoryJobQueue = api.app.state.jobs
    vid = await _needs_court(api, ids)
    await api.post(
        f"/v1/orgs/{org}/videos/{vid}/calibration/clicks",
        json={"space": "panorama", "lines": _lines()},
    )
    token = {"x-internal-token": api.app.state.settings.internal_token.get_secret_value()}
    r = await api.http.post(
        f"/internal/jobs/{jobs.jobs[-1][2]}",
        headers=token,
        json={"status": "failed", "progress": 1, "error": "timeout"},
    )
    assert r.status_code == 200, r.text
    assert await _state(api, org, vid) == "missing"


async def test_the_automatic_court_is_a_suggestion_until_confirmed(
    make_api: Callable[[], Api],
) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    vid, job, _ = await _video(api, ids)
    info = {"goal_score": 0.6, "line_score": 1.3, "floor_fit": 0.5}
    await _finish(
        api,
        job,
        {
            "calibration": _court("heuristic"),
            "calibration_info": info,
            "tracks": _tracks(),
            "panorama": PANORAMA,
        },
    )
    assert await _state(api, org, vid) == "suggested"
    r = await api.post(f"/v1/orgs/{org}/videos/{vid}/calibration/confirm")
    assert r.status_code == 200, r.text
    assert await _state(api, org, vid) == "confirmed"


@pytest.mark.parametrize(("floor", "state"), [(140, "confirmed"), (20, "suggested")])
async def test_a_court_from_the_hall_is_confirmed_only_with_a_sure_match(
    make_api: Callable[[], Api], floor: int, state: str
) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    first, job, _ = await _video(api, ids, venue="Sporthalle Moosgarten")
    await _finish(
        api,
        job,
        {"calibration": _court("user_correction"), "tracks": _tracks(), "panorama": PANORAMA},
    )
    second, job2, _ = await _video(
        api, ids, venue="Sporthalle Moosgarten", kickoff_at="2026-11-14T18:00:00+01:00"
    )
    info = {"method": "hall", "reference_video_id": first, "floor_inliers": floor, "error_px": 1.5}
    await _finish(
        api,
        job2,
        {
            "calibration": _court("heuristic"),
            "calibration_info": info,
            "tracks": _tracks(),
            "panorama": PANORAMA,
        },
    )
    assert await _state(api, org, second) == state
