"""Shot candidates (kind "shot" of the goal candidates): stored beside the goal candidates,
suggested from the official report, confirmed with an outcome, merged with known shots."""

from __future__ import annotations

from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

import pytest

from handball_api.core.jobs import MemoryJobQueue
from handball_api.services import match_clock

from .conftest import Api, setup_club
from .test_auto_events import AUTO
from .test_identity_sync import _finish, _ingest, _tracks
from .test_matches import new_match, upload
from .test_official_report import CH_URL, recorded  # noqa: F401  (fixture)

pytestmark = pytest.mark.usefixtures("clean_db")


def _cand(goal_ms: int, rate: int, before_ms: int = 8000) -> dict[str, Any]:
    t_ms = goal_ms + 1500
    return {
        "t_ms": t_ms,
        "goal_ms": goal_ms,
        "start_ms": max(0, t_ms - before_ms),
        "end_ms": t_ms + 4000,
        "score": 1.5,
        "rate": rate,
        "rank": 0,
    }


SHOTS = {
    "template": "2026-11-05.s1",
    "default_rate": 4,
    "rates": [2, 4, 6],
    "candidates": [
        _cand(67_500, 2),  # report: save of the opponent's #5 at 2:06 = 66 s of video
        _cand(90_000, 4),  # report: miss of our #7 at 2:24 = 84 s
        _cand(214_500, 2),  # report: save, our #33, 4:34 = 214 s
        _cand(400_000, 4),  # nothing in the report
        _cand(500_000, 6),  # a shot tagged by hand at 501 s
    ],
}
FOUND = {
    "template": "2026-11-05.1",
    "default_rate": 2,
    "rates": [1, 2, 4],
    "candidates": [_cand(90_500, 1, 10_000)],
    "shots": SHOTS,
}
# the overlay clock runs from 1:00 at the start of the clip to 11:00
OVERLAY = {"goals": [], "clock": [{"start_ms": 0, "end_ms": 600_000, "start_clock_s": 60}]}


def test_clock_map_counts_from_the_nearer_anchor() -> None:
    match = SimpleNamespace(period_s=1800, kickoff_ms={"1": 10_000})
    ev = SimpleNamespace(clock_s=300.0, period=1, attributes={"video": {"t_ms": 400_000}})
    cm = match_clock.build(match, None, [ev])  # type: ignore[arg-type,list-item]
    # throw-off at 10 s, 5:00 shown at 400 s of video: the clock stood for 90 s in between
    assert cm.video_ms(1, 60.0) == (70_000, 90_000)
    assert cm.video_ms(1, 280.0) == (380_000, 90_000)
    assert cm.video_ms(1, 600.0) == (700_000, None)  # after the last anchor: unknown stops
    assert cm.video_ms(2, 2000.0) == (None, None)
    # an overlay run is exact
    cm = match_clock.build(match, {"scoreboard": OVERLAY}, [])  # type: ignore[arg-type]
    assert cm.video_ms(1, 126.0) == (66_000, 0)
    assert cm.video_ms(1, 42.0) == (-18_000, None)  # before the run: stops unknown


