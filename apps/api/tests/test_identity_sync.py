"""Track identities, physical load and goal-cam sync (M5)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from handball_api.core.jobs import MemoryJobQueue

from .conftest import Api, setup_club
from .test_matches import new_match, upload

pytestmark = pytest.mark.usefixtures("clean_db")


def _phys(distance: float, seconds: float, top: float, sprints: int) -> dict[str, Any]:
    return {
        "distance_m": distance,
        "duration_s": seconds,
        "max_speed_ms": top,
        "sprints": sprints,
        "band_distance_m": {"walk": distance / 2, "jog": distance / 2, "run": 0, "sprint": 0},
        "heatmap": [[1.0, 0.0], [0.0, 0.0]],
    }


async def _ingest(api: Api, job_id: str, prefix: str, audio: bool = True) -> None:
    token = {"x-internal-token": api.app.state.settings.internal_token.get_secret_value()}
    r = await api.http.post(
        f"/internal/jobs/{job_id}",
        headers=token,
        json={
            "status": "succeeded",
            "progress": 1,
            "result": {
                "proxy_key": prefix + "proxy.mp4",
                "hls_prefix": prefix + "hls/",
                "audio_key": prefix + "audio_8k.wav" if audio else None,
            },
        },
    )
    assert r.status_code == 200, r.text


async def _finish(api: Api, job_id: str, result: dict[str, Any]) -> None:
    token = {"x-internal-token": api.app.state.settings.internal_token.get_secret_value()}
    r = await api.http.post(
        f"/internal/jobs/{job_id}",
        headers=token,
        json={"status": "succeeded", "progress": 1, "result": result},
    )
    assert r.status_code == 200, r.text


def _tracks() -> list[dict[str, Any]]:
    return [
        {
            "track_id": 1,
            "first_ms": 0,
            "last_ms": 30_000,
            "points": 700,
            "observed_share": 0.9,
            "team": "home",
            "team_confidence": 0.9,
            "physical": _phys(100, 30, 6.2, 1),
        },
        {
            "track_id": 2,
            "first_ms": 32_000,
            "last_ms": 60_000,
            "points": 600,
            "observed_share": 0.8,
            "team": "home",
            "team_confidence": 0.8,
            "physical": _phys(80, 28, 5.0, 0),
        },
        {
            "track_id": 3,
            "first_ms": 0,
            "last_ms": 60_000,
            "points": 1400,
            "observed_share": 0.9,
            "team": "away",
            "team_confidence": 0.9,
            "number": 14,
            "physical": _phys(150, 60, 7.0, 2),
        },
        {
            "track_id": 4,
            "first_ms": 0,
            "last_ms": 60_000,
            "points": 1400,
            "observed_share": 0.9,
            "team": "referee",
            "team_confidence": 0.9,
            "physical": _phys(90, 60, 4.0, 0),
        },
    ]


async def test_identity_and_physical(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    roster = f"/v1/orgs/{org}/teams/{ids['team']}/seasons/{ids['season']}/roster"
    mia = (
        await api.post(
            roster, json={"first_name": "Mia", "last_name": "Keller", "jersey_number": 7}
        )
    ).json()
    m = await new_match(api, ids)
    assert (await api.get(f"/v1/orgs/{org}/matches/{m['id']}/physical")).json()["players"] == []
    vid = (await upload(api, ids, m["id"], b"v" * 100))["id"]
    jobs: MemoryJobQueue = api.app.state.jobs
    await _ingest(api, jobs.jobs[-1][2], jobs.jobs[-1][3]["prefix"])
    analysis_id = jobs.jobs[-1][2]
    seg = {"team": "away", "formation": "5-1", "start_ms": 0, "end_ms": 8000, "confidence": 0.9}
    await _finish(
        api, analysis_id, {"tracks": _tracks(), "detector": "heuristic", "formations": [seg]}
    )

    a = (await api.get(f"/v1/orgs/{org}/videos/{vid}/analysis")).json()
    assert a["formations"] == [seg]
    notes = (await api.get(f"/v1/orgs/{org}/me/notifications")).json()
    assert notes["items"][0]["kind"] == "analysis_ready"
    away = next(t for t in a["tracks"] if t["track_no"] == 3)
    assert (away["number"], away["identity_source"]) == (14, "model")
    assert away["physical"]["distance_m"] == 150

    base = f"/v1/orgs/{org}/videos/{vid}/tracks"
    # both fragments belong to Mia; the number comes from the roster
    for n in (1, 2):
        r = await api.put(f"{base}/{n}/identity", json={"player_id": mia["player_id"]})
        assert r.status_code == 200, r.text
        assert (r.json()["number"], r.json()["identity_source"]) == (7, "user_correction")
    assert (await api.put(f"{base}/99/identity", json={"number": 3})).status_code == 404
    stranger = "00000000-0000-0000-0000-000000000001"
    assert (await api.put(f"{base}/1/identity", json={"player_id": stranger})).status_code == 422

    phys = (await api.get(f"/v1/orgs/{org}/matches/{m['id']}/physical")).json()
    assert phys["estimated"] is True
    [p] = phys["players"]
    assert p["player_id"] == mia["player_id"]
    assert (p["distance_m"], p["sprints"], p["max_speed_ms"]) == (180, 1, 6.2)
    assert p["tracks"] == [1, 2]
    assert p["band_distance_m"]["walk"] == 90
    assert [t["track_no"] for t in phys["tracks"]] == [3]  # referee left out

    # a re-run keeps manual identities on the track that covers the same time
    r = await api.post(
        f"/v1/orgs/{org}/videos/{vid}/calibration",
        json={
            "points": [
                {"image": [10 * i, 20 * i + 5], "court": [10 * i, 5 * (i % 2)]} for i in range(4)
            ]
        },
    )
    assert r.status_code == 202
    rerun = _tracks()
    rerun[0]["track_id"] = 11
    await _finish(api, jobs.jobs[-1][2], {"tracks": rerun, "detector": "heuristic"})
    a = (await api.get(f"/v1/orgs/{org}/videos/{vid}/analysis")).json()
    t11 = next(t for t in a["tracks"] if t["track_no"] == 11)
    assert (t11["player_id"], t11["identity_source"]) == (mia["player_id"], "user_correction")

    # clearing
    r = await api.put(f"{base}/11/identity", json={"player_id": None, "number": None})
    assert (r.json()["player_id"], r.json()["identity_source"]) == (None, None)


async def test_goal_cam_sync(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    m = await new_match(api, ids)
    jobs: MemoryJobQueue = api.app.state.jobs

    # the goal cam is processed first: nothing to sync against yet
    cam = (await upload(api, ids, m["id"], b"g" * 100, name="tor.mp4", role="goal_cam_left"))["id"]
    await _ingest(api, jobs.jobs[-1][2], jobs.jobs[-1][3]["prefix"])
    assert jobs.jobs[-1][1] == "handball_worker.ingest.run_ingest"

    # the main video arrives: analysis and a sync job for the goal cam start
    await upload(api, ids, m["id"], b"v" * 100)
    await _ingest(api, jobs.jobs[-1][2], jobs.jobs[-1][3]["prefix"])
    sync = [j for j in jobs.jobs if j[1] == "handball_gpu_worker.sync.run_sync"]
    assert len(sync) == 1
    _, _, sync_id, payload = sync[0]
    assert payload["main_audio_key"].endswith("audio_8k.wav")
    assert payload["other_audio_key"] != payload["main_audio_key"]

    # weak audio match: stored, not applied
    await _finish(api, sync_id, {"offset_ms": -7250, "confidence": 0.1})
    v = next(
        x
        for x in (await api.get(f"/v1/orgs/{org}/matches/{m['id']}")).json()["videos"]
        if x["id"] == cam
    )
    assert v["time_offset_ms"] == 0
    assert v["sync"] == {"offset_ms": -7250, "confidence": 0.1, "source": "audio", "applied": False}

    # manual offset wins and blocks further automatic sync
    r = await api.patch(f"/v1/orgs/{org}/videos/{cam}", json={"time_offset_ms": -7000})
    assert r.json()["sync"]["source"] == "user_correction"
    assert r.json()["time_offset_ms"] == -7000


async def test_sync_applied_when_confident(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    m = await new_match(api, ids)
    jobs: MemoryJobQueue = api.app.state.jobs
    await upload(api, ids, m["id"], b"v" * 100)
    await _ingest(api, jobs.jobs[-1][2], jobs.jobs[-1][3]["prefix"])
    cam = (await upload(api, ids, m["id"], b"g" * 100, name="tor.mp4", role="goal_cam_right"))["id"]
    await _ingest(api, jobs.jobs[-1][2], jobs.jobs[-1][3]["prefix"])
    _, func, sync_id, _ = jobs.jobs[-1]
    assert func == "handball_gpu_worker.sync.run_sync"
    await _finish(api, sync_id, {"offset_ms": 3120, "confidence": 0.8})
    v = next(
        x
        for x in (await api.get(f"/v1/orgs/{org}/matches/{m['id']}")).json()["videos"]
        if x["id"] == cam
    )
    assert (v["time_offset_ms"], v["sync"]["applied"]) == (3120, True)
    # a failed sync keeps the video playable
    cam2 = (await upload(api, ids, m["id"], b"h" * 100, name="b.mp4", role="other"))["id"]
    await _ingest(api, jobs.jobs[-1][2], jobs.jobs[-1][3]["prefix"], audio=False)
    assert jobs.jobs[-1][1] != "handball_gpu_worker.sync.run_sync"  # no audio, no sync
    v2 = next(
        x
        for x in (await api.get(f"/v1/orgs/{org}/matches/{m['id']}")).json()["videos"]
        if x["id"] == cam2
    )
    assert v2["status"] == "ready" and v2["sync"] is None
