"""Report goals taken over without a question (livegang L1, goal_candidates.auto_accept): only
where one goal candidate and one report goal meet on the overlay clock read in the video; all
else stays a question. Undone by the coach, a report goal is never taken over again."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from handball_api.core.jobs import MemoryJobQueue

from .conftest import Api, setup_club
from .test_identity_sync import _finish, _ingest, _tracks
from .test_matches import new_match, upload
from .test_official_report import CH_URL, recorded  # noqa: F401  (fixture)

pytestmark = pytest.mark.usefixtures("clean_db")

# the overlay clock runs from 1:00 at the start of the clip to 11:00: report goals of the fixture
# at 01:33 (ours, video 33 s), 02:59 (theirs, 119 s), 03:30 (ours, 150 s), 04:02 (theirs, 182 s)
# and 04:53 (theirs, 233 s)
OVERLAY = {"goals": [], "clock": [{"start_ms": 0, "end_ms": 600_000, "start_clock_s": 60}]}
EVENTS = {
    "events": [{"t_ms": 8000, "type": "throw_off", "team": "home", "confidence": 0.9}],
    "possessions": [
        # their attack ends just before 03:30, our goal: the candidate there is suggested theirs
        {"team": "away", "start_ms": 135_000, "end_ms": 146_000, "confidence": 0.9},
        {"team": "away", "start_ms": 220_000, "end_ms": 230_000, "confidence": 0.9},
    ],
}


def _cand(peak_ms: int, rate: int = 2) -> dict[str, Any]:
    return {
        "t_ms": peak_ms,
        "goal_ms": peak_ms - 1500,
        "start_ms": max(0, peak_ms - 10_000),
        "end_ms": peak_ms + 4000,
        "score": 1.5,
        "rate": rate,
        "rank": 0,
    }


FOUND: dict[str, Any] = {
    "template": "2026-11-05.1",
    "default_rate": 2,
    "rates": [1, 2, 4],
    "candidates": [
        _cand(35_000),  # 01:33, alone: taken over
        _cand(120_000),  # 02:59 with two candidates in reach: asked
        _cand(129_000, 4),
        _cand(152_000),  # 03:30 ours, suggested theirs: asked
        _cand(184_000, 4),  # 04:02, alone (rate 4 too): taken over
        _cand(236_000),  # 04:53 theirs, suggested theirs: taken over
        _cand(400_000),  # no report goal near: asked
    ],
}


async def _analysed(
    api: Api,
    ids: dict[str, Any],
    overlay: dict[str, Any] | None = OVERLAY,
    events: dict[str, Any] = EVENTS,
    found: dict[str, Any] = FOUND,
) -> tuple[str, str, Callable[[], Any]]:
    org = ids["org"]
    m = await new_match(api, ids, opponent_name="HC Kalmoos")  # home: we are HSG Haselgrund
    base = f"/v1/orgs/{org}/matches/{m['id']}"
    r = await api.post(f"{base}/official-report", json={"url": CH_URL})
    assert r.status_code == 200, r.text
    await upload(api, ids, m["id"], b"v" * 100)
    jobs: MemoryJobQueue = api.app.state.jobs
    await _ingest(api, jobs.jobs[-1][2], jobs.jobs[-1][3]["prefix"])
    result: dict[str, Any] = {"tracks": _tracks(), "detector": "model", "events": events}
    if overlay is not None:
        result["scoreboard"] = overlay
    await _finish(api, jobs.jobs[-1][2], {**result, "goal_candidates": found})

    async def rows() -> dict[int, dict[str, Any]]:
        data = (await api.get(f"{base}/goal-candidates")).json()
        return {r["t_ms"]: r for r in data["candidates"]}

    return base, m["id"], rows


async def _report_goals(api: Api, base: str) -> dict[str, dict[str, Any]]:
    return {
        e["attributes"]["official_time"]: e
        for e in (await api.get(f"{base}/events")).json()
        if e["source"] == "official_report" and e["outcome"] == "goal"
    }


async def test_unambiguous_report_goals_are_taken_over(
    make_api: Callable[[], Api],
    recorded: list[tuple[str, int]],  # noqa: F811
) -> None:
    api = make_api()
    ids = await setup_club(api)
    base, _, rows = await _analysed(api, ids)
    got = await rows()
    taken = {t for t, r in got.items() if r["auto"]}
    assert taken == {35_000, 184_000, 236_000}
    for t in taken:
        assert got[t]["status"] == "confirmed" and got[t]["outcome"] == "goal"
    assert got[35_000]["side"] == "own" and got[236_000]["side"] == "opponent"
    # two candidates near one report goal, a side against the report, no report goal: asked
    for t in (120_000, 129_000, 152_000, 400_000):
        assert got[t]["status"] == "open" and not got[t]["auto"], t
    goals = await _report_goals(api, base)
    first = goals["01:33"]
    assert first["id"] == got[35_000]["event_id"]
    assert first["t_ms"] == 33_500  # the candidate's goal time
    video = first["attributes"]["video"]
    assert (video["auto"], video["candidate_id"], video["source"]) == (
        "report",
        got[35_000]["id"],
        "goal_candidate",
    )
    assert "video" not in goals["02:59"]["attributes"]

    # Prüfen asks none of the goals taken over; they used up no question of the round
    g = (await api.get(f"{base}/graphics")).json()
    asked = {c["id"] for c in [*g["checks"], *g["more_checks"]] if c["kind"] == "goal"}
    assert not asked & {got[t]["id"] for t in taken}
    assert got[400_000]["id"] in asked

    # undo: one tap, the report goal goes back to its time from the clock and is not taken
    # over again, also not after a re-import of the report
    r = await api.put(f"{base}/goal-candidates/{got[35_000]['id']}/review", json={"status": None})
    assert r.status_code == 200, r.text
    assert (r.json()["status"], r.json()["auto"], r.json()["event_id"]) == ("open", False, None)
    back = (await _report_goals(api, base))["01:33"]
    assert "video" not in back["attributes"] and back["attributes"]["auto_declined"] is True
    assert (await api.post(f"{base}/official-report", json={"url": CH_URL})).status_code == 200
    got = await rows()
    assert got[35_000]["status"] == "open" and not got[35_000]["auto"]
    again = await _report_goals(api, base)
    assert again["01:33"]["attributes"]["auto_declined"] is True
    # the others keep their automatic pin over the re-import
    assert got[236_000]["auto"] and got[236_000]["event_id"] == again["04:53"]["id"]
    assert again["04:53"]["attributes"]["video"]["auto"] == "report"

    # the coach confirms one taken over: it is the coach's now
    r = await api.put(
        f"{base}/goal-candidates/{got[236_000]['id']}/review", json={"status": "confirmed"}
    )
    assert r.status_code == 200, r.text
    assert (r.json()["status"], r.json()["auto"]) == ("confirmed", False)
    ev = (await _report_goals(api, base))["04:53"]
    assert "auto" not in ev["attributes"]["video"] and "auto_declined" not in ev["attributes"]


async def test_without_the_overlay_clock_everything_is_asked(
    make_api: Callable[[], Api],
    recorded: list[tuple[str, int]],  # noqa: F811
) -> None:
    """The report's times counted from the throw-off only: a guess, nothing is taken over."""
    api = make_api()
    ids = await setup_club(api)
    base, _, rows = await _analysed(api, ids, overlay=None)
    got = await rows()
    assert len(got) == len(FOUND["candidates"])
    assert all(r["status"] == "open" and not r["auto"] for r in got.values())
    goals = await _report_goals(api, base)
    assert all("video" not in g["attributes"] for g in goals.values())


