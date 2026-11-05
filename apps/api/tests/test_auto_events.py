"""Automatic events from the analysis (addendum 01, A3)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from handball_api.core.jobs import MemoryJobQueue

from .conftest import Api, setup_club
from .test_identity_sync import _finish, _ingest, _tracks
from .test_matches import new_match, upload

pytestmark = pytest.mark.usefixtures("clean_db")

AUTO = {
    "events": [
        {"t_ms": 8000, "type": "throw_off", "team": "home", "confidence": 0.9},
        {
            "t_ms": 61_600,
            "type": "goal",
            "team": "home",
            "confidence": 0.77,
            "inferred_from": "throw_off",
        },
        {"t_ms": 61_600, "type": "possession_change", "team": "away", "confidence": 0.9},
        {"t_ms": 68_000, "type": "throw_off", "team": "away", "confidence": 0.9},
        {"t_ms": 81_600, "type": "goal", "team": "away", "confidence": 0.75},
        {"t_ms": 88_000, "type": "throw_off", "team": "home", "confidence": 0.88},
        {"t_ms": 95_000, "type": "goal", "team": "away", "confidence": 0.3},
        {"t_ms": 100_000, "type": "side_change", "team": None, "confidence": 0.8},
        {"t_ms": 108_000, "type": "throw_off", "team": "away", "confidence": 0.9},
    ],
    "possessions": [
        {"team": "home", "start_ms": 9000, "end_ms": 21_600, "confidence": 0.9, "outcome": "lost"},
        {
            "team": "away",
            "start_ms": 23_000,
            "end_ms": 41_600,
            "confidence": 0.9,
            "outcome": "lost",
        },
        {
            "team": "home",
            "start_ms": 43_200,
            "end_ms": 61_600,
            "confidence": 0.9,
            "outcome": "goal",
        },
    ],
    "sides": [
        {"from_ms": 2800, "home_defends": "left"},
        {"from_ms": 100_000, "home_defends": "right"},
    ],
    "missing": [],
}


async def test_auto_events_from_analysis(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    m = await new_match(api, ids)
    ev_url = f"/v1/orgs/{org}/matches/{m['id']}/events"
    # a goal tagged by hand close to the automatic one wins
    await api.post(
        ev_url, json={"type": "shot", "side": "opponent", "outcome": "goal", "t_ms": 80_000}
    )
    await upload(api, ids, m["id"], b"v" * 100)
    jobs: MemoryJobQueue = api.app.state.jobs
    await _ingest(api, jobs.jobs[-1][2], jobs.jobs[-1][3]["prefix"])
    await _finish(
        api, jobs.jobs[-1][2], {"tracks": _tracks(), "detector": "heuristic", "events": AUTO}
    )

    match = (await api.get(f"/v1/orgs/{org}/matches/{m['id']}")).json()
    assert match["kickoff_ms"] == {"1": 8000, "2": 108_000}  # clock from the opening throw-offs
    events = (await api.get(ev_url)).json()
    auto = [e for e in events if e["source"] == "heuristic"]
    assert sorted((e["type"], e["side"], e["t_ms"]) for e in auto) == [
        ("shot", "own", 61_600),
        ("throw_off", "opponent", 68_000),
        ("throw_off", "opponent", 108_000),
        ("throw_off", "own", 8000),
        ("throw_off", "own", 88_000),
    ]
    goal = next(e for e in auto if e["type"] == "shot")
    assert goal["confidence"] == 0.77 and goal["clock_s"] == 53.6 and goal["outcome"] == "goal"
    stats = (await api.get(f"/v1/orgs/{org}/matches/{m['id']}/stats")).json()
    assert stats["own"]["goals"] == 1 and stats["opponent"]["goals"] == 1
    assert stats["possessions_source"] == "tracking"
    a = (await api.get(f"/v1/orgs/{org}/videos/{jobs.jobs[-1][3]['asset_id']}/analysis")).json()
    assert a["status"] == "ready"

    # a re-run of the analysis replaces the automatic rows, manual ones stay
    await _finish(
        api, jobs.jobs[-1][2], {"tracks": _tracks(), "detector": "heuristic", "events": AUTO}
    )
    again = (await api.get(ev_url)).json()
    assert len([e for e in again if e["source"] == "heuristic"]) == 5
    assert len([e for e in again if e["source"] != "heuristic"]) == 1


OVERLAY = {
    "first_score": [1, 0],
    "last_score": [3, 2],
    "goals": [
        {"t_ms": 63_000, "side": "right", "score": [1, 1]},
        {"t_ms": 91_000, "side": "left", "score": [2, 1]},
        {
            "t_ms": 400_000,
            "side": "right",
            "score": [2, 2],
            "scorer": {"number": 7, "name": "Mia KELLER"},
            "shot": {"t_ms": 397_000, "x": 34.0, "y": 8.0, "track_id": 3, "method": "number"},
        },
        {"t_ms": 900_000, "side": "left", "score": [3, 2]},
    ],
    "clock": [
        {"start_ms": 0, "end_ms": 285_000, "start_clock_s": 120, "reads": 20},
        {"start_ms": 300_000, "end_ms": 3_300_000, "start_clock_s": 1800, "reads": 200},
    ],
}


async def test_goals_and_clock_from_score_overlay(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    roster = f"/v1/orgs/{org}/teams/{ids['team']}/seasons/{ids['season']}/roster"
    mia = (
        await api.post(
            roster, json={"first_name": "Mia", "last_name": "Keller", "jersey_number": 7}
        )
    ).json()
    m = await new_match(api, ids, is_home=False)  # away game: the overlay's left team is them
    ev_url = f"/v1/orgs/{org}/matches/{m['id']}/events"
    await api.post(ev_url, json={"type": "shot", "side": "own", "outcome": "goal", "t_ms": 70_000})
    await upload(api, ids, m["id"], b"v" * 100)
    jobs: MemoryJobQueue = api.app.state.jobs
    await _ingest(api, jobs.jobs[-1][2], jobs.jobs[-1][3]["prefix"])
    attack = {"team": "away", "start_ms": 70_000, "end_ms": 88_500, "confidence": 0.9}
    events_in = {**AUTO, "possessions": [*AUTO["possessions"], attack]}
    payload = {"tracks": _tracks(), "detector": "model", "events": events_in, "scoreboard": OVERLAY}
    await _finish(api, jobs.jobs[-1][2], payload)

    match = (await api.get(f"/v1/orgs/{org}/matches/{m['id']}")).json()
    # clock from the overlay (the clip starts at 2:00), not from the throw-off heuristic
    assert match["kickoff_ms"] == {"1": -120_000, "2": 300_000}
    assert (match["score_own"], match["score_opponent"]) == (2, 3)  # video reaches the end
    events = (await api.get(ev_url)).json()
    read = sorted(
        (e["side"], e["t_ms"], e["period"], e["clock_s"])
        for e in events
        if e["source"] == "scoreboard_ocr"
    )
    # the own goal at 63 s is the one tagged by hand at 70 s; the opponent's goal shown at 91 s
    # moves to the end of their attack at 88.5 s
    assert read == [
        ("opponent", 88_500, 1, 208.5),
        ("opponent", 900_000, 2, 2400.0),
        ("own", 397_000, 2, 1897.0),
    ]
    # the scorer named by the overlay is linked to the roster
    own = next(e for e in events if e["source"] == "scoreboard_ocr" and e["side"] == "own")
    assert own["number"] == 7 and own["player_id"] == mia["player_id"]
    assert (own["x"], own["y"]) == (34.0, 8.0)  # where she scored from (normalised)
    # the overlay is the goal source: no goals from the throw-off heuristic
    assert not [e for e in events if e["source"] == "heuristic" and e["type"] == "shot"]
    a = (await api.get(f"/v1/orgs/{org}/videos/{jobs.jobs[-1][3]['asset_id']}/analysis")).json()
    assert a["auto_events"]["overlay_goals"] == 3 and a["auto_events"]["overlay_aligned"] == 1
    poss = (await api.get(f"/v1/orgs/{org}/matches/{m['id']}/possessions")).json()["phases"]
    assert [p["outcome"] for p in poss if p["start_ms"] == 70_000] == ["goal"]


async def test_marked_goal_gets_its_shot_position_from_the_tracks(
    make_api: Callable[[], Api],
) -> None:
    import numpy as np

    from handball_api.core.storage import MemoryStorage

    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    m = await new_match(api, ids)
    ev_url = f"/v1/orgs/{org}/matches/{m['id']}/events"
    # a courtside mark with the scorer's number, no position
    await api.post(
        ev_url,
        json={"type": "shot", "side": "own", "outcome": "goal", "t_ms": 20_000, "number": 7},
    )
    await upload(api, ids, m["id"], b"v" * 100)
    jobs: MemoryJobQueue = api.app.state.jobs
    prefix = jobs.jobs[-1][3]["prefix"]
    await _ingest(api, jobs.jobs[-1][2], prefix)
    # tracks: #7 runs in to 4 m from the goal at x = 40; a teammate gets even closer
    rows = [(t, 1, 30 + 0.75 * k, 10.0) for k, t in enumerate(range(12_000, 20_001, 1000))]
    rows += [(t, 2, 33 + 0.5 * k, 4.0) for k, t in enumerate(range(12_000, 20_001, 1000))]
    storage: MemoryStorage = api.app.state.storage
    await storage.put(
        "artifacts",
        jobs.jobs[-1][3]["prefix"] + "analysis/chunk_00000.bin",
        np.array(rows, "<f4").tobytes(),
        "application/octet-stream",
    )
    track = {"first_ms": 0, "last_ms": 30_000, "points": 9, "observed_share": 1.0}
    tracks = [
        {**track, "track_id": 1, "team": "home", "team_confidence": 0.9, "number": 7},
        {**track, "track_id": 2, "team": "home", "team_confidence": 0.9},
    ]
    await _finish(
        api,
        jobs.jobs[-1][2],
        {"tracks": tracks, "detector": "model", "chunks": 1, "chunk_ms": 30_000, "events": AUTO},
    )
    goal = next(e for e in (await api.get(ev_url)).json() if e["source"] != "heuristic")
    assert (goal["x"], goal["y"]) == (36.0, 10.0)  # the scorer, not the nearer teammate
    assert goal["attributes"]["position_source"] == "tracking_number"


def test_hall_scoreboard_goal_moves_back_within_its_window() -> None:
    """A goal read from the hall scoreboard can lie far back (board out of view): it moves to the
    scoring side's last attack inside its window, not further."""
    from handball_api.models import Event, Possession
    from handball_api.services.auto_events import align_goals

    def poss(side: str, start: int, end: int) -> Possession:
        return Possession(side=side, start_ms=start, end_ms=end, source="tracking", confidence=1.0)

    rows = [poss("own", 0, 20_000), poss("opponent", 20_000, 40_000), poss("own", 40_000, 52_000)]
    g = Event(
        type="shot", side="own", outcome="goal", t_ms=90_000, attributes={"window_ms": 60_000}
    )
    near = Event(type="shot", side="own", outcome="goal", t_ms=90_000, attributes={})
    assert align_goals([g, near], rows) == 1
    assert g.t_ms == 52_000 and rows[2].outcome == "goal"
    assert near.t_ms == 90_000  # 15 s window: no attack ended there


