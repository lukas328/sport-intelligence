"""Several files per match and match boundaries (addendum 01, 4.8)."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from handball_api.core.jobs import MemoryJobQueue

from .conftest import Api, setup_club
from .test_identity_sync import _finish, _tracks
from .test_matches import new_match, upload

pytestmark = pytest.mark.usefixtures("clean_db")


async def _ingest_at(
    api: Api, job_id: str, prefix: str, recorded: str | None, duration: float
) -> None:
    await _finish(
        api,
        job_id,
        {
            "proxy_key": prefix + "proxy.mp4",
            "hls_prefix": prefix + "hls/",
            "duration_s": duration,
            "recorded_at": recorded,
        },
    )


async def test_parts_ordered_by_camera_clock_with_gaps(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    m = await new_match(api, ids)
    jobs: MemoryJobQueue = api.app.state.jobs
    # the second half is uploaded first
    second = await upload(api, ids, m["id"], b"b" * 100, name="halbzeit2.mp4")
    await _ingest_at(
        api, jobs.jobs[-1][2], jobs.jobs[-1][3]["prefix"], "2026-11-07T18:47:00Z", 1800
    )
    first = await upload(api, ids, m["id"], b"a" * 100, name="halbzeit1.mp4")
    await _ingest_at(
        api,
        [j for j in jobs.jobs if j[3].get("asset_id") == first["id"]][-1][2],
        f"x/{first['id']}/",
        "2026-11-07T18:00:00Z",
        1800,
    )
    url = f"/v1/orgs/{ids['org']}/matches/{m['id']}/parts"
    parts = (await api.get(url)).json()
    assert [p["filename"] for p in parts] == ["halbzeit1.mp4", "halbzeit2.mp4"]
    assert parts[1]["gap_before_ms"] == 17 * 60 * 1000  # half-time break
    assert parts[0]["source"] == "metadata" and not parts[0]["confirmed"]
    swapped = (await api.put(url, json={"video_ids": [second["id"], first["id"]]})).json()
    assert [p["filename"] for p in swapped] == ["halbzeit2.mp4", "halbzeit1.mp4"]
    assert all(p["confirmed"] for p in swapped)
    assert (await api.put(url, json={"video_ids": [first["id"]]})).status_code == 422


async def test_boundary_suggestions(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    m = await new_match(api, ids)
    jobs: MemoryJobQueue = api.app.state.jobs
    await upload(api, ids, m["id"], b"v" * 100)
    await _ingest_at(api, jobs.jobs[-1][2], jobs.jobs[-1][3]["prefix"], None, 3600)
    auto = {
        "events": [
            {
                "t_ms": 1_500_000,
                "type": "pause",
                "team": None,
                "confidence": 0.9,
                "end_ms": 1_700_000,
            },
            {
                "t_ms": 1_700_000,
                "type": "match_boundary",
                "team": None,
                "confidence": 0.7,
                "pause_ms": 200_000,
            },
        ],
        "possessions": [],
        "sides": [],
        "missing": [],
    }
    await _finish(
        api, jobs.jobs[-1][2], {"tracks": _tracks(), "detector": "heuristic", "events": auto}
    )
    b = (await api.get(f"/v1/orgs/{ids['org']}/matches/{m['id']}/boundaries")).json()
    assert [(x["t_ms"], x["pause_ms"]) for x in b] == [(1_700_000, 200_000)]