async def test_shot_candidates_with_the_official_report(
    make_api: Callable[[], Api],
    recorded: list[tuple[str, int]],  # noqa: F811
    owner_conn: Any,
) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    m = await new_match(api, ids, opponent_name="HC Arbon")  # home: we are HSG Leimental
    base = f"/v1/orgs/{org}/matches/{m['id']}"
    url = f"{base}/goal-candidates"
    shot_url = f"{base}/shot-candidates"

    empty = (await api.get(shot_url)).json()
    assert empty["kind"] == "shot" and empty["candidates"] == [] and empty["official"] is None
    assert empty["default_rate"] == 4 and empty["rates"] == [2, 4, 6]
    assert (await api.get(f"{url}?kind=pass")).status_code == 422

    tagged = (
        await api.post(
            f"{base}/events",
            json={"type": "shot", "side": "own", "outcome": "miss", "t_ms": 501_000},
        )
    ).json()
    r = await api.post(f"{base}/official-report", json={"url": CH_URL})
    assert r.status_code == 200, r.text
    await upload(api, ids, m["id"], b"v" * 100)
    jobs: MemoryJobQueue = api.app.state.jobs
    await _ingest(api, jobs.jobs[-1][2], jobs.jobs[-1][3]["prefix"])
    job = jobs.jobs[-1][2]
    result = {"tracks": _tracks(), "detector": "model", "events": AUTO, "scoreboard": OVERLAY}
    await _finish(api, job, {**result, "goal_candidates": FOUND})

    goals = (await api.get(url)).json()
    assert [r["t_ms"] for r in goals["candidates"]] == [92_000]
    data = (await api.get(f"{url}?kind=shot")).json()
    assert data == (await api.get(shot_url)).json()
    assert data["template"] == "2026-11-05.s1"
    rows = data["candidates"]
    assert [r["kind"] for r in rows] == ["shot"] * 5
    save, miss, own_save, free, by_hand = rows
    assert (save["start_ms"], save["end_ms"], save["rate"]) == (61_000, 73_000, 2)
    sugg = save["suggestion"]
    assert (sugg["side"], sugg["outcome"], sugg["number"], sugg["name"]) == (
        "opponent",
        "save",
        5,
        "ÖZCELIK Zerin",
    )
    assert (sugg["t_ms"], sugg["uncertainty_ms"], sugg["official_time"]) == (66_000, 0, "02:06")
    assert (miss["suggestion"]["side"], miss["suggestion"]["outcome"]) == ("own", "miss")
    assert miss["suggestion"]["number"] == 7
    assert own_save["suggestion"]["outcome"] == "save" and own_save["suggestion"]["side"] == "own"
    assert free["suggestion"] is None
    assert by_hand["known"]["event_id"] == tagged["id"] and by_hand["suggestion"] is None
    assert data["counts"] == {
        "total": 5,
        "open": 4,
        "open_by_rate": {"2": 2, "4": 4, "6": 4},
        "confirmed": 0,
        "rejected": 0,
        "known": 1,
        "suggested": 3,
    }
    official = {(o["official_time"], o["outcome"]): o for o in data["official"]["shots"]}
    assert official[("00:42", "save")]["status"] == "outside"  # before the clip
    assert official[("00:42", "save")]["t_ms"] == -18_000
    assert official[("02:06", "save")]["status"] == "suggested"
    assert official[("02:06", "save")]["candidate_id"] == save["id"]
    assert official[("01:33", "goal")]["status"] == "missing"
    # second half: counted from its throw-off (108 s, the automatic events), stops unknown
    late = official[("31:34", "save")]
    assert (late["status"], late["t_ms"], late["uncertainty_ms"]) == ("missing", 202_000, None)
    assert data["official"]["counts"]["suggested"] == 3

    events_before = (await api.get(f"{base}/events")).json()
    entry = next(e for e in events_before if e["id"] == sugg["event_id"])
    # one key: the suggestion is taken, the report entry gets the video time; no second event
    r = await api.put(f"{url}/{save['id']}/review", json={"status": "confirmed"})
    assert r.status_code == 200, r.text
    done = r.json()
    assert (done["status"], done["side"], done["outcome"], done["event_id"]) == (
        "confirmed",
        "opponent",
        "save",
        entry["id"],
    )
    events = (await api.get(f"{base}/events")).json()
    assert len(events) == len(events_before)
    pinned = next(e for e in events if e["id"] == entry["id"])
    assert pinned["t_ms"] == 67_500 and pinned["number"] == 5
    assert pinned["attributes"]["video"]["source"] == "goal_candidate"
    assert pinned["attributes"]["video"]["candidate_id"] == save["id"]
    data = (await api.get(shot_url)).json()
    row = next(o for o in data["official"]["shots"] if o["event_id"] == entry["id"])
    assert (row["status"], row["candidate_id"], row["t_ms"]) == ("confirmed", save["id"], 67_500)
    # a re-import of the report keeps the confirmed video time; the candidate follows the entry
    assert (await api.post(f"{base}/official-report", json={"url": CH_URL})).status_code == 200
    again = next(e for e in (await api.get(f"{base}/events")).json() if e["clock_s"] == 126)
    assert again["t_ms"] == 67_500 and again["attributes"]["video"]["candidate_id"] == save["id"]
    rows = (await api.get(shot_url)).json()["candidates"]
    assert rows[0]["event_id"] == again["id"] and rows[0]["status"] == "confirmed"
    entry = {**entry, "id": again["id"]}

    # another side or outcome than the report entry it pins is refused
    review = f"{url}/{miss['id']}/review"
    r = await api.put(
        review,
        json={
            "status": "confirmed",
            "official_event_id": miss["suggestion"]["event_id"],
            "outcome": "save",
        },
    )
    assert r.status_code == 422
    # without a report entry: a side and an outcome are needed
    r = await api.put(f"{url}/{free['id']}/review", json={"status": "confirmed"})
    assert r.status_code == 422
    r = await api.put(f"{url}/{free['id']}/review", json={"status": "confirmed", "side": "own"})
    assert r.status_code == 422  # which outcome?
    r = await api.put(
        f"{url}/{free['id']}/review",
        json={"status": "confirmed", "side": "own", "outcome": "blocked", "number": 9},
    )
    assert r.status_code == 200, r.text
    blocked = r.json()
    mine = next(
        e for e in (await api.get(f"{base}/events")).json() if e["id"] == blocked["event_id"]
    )
    assert (mine["source"], mine["outcome"], mine["number"], mine["t_ms"]) == (
        "goal_candidate",
        "blocked",
        9,
        400_000,
    )
    assert mine["attributes"]["candidate_kind"] == "shot"
    # the coach says the miss was the opponent's: a new event, the report entry stays a suggestion
    r = await api.put(review, json={"status": "confirmed", "side": "opponent", "outcome": "miss"})
    assert r.status_code == 200, r.text
    assert r.json()["event_id"] != miss["suggestion"]["event_id"]
    # the goal candidate at the same moment is now covered by that shot
    goals = (await api.get(url)).json()
    assert goals["candidates"][0]["known"]["outcome"] == "miss"

    # undo: the report entry goes back to its time from the clock and is suggested again
    r = await api.put(f"{url}/{save['id']}/review", json={"status": None})
    assert (r.json()["status"], r.json()["event_id"]) == ("open", None)
    assert r.json()["suggestion"]["event_id"] == entry["id"]
    restored = next(e for e in (await api.get(f"{base}/events")).json() if e["id"] == entry["id"])
    assert restored["t_ms"] == entry["t_ms"] and "video" not in restored["attributes"]

    # reject: a hard negative; its report entry has no candidate left
    r = await api.put(f"{url}/{own_save['id']}/review", json={"status": "rejected"})
    assert r.json()["status"] == "rejected" and r.json()["suggestion"] is None
    data = (await api.get(shot_url)).json()
    statuses = {(o["official_time"], o["outcome"]): o["status"] for o in data["official"]["shots"]}
    assert statuses[("04:34", "save")] == "missing"

    # a re-analysis replaces the open candidates of each kind; reviewed ones stay
    rerun = {
        **FOUND,
        "candidates": [],
        "shots": {**SHOTS, "candidates": [_cand(215_000, 2), _cand(300_000, 2)]},
    }
    await owner_conn.execute(
        "UPDATE processing_jobs SET status = 'running' WHERE id = $1::uuid", job
    )
    await _finish(api, job, {**result, "goal_candidates": rerun})
    rows = (await api.get(shot_url)).json()["candidates"]
    assert [(r["goal_ms"], r["status"]) for r in rows] == [
        (90_000, "confirmed"),
        (214_500, "rejected"),
        (300_000, "open"),
        (400_000, "confirmed"),
    ]
    assert (await api.get(url)).json()["candidates"] == []