async def test_after_a_stop_of_the_clock_the_read_clock_finds_the_goal(
    make_api: Callable[[], Api],
    recorded: list[tuple[str, int]],  # noqa: F811
) -> None:
    """The clock stood still for a minute after 03:30 (a time-out): the report's times counted
    from the throw-off are a minute early from then on, so the candidates of 04:02 and 04:53 are
    not «known» and would be asked. The overlay clock read in the video places the two report
    goals on them: no question."""
    api = make_api()
    ids = await setup_club(api)
    overlay = {
        "goals": [],
        "clock": [
            {"start_ms": 0, "end_ms": 150_000, "start_clock_s": 60},
            {"start_ms": 210_000, "end_ms": 600_000, "start_clock_s": 210},
        ],
    }
    found = {**FOUND, "candidates": [_cand(244_000), _cand(295_000)]}
    base, _, rows = await _analysed(api, ids, overlay, {"events": [], "possessions": []}, found)
    got = await rows()
    assert all(r["auto"] and r["status"] == "confirmed" for r in got.values())
    goals = await _report_goals(api, base)
    assert (goals["04:02"]["t_ms"], goals["04:53"]["t_ms"]) == (242_500, 293_500)
    g = (await api.get(f"{base}/graphics")).json()
    assert [c for c in [*g["checks"], *g["more_checks"]] if c["kind"] == "goal"] == []