async def _rerun(api: Api, org: str, video_id: str, payload: dict[str, Any]) -> None:
    """A new analysis run of the video (as after clicked court points) with this result."""
    pts = [{"image": [10 * i, 20 * i + 5], "court": [10 * i, 5 * (i % 2)]} for i in range(4)]
    jobs: MemoryJobQueue = api.app.state.jobs
    r = await api.post(f"/v1/orgs/{org}/videos/{video_id}/calibration", json={"points": pts})
    assert r.status_code == 202, r.text
    await _finish(api, jobs.jobs[-1][2], payload)


async def test_reanalysis_keeps_the_coachs_decisions(make_api: Callable[[], Api]) -> None:
    """The coach checked the automatic goals (one overlay goal dismissed as a misreading in the
    comparison, one deleted) and deleted a wrong throw-off; the analysis then runs again (court
    points clicked). The check used to be lost and the deleted rows came back."""
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    m = await new_match(api, ids, is_home=False)
    base = f"/v1/orgs/{org}/matches/{m['id']}"
    video = await upload(api, ids, m["id"], b"v" * 100)
    jobs: MemoryJobQueue = api.app.state.jobs
    await _ingest(api, jobs.jobs[-1][2], jobs.jobs[-1][3]["prefix"])
    payload = {"tracks": _tracks(), "detector": "model", "events": AUTO, "scoreboard": OVERLAY}
    await _finish(api, jobs.jobs[-1][2], payload)

    def auto(rows: list[dict[str, Any]]) -> list[tuple[str, str, str, int]]:
        return sorted(
            (e["source"], e["type"], e["side"], e["t_ms"])
            for e in rows
            if e["source"] in ("scoreboard_ocr", "heuristic")
        )

    first = (await api.get(f"{base}/events")).json()
    overlay = sorted((e for e in first if e["source"] == "scoreboard_ocr"), key=lambda e: e["t_ms"])
    dismissed, deleted = overlay[0], overlay[1]
    throw_off = next(e for e in first if e["type"] == "throw_off" and e["t_ms"] == 88_000)
    r = await api.put(
        f"{base}/official-report/review",
        json={"event_id": dismissed["id"], "status": "dismissed"},
    )
    assert r.status_code == 204, r.text
    for e in (deleted, throw_off):
        assert (await api.delete(f"/v1/orgs/{org}/events/{e['id']}")).status_code == 204
    before = auto((await api.get(f"{base}/events")).json())

    await _rerun(api, org, video["id"], payload)
    again = (await api.get(f"{base}/events")).json()
    assert auto(again) == before
    new = next(
        e for e in again if e["source"] == "scoreboard_ocr" and e["t_ms"] == dismissed["t_ms"]
    )
    assert new["id"] != dismissed["id"] and new["attributes"]["review"] == "dismissed"
    cmp = (await api.get(f"{base}/official-report/comparison")).json()
    assert [x["review"] for x in cmp["extra"] if x["event_id"] == new["id"]] == ["dismissed"]
    a = (await api.get(f"/v1/orgs/{org}/videos/{video['id']}/analysis")).json()
    assert a["auto_events"]["overlay_goals"] == len(overlay) - 1  # the deleted one


