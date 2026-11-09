"""Courts carried over between videos of the same hall (backlog item 1, ADR 025)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from handball_api.core.jobs import MemoryJobQueue
from handball_api.services.halls import fold

from .conftest import Api, setup_club
from .test_identity_sync import _finish, _ingest, _tracks
from .test_matches import new_match, upload

pytestmark = pytest.mark.usefixtures("clean_db")

PANORAMA = {"width": 3600, "height": 1100}


def _court(source: str, size: tuple[int, int] = (3600, 1100)) -> dict[str, Any]:
    return {
        "homography": [[2.0, 0, 10], [0, 2.0, 20], [0, 0, 1]],
        "image_size": list(size),
        "confidence": 1.0,
        "reprojection_px": 0.5,
        "source": source,
    }


async def _video(api: Api, ids: dict[str, Any], **match: Any) -> tuple[str, str, dict[str, Any]]:
    """A match with an uploaded and ingested video: (video id, analysis job id, job payload)."""
    m = await new_match(api, ids, **match)
    vid = (await upload(api, ids, m["id"], b"v" * 100))["id"]
    jobs: MemoryJobQueue = api.app.state.jobs
    await _ingest(api, jobs.jobs[-1][2], jobs.jobs[-1][3]["prefix"], audio=False)
    _, func, job, payload = jobs.jobs[-1]
    assert func == "handball_gpu_worker.analysis.run_analysis"
    return vid, job, payload


def test_hall_names_compare_without_case_accents_and_spaces() -> None:
    assert fold("  Sporthalle  Untermosen ") == fold("sporthalle untermosen")
    assert fold("Turnhalle Stäfa") == fold("TURNHALLE STAFA")
    assert fold("Halle Süd") != fold("Halle Nord")


async def test_the_clicked_court_of_a_hall_is_offered_to_its_later_videos(
    make_api: Callable[[], Api],
) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    jobs: MemoryJobQueue = api.app.state.jobs

    # first video of the hall: the automatic court failed (flat view), the coach clicks it once
    first, job, payload = await _video(api, ids, venue="Sporthalle Untermosen")
    assert "hall_references" not in payload  # nothing marked in this hall yet
    await _finish(
        api,
        job,
        {"needs_calibration": True, "calibration": None, "tracks": [], "panorama": PANORAMA},
    )
    a = (await api.get(f"/v1/orgs/{org}/videos/{first}/analysis")).json()
    assert a["hall"] == {"name": "Sporthalle Untermosen", "source": "match", "calibrated_videos": 0}
    pts = [{"image": [100 * i, 50 * i + 5], "court": [10 * i, 5 * (i % 2)]} for i in range(4)]
    body = {"points": pts, "space": "panorama"}
    assert (
        await api.post(f"/v1/orgs/{org}/videos/{first}/calibration", json=body)
    ).status_code == 202
    await _finish(
        api,
        jobs.jobs[-1][2],
        {"calibration": _court("user_correction"), "tracks": _tracks(), "panorama": PANORAMA},
    )

    # the next home game in the same hall (name written differently): the worker gets the court
    second, job2, payload2 = await _video(
        api, ids, venue="sporthalle  untermosen", kickoff_at="2026-11-14T18:00:00+01:00"
    )
    refs = payload2["hall_references"]
    assert [r["video_id"] for r in refs] == [first]
    assert refs[0]["panorama_key"].endswith(f"/{first}/analysis/panorama.jpg")
    assert refs[0]["homography"][0][0] == 2.0 and refs[0]["image_size"] == [3600, 1100]
    assert refs[0]["hall"] == "Sporthalle Untermosen"
    a2 = (await api.get(f"/v1/orgs/{org}/videos/{second}/analysis")).json()
    assert a2["hall"]["calibrated_videos"] == 1
    # the court carried over is shown as an automatic court for the coach to check
    info = {"method": "hall", "reference_video_id": first, "floor_inliers": 140}
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
    a2 = (await api.get(f"/v1/orgs/{org}/videos/{second}/analysis")).json()
    assert a2["calibration_info"]["method"] == "hall"
    assert a2["calibration"]["source"] == "heuristic"

    # an away game elsewhere gets nothing; a home game without a venue gets the usual home hall
    _, _, away = await _video(
        api, ids, venue="Halle Gegner", is_home=False, kickoff_at="2026-11-21T18:00:00+01:00"
    )
    assert "hall_references" not in away
    third, _, home = await _video(api, ids, kickoff_at="2026-11-28T18:00:00+01:00")
    assert [r["video_id"] for r in home["hall_references"]] == [first]
    a3 = (await api.get(f"/v1/orgs/{org}/videos/{third}/analysis")).json()
    assert a3["hall"] == {
        "name": "Sporthalle Untermosen",
        "source": "home_matches",
        "calibrated_videos": 1,
    }

    # once the coach confirms the carried-over court, that video is a reference too (newest first)
    assert (
        await api.post(f"/v1/orgs/{org}/videos/{second}/calibration/confirm")
    ).status_code == 200
    _, _, later = await _video(
        api, ids, venue="Sporthalle Untermosen", kickoff_at="2026-12-05T18:00:00+01:00"
    )
    assert [r["video_id"] for r in later["hall_references"]] == [second, first]


async def test_a_court_on_a_single_frame_is_not_offered(make_api: Callable[[], Api]) -> None:
    """Only courts on the hall image can be carried over (the worker matches hall images)."""
    api = make_api()
    ids = await setup_club(api)
    _, job, _ = await _video(api, ids, venue="Halle A")
    await _finish(
        api,
        job,
        {
            "calibration": _court("user_correction", (1280, 720)),
            "tracks": _tracks(),
            "panorama": PANORAMA,
        },
    )
    _, _, payload = await _video(api, ids, venue="Halle A", kickoff_at="2026-11-14T18:00:00+01:00")
    assert "hall_references" not in payload


async def test_a_rerun_with_clicked_points_needs_no_hall(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    jobs: MemoryJobQueue = api.app.state.jobs
    first, job, _ = await _video(api, ids, venue="Halle A")
    await _finish(
        api,
        job,
        {"calibration": _court("user_correction"), "tracks": _tracks(), "panorama": PANORAMA},
    )
    second, job2, _ = await _video(
        api, ids, venue="Halle A", kickoff_at="2026-11-14T18:00:00+01:00"
    )
    await _finish(api, job2, {"needs_calibration": True, "tracks": [], "panorama": PANORAMA})
    pts = [{"image": [100 * i, 50 * i + 5], "court": [10 * i, 5 * (i % 2)]} for i in range(4)]
    assert (
        await api.post(
            f"/v1/orgs/{org}/videos/{second}/calibration",
            json={"points": pts, "space": "panorama"},
        )
    ).status_code == 202
    payload = jobs.jobs[-1][3]
    assert payload["calibration_points"] and "hall_references" not in payload
    assert first != second


async def test_references_read_one_court_per_video_in_sql(
    make_api: Callable[[], Api], query_counter: list[str]
) -> None:
    """The newest court of each video is picked in the database (DISTINCT ON), and only the hall
    image size is read from the analysis, not every court and analysis of the organisation."""
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    jobs: MemoryJobQueue = api.app.state.jobs
    first, job, _ = await _video(api, ids, venue="Sporthalle Untermosen")
    await _finish(
        api,
        job,
        {"needs_calibration": True, "calibration": None, "tracks": [], "panorama": PANORAMA},
    )
    pts = [{"image": [100 * i, 50 * i + 5], "court": [10 * i, 5 * (i % 2)]} for i in range(4)]
    body = {"points": pts, "space": "panorama"}
    for _ in range(2):  # two courts clicked on the same video: its newest counts
        assert (
            await api.post(f"/v1/orgs/{org}/videos/{first}/calibration", json=body)
        ).status_code == 202
        await _finish(
            api,
            jobs.jobs[-1][2],
            {"calibration": _court("user_correction"), "tracks": _tracks(), "panorama": PANORAMA},
        )
    second, _, payload = await _video(
        api, ids, venue="Sporthalle Untermosen", kickoff_at="2026-11-14T18:00:00+01:00"
    )
    assert [r["video_id"] for r in payload["hall_references"]] == [first]
    query_counter.clear()
    a = (await api.get(f"/v1/orgs/{org}/videos/{second}/analysis")).json()
    assert a["hall"]["calibrated_videos"] == 1
    refs = [q for q in query_counter if "FROM calibrations" in q and "JOIN matches" in q]
    assert refs, query_counter
    assert all("DISTINCT ON (calibrations.video_asset_id)" in q for q in refs)
    assert not any("video_assets.analysis AS" in q for q in refs)