async def test_shots_confirmed_before_the_report_are_taken_over(
    make_api: Callable[[], Api],
    recorded: list[tuple[str, int]],  # noqa: F811
) -> None:
    """The coach confirmed a save on the video; the report imported later has it with the player:
    the report entry takes the video time and the candidate's own event goes (one save)."""
    api = make_api()
    ids = await setup_club(api)
    m = await new_match(api, ids, opponent_name="HC Arbon")
    base = f"/v1/orgs/{ids['org']}/matches/{m['id']}"
    await upload(api, ids, m["id"], b"v" * 100)
    jobs: MemoryJobQueue = api.app.state.jobs
    await _ingest(api, jobs.jobs[-1][2], jobs.jobs[-1][3]["prefix"])
    payload = {"tracks": [], "needs_calibration": True, "scoreboard": OVERLAY}
    await _finish(api, jobs.jobs[-1][2], {**payload, "goal_candidates": FOUND})
    rows = (await api.get(f"{base}/shot-candidates")).json()["candidates"]
    first = rows[0]
    r = await api.put(
        f"{base}/goal-candidates/{first['id']}/review",
        json={"status": "confirmed", "side": "opponent", "outcome": "save"},
    )
    own = r.json()["event_id"]
    assert (await api.post(f"{base}/official-report", json={"url": CH_URL})).status_code == 200
    events = (await api.get(f"{base}/events")).json()
    assert own not in {e["id"] for e in events}
    saves = [e for e in events if e["outcome"] == "save" and e["clock_s"] == 126]
    assert len(saves) == 1 and saves[0]["source"] == "official_report"
    assert saves[0]["t_ms"] == 67_500 and saves[0]["number"] == 5
    assert saves[0]["attributes"]["video"]["candidate_id"] == first["id"]
    # the other entries get their time from the overlay clock (1:00 at 0 s of the clip)
    miss = next(e for e in events if e["outcome"] == "miss" and e["clock_s"] == 144)
    assert miss["t_ms"] == 84_000
    data = (await api.get(f"{base}/shot-candidates")).json()
    assert data["candidates"][0]["event_id"] == saves[0]["id"]
    assert data["candidates"][1]["suggestion"]["event_id"] == miss["id"]