async def test_second_file_of_a_match_keeps_the_first_files_events(
    make_api: Callable[[], Api],
) -> None:
    """Two halves as two main files: the events, the match clock and the possessions belong to
    the first file (the one the workspace plays). The analysis of the second file used to replace
    them with times of the other file."""
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    m = await new_match(api, ids)
    base = f"/v1/orgs/{org}/matches/{m['id']}"
    jobs: MemoryJobQueue = api.app.state.jobs
    first = await upload(api, ids, m["id"], b"v" * 100, name="halbzeit1.mp4")
    await _ingest(api, jobs.jobs[-1][2], jobs.jobs[-1][3]["prefix"])
    await _finish(api, jobs.jobs[-1][2], {"tracks": _tracks(), "detector": "model", "events": AUTO})
    events = (await api.get(f"{base}/events")).json()
    match = (await api.get(base)).json()
    possessions = (await api.get(f"{base}/possessions")).json()

    second = await upload(api, ids, m["id"], b"w" * 100, name="halbzeit2.mp4")
    await _ingest(api, jobs.jobs[-1][2], jobs.jobs[-1][3]["prefix"])
    analysis = [j for j in jobs.jobs if j[1] == "handball_gpu_worker.analysis.run_analysis"]
    job, payload = analysis[-1][2], analysis[-1][3]
    assert payload["asset_id"] == second["id"]
    other = {
        "events": [{"t_ms": 5000, "type": "throw_off", "team": "away", "confidence": 0.9}],
        "possessions": [{"team": "away", "start_ms": 6000, "end_ms": 9000, "confidence": 0.9}],
    }
    await _finish(api, job, {"tracks": _tracks(), "detector": "model", "events": other})

    assert (await api.get(f"{base}/events")).json() == events
    assert (await api.get(base)).json()["kickoff_ms"] == match["kickoff_ms"]
    assert (await api.get(f"{base}/possessions")).json() == possessions
    # the second file keeps its own tracks
    a = (await api.get(f"/v1/orgs/{org}/videos/{second['id']}/analysis")).json()
    assert a["status"] == "ready" and len(a["tracks"]) == len(_tracks())
    assert a["auto_events"] is None
    assert first["id"] != second["id"]
