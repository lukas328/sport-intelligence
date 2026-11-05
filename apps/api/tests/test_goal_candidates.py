"""Goal candidates from the video analysis: stored, merged with known goals, reviewed."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from handball_api.core.jobs import MemoryJobQueue
from handball_api.services.goal_candidates import suggest_side

from .conftest import Api, setup_club
from .test_auto_events import AUTO
from .test_identity_sync import _finish, _ingest, _tracks
from .test_matches import new_match, upload

pytestmark = pytest.mark.usefixtures("clean_db")


def _cand(t_ms: int, rate: int, score: float = 2.0) -> dict[str, Any]:
    return {
        "t_ms": t_ms,
        "goal_ms": t_ms - 1500,
        "start_ms": max(0, t_ms - 10_000),
        "end_ms": t_ms + 4000,
        "score": score,
        "rate": rate,
        "rank": 0,
    }


FOUND = {
    "template": "2026-11-05.1",
    "default_rate": 2,
    "rates": [1, 2, 4],
    "candidates": [_cand(63_000, 1), _cand(150_000, 2), _cand(200_000, 4), _cand(305_000, 1)],
}


def test_suggested_side_is_the_attack_that_ended_last() -> None:
    class P:
        def __init__(self, side: str, end_ms: int) -> None:
            self.side, self.end_ms = side, end_ms

    attacks = [P("own", 40_000), P("opponent", 52_000), P("own", 70_000)]
    assert suggest_side(attacks, 55_000) == "opponent"
    assert suggest_side(attacks, 100_000) is None


async def test_goal_candidates_review_flow(make_api: Callable[[], Api], owner_conn: Any) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    m = await new_match(api, ids)
    base = f"/v1/orgs/{org}/matches/{m['id']}"
    url = f"{base}/goal-candidates"

    empty = (await api.get(url)).json()
    assert empty["candidates"] == [] and empty["template"] is None
    assert empty["default_rate"] == 2 and empty["rates"] == [1, 2, 4]

    # a goal tagged by hand at 3:21: the candidate at 3:25 is the same moment
    tagged = (
        await api.post(
            f"{base}/events",
            json={"type": "shot", "side": "opponent", "outcome": "goal", "t_ms": 201_000},
        )
    ).json()
    await upload(api, ids, m["id"], b"v" * 100)
    jobs: MemoryJobQueue = api.app.state.jobs
    await _ingest(api, jobs.jobs[-1][2], jobs.jobs[-1][3]["prefix"])
    job = jobs.jobs[-1][2]  # the analysis
    result = {"tracks": _tracks(), "detector": "heuristic", "events": AUTO}
    await _finish(api, job, {**result, "goal_candidates": FOUND})

    data = (await api.get(url)).json()
    assert data["template"] == "2026-11-05.1"
    rows = data["candidates"]
    assert [r["t_ms"] for r in rows] == [63_000, 150_000, 200_000, 305_000]
    first, second, third, fourth = rows
    # the home attack ended at 61.6 s: the own team probably scored
    assert first["suggested_side"] == "own" and second["suggested_side"] is None
    assert (first["start_ms"], first["end_ms"], first["goal_ms"]) == (53_000, 67_000, 61_500)
    assert first["clock_s"] == 53.5 and first["period"] == 1  # match clock from the throw-off
    assert third["known"] == {
        "event_id": tagged["id"],
        "source": "user_correction",
        "side": "opponent",
        "t_ms": 201_000,
        "outcome": "goal",
    }
    assert data["counts"] == {
        "total": 4,
        "open": 3,
        "open_by_rate": {"1": 2, "2": 3, "4": 3},
        "confirmed": 0,
        "rejected": 0,
        "known": 1,
        "suggested": 0,
    }
    assert data["kind"] == "goal" and data["official"] is None
    assert all(r["kind"] == "goal" and r["suggestion"] is None for r in rows)
    stats = (await api.get(f"{base}/stats")).json()
    assert stats["own"]["goals"] == 1  # the goal estimated from the throw-off

    review = f"{url}/{first['id']}/review"
    r = await api.put(review, json={"status": "confirmed"})
    assert r.status_code == 422  # whose goal?
    r = await api.put(f"{url}/{third['id']}/review", json={"status": "confirmed", "side": "own"})
    assert r.status_code == 409  # already a goal
    r = await api.put(review, json={"status": "confirmed", "side": "own"})
    assert r.status_code == 200, r.text
    done = r.json()
    assert (done["status"], done["side"], done["known"]) == ("confirmed", "own", None)
    goals = [
        e
        for e in (await api.get(f"{base}/events")).json()
        if e["type"] == "shot" and e["outcome"] == "goal"
    ]
    mine = next(e for e in goals if e["id"] == done["event_id"])
    assert (mine["source"], mine["side"], mine["t_ms"], mine["clock_s"]) == (
        "goal_candidate",
        "own",
        61_500,
        53.5,
    )
    assert mine["attributes"]["goal_candidate"] == first["id"]
    # the throw-off estimate of the same goal is superseded: still one own goal
    assert not [e for e in goals if e["source"] == "heuristic" and e["side"] == "own"]
    stats = (await api.get(f"{base}/stats")).json()
    assert stats["own"]["goals"] == 1
    # the side can be corrected; the same goal event is kept
    fixed = (await api.put(review, json={"status": "confirmed", "side": "opponent"})).json()
    assert fixed["event_id"] == done["event_id"] and fixed["side"] == "opponent"

    # reject: kept (a hard negative), hidden from the open list
    r = await api.put(f"{url}/{second['id']}/review", json={"status": "rejected"})
    assert r.json()["status"] == "rejected"
    # confirm then undo: the goal goes again
    r = await api.put(
        f"{url}/{fourth['id']}/review", json={"status": "confirmed", "side": "opponent"}
    )
    event_id = r.json()["event_id"]
    r = await api.put(f"{url}/{fourth['id']}/review", json={"status": None})
    assert (r.json()["status"], r.json()["event_id"]) == ("open", None)
    assert event_id not in {e["id"] for e in (await api.get(f"{base}/events")).json()}

    actions = await owner_conn.fetch(
        "SELECT data FROM audit_logs WHERE action = 'match.goal_candidate_reviewed'"
        " ORDER BY created_at"
    )
    assert len(actions) == 5
    import json

    logged = [json.loads(a["data"]) if isinstance(a["data"], str) else a["data"] for a in actions]
    assert logged[0]["review"] == "confirmed" and logged[0]["template"] == "2026-11-05.1"
    assert logged[0]["superseded"] and logged[0]["candidate_id"] == first["id"]
    assert logged[2]["review"] == "rejected" and logged[4]["removed_event_id"] == event_id

    # a re-analysis replaces the open candidates; the reviewed ones stay and are not proposed again
    again = {**FOUND, "candidates": [_cand(64_000, 1), _cand(152_000, 1), _cand(250_000, 2)]}
    rerun = "UPDATE processing_jobs SET status = 'running' WHERE id = $1::uuid"
    await owner_conn.execute(rerun, job)
    await _finish(api, job, {**result, "goal_candidates": again})
    rows = (await api.get(url)).json()["candidates"]
    assert [(r["t_ms"], r["status"]) for r in rows] == [
        (63_000, "confirmed"),
        (150_000, "rejected"),
        (250_000, "open"),
    ]
    events = (await api.get(f"{base}/events")).json()
    assert done["event_id"] in {e["id"] for e in events}

    # the open candidates of an analysis that found none go; the reviewed ones stay
    await owner_conn.execute(rerun, job)
    await _finish(api, job, {**result, "goal_candidates": None})
    rows = (await api.get(url)).json()["candidates"]
    assert [r["status"] for r in rows] == ["confirmed", "rejected"]

    # another club sees nothing and cannot review
    other = make_api()
    oid = await setup_club(other, "b@hc-test.ch")
    r = await other.get(f"/v1/orgs/{oid['org']}/matches/{m['id']}/goal-candidates")
    assert r.status_code == 404
    r = await other.put(
        f"/v1/orgs/{oid['org']}/matches/{m['id']}/goal-candidates/{first['id']}/review",
        json={"status": "rejected"},
    )
    assert r.status_code == 404


async def test_overlay_goal_covers_a_candidate(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    m = await new_match(api, ids)
    base = f"/v1/orgs/{ids['org']}/matches/{m['id']}"
    await upload(api, ids, m["id"], b"v" * 100)
    jobs: MemoryJobQueue = api.app.state.jobs
    await _ingest(api, jobs.jobs[-1][2], jobs.jobs[-1][3]["prefix"])
    overlay = {"goals": [{"t_ms": 290_000, "side": "left", "score": [1, 0]}], "clock": []}
    # no court found: the candidates come with the request to mark it
    await _finish(
        api,
        jobs.jobs[-1][2],
        {
            "tracks": [],
            "needs_calibration": True,
            "scoreboard": overlay,
            "goal_candidates": FOUND,
        },
    )
    data = (await api.get(f"{base}/goal-candidates")).json()
    covered = [r for r in data["candidates"] if r["known"]]
    # the overlay is updated a few seconds after the goal: 15 s apart is the same goal
    assert [(r["t_ms"], r["known"]["source"]) for r in covered] == [(305_000, "scoreboard_ocr")]
    assert data["counts"]["open"] == 3 and data["counts"]["known"] == 1
