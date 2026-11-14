"""Where the shot of a goal came from (fourth real-video test H7): Prüfen asks «Von wo?» after a
confirmed goal; the coach's tap is written on the goal, the estimate from the tracks is only the
fallback, and goals without a place (older matches, the match report) are filled in later."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np
import pytest

from handball_api.core.storage import MemoryStorage
from handball_api.models import Event
from handball_api.services.shot_positions import event_zone_at, zone_at, zone_of

from .conftest import Api, setup_club
from .test_goal_candidates import _cand
from .test_graphics import event
from .test_video_parts import HALF, SECOND, _analyse, _two_halves

pytestmark = pytest.mark.usefixtures("clean_db")


def test_zones_from_a_point_left_is_the_attackers_left() -> None:
    # attacked goal at x = 40, facing it the attacker's left is +y
    assert zone_at(38.5, 18.5) == "la" and zone_at(38.5, 1.5) == "ra"
    assert zone_at(35.0, 10.0) == "kr"
    assert zone_at(30.0, 10.0) == "rm"
    assert zone_at(34.0, 16.0) == "rl" and zone_at(34.0, 4.0) == "rr"
    # a long throw is the back court of its side, never no zone
    assert event_zone_at(20.0, 16.0) == "back_left" and zone_at(20.0, 10.0) == "rm"
    # penalty and fast break by their kind, before any zone or spot
    assert zone_of(Event(shot_type="penalty", shot_zone="back_left")) == "m7"
    assert zone_of(Event(shot_type="fast_break", x=34.0, y=4.0)) == "gs"
    assert zone_of(Event(x=34.0, y=16.0)) == "rl"  # an overlay goal: only its spot
    assert zone_of(Event()) is None


def _rows(points: list[tuple[int, int, float, float]]) -> bytes:
    return np.array(points, dtype="<f4").tobytes()


async def _second_half_with_tracks(
    api: Api, ids: dict[str, Any]
) -> tuple[str, str, str, dict[str, Any]]:
    """Both halves; the second half's tracks: home player 2 runs at the goal at x = 0 (the teams
    changed ends) and comes closest to it at (6, 5.2), the attacker's left back court."""
    match_id, first, second = await _two_halves(api, ids)
    storage: MemoryStorage = api.app.state.storage
    org = ids["org"]
    prefix = f"{org}/{match_id}/{second}/analysis/"
    run = [(40_500 + 1000 * i, 2, 14.0 - i, 10.0 - 0.6 * i) for i in range(9)]  # to (6, 5.2)
    run.append((50_000, 2, 6.0, 4.0))  # turning away: farther from the goal mouth
    await storage.put(
        "artifacts", prefix + "chunk_00001.bin", _rows(run), "application/octet-stream"
    )
    await _analyse(
        api,
        second,
        events=SECOND,
        goal_candidates={"candidates": [_cand(52_000, 1)]},
        chunks=2,
        chunk_ms=30_000,
    )
    base = f"/v1/orgs/{org}/matches/{match_id}"
    cand = (await api.get(f"{base}/goal-candidates")).json()["candidates"][-1]
    assert cand["t_ms"] == HALF + 52_000 and cand["video_asset_id"] == second
    return base, first, second, cand


def _goal(g: dict[str, Any], event_id: str) -> dict[str, Any]:
    return next(x for x in g["goals"] if x["event_id"] == event_id)


async def test_a_goal_in_the_second_half_gets_its_place_estimated_then_tapped(
    make_api: Callable[[], Api],
) -> None:
    api = make_api()
    ids = await setup_club(api)
    base, _, _, cand = await _second_half_with_tracks(api, ids)
    review = f"{base}/goal-candidates/{cand['id']}/review"

    # confirmed without a tap: the estimate from the second file's tracks, at the goal it attacks
    r = await api.put(review, json={"status": "confirmed", "side": "own"})
    assert r.status_code == 200, r.text
    row = r.json()
    assert (row["shot_zone"], row["zone_source"]) == ("rl", "estimated")
    g = (await api.get(f"{base}/graphics")).json()
    goal = _goal(g, row["event_id"])
    assert goal["t_ms"] == HALF + 50_500
    assert (goal["zone"], goal["zone_source"], goal["confirmed"]) == ("rl", "estimated", False)
    # mirrored to the goal at x = 40, then the half court (goal at the top, attacker's left small)
    assert goal["shot"] == [5.2, 6.0] and goal["spot_missing"] is False

    # the coach taps «Kreis» on the small court: the tap wins and is no longer estimated
    spot = f"{base}/goals/{row['event_id']}/spot"
    r = await api.put(spot, json={"shot_zone": "kr", "x": 35.5, "y": 10.5})
    assert r.status_code == 200, r.text
    assert r.json() == {
        "event_id": row["event_id"],
        "shot_zone": "kr",
        "zone_source": "coach",
        "x": 35.5,
        "y": 10.5,
    }
    goal = _goal((await api.get(f"{base}/graphics")).json(), row["event_id"])
    assert (goal["zone"], goal["zone_source"], goal["confirmed"]) == ("kr", "coach", True)
    assert goal["shot"] == [9.5, 4.5]
    listed = (await api.get(f"{base}/goal-candidates")).json()["candidates"][-1]
    assert (listed["shot_zone"], listed["zone_source"]) == ("kr", "coach")

    # a repeated confirmation without a tap keeps what the coach said
    r = await api.put(review, json={"status": "confirmed", "side": "own"})
    assert (r.json()["shot_zone"], r.json()["zone_source"]) == ("kr", "coach")


async def test_review_with_the_place_and_its_corrections(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    base, _, _, cand = await _second_half_with_tracks(api, ids)
    review = f"{base}/goal-candidates/{cand['id']}/review"

    bad = await api.put(review, json={"status": "confirmed", "side": "own", "x": 30, "y": 10})
    assert bad.status_code == 422  # a point needs its zone
    r = await api.put(
        review, json={"status": "confirmed", "side": "own", "shot_zone": "ra", "x": 38, "y": 2}
    )
    assert r.status_code == 200, r.text
    row = r.json()
    assert (row["shot_zone"], row["zone_source"]) == ("ra", "coach")
    spot = f"{base}/goals/{row['event_id']}/spot"

    # Siebenmeter: the 7 m mark and the kind of the shot
    r = (await api.put(spot, json={"shot_zone": "m7"})).json()
    assert (r["shot_zone"], r["x"], r["y"]) == ("m7", 33.0, 10.0)
    ev = next(e for e in (await api.get(f"{base}/events")).json() if e["id"] == row["event_id"])
    assert (ev["shot_type"], ev["shot_zone"]) == ("penalty", "penalty")

    # Gegenstoss replaces the place in the question; the estimate from the tracks stays a place
    r = (await api.put(spot, json={"shot_zone": "gs"})).json()
    assert (r["shot_zone"], r["zone_source"]) == ("gs", "coach")
    ev = next(e for e in (await api.get(f"{base}/events")).json() if e["id"] == row["event_id"])
    assert ev["shot_type"] == "fast_break"

    # a zone by keyboard (no point): an earlier point of another zone is not drawn there
    r = (await api.put(spot, json={"shot_zone": "rm"})).json()
    assert (r["shot_zone"], r["x"], r["y"]) == ("rm", None, None)
    ev = next(e for e in (await api.get(f"{base}/events")).json() if e["id"] == row["event_id"])
    assert ev["shot_type"] is None and ev["shot_zone"] == "back_centre"

    # «Weiss nicht»: the estimate from the tracks stands, and it is not asked again
    r = (await api.put(spot, json={"shot_zone": "unknown"})).json()
    assert (r["shot_zone"], r["zone_source"]) == ("rl", "unknown")
    goal = _goal((await api.get(f"{base}/graphics")).json(), row["event_id"])
    assert goal["zone_source"] == "unknown" and goal["spot_missing"] is False

    assert (await api.put(spot, json={"shot_zone": "xx"})).status_code == 422
    assert (await api.put(spot, json={"shot_zone": "rl", "x": 30})).status_code == 422


async def test_goals_without_a_place_are_filled_in_later(
    make_api: Callable[[], Api], owner_conn: Any
) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    base, _, _, _ = await _second_half_with_tracks(api, ids)
    match_id = base.rsplit("/", 1)[1]
    # a goal tagged in the first half without a place, a report goal in the video (the throw-off
    # places it), a report goal before the video and a save
    tagged = await event(
        api, org, match_id, type="shot", side="opponent", outcome="goal", t_ms=90_000
    )
    report = await event(api, org, match_id, type="shot", side="own", outcome="goal", clock_s=200)
    early = await event(api, org, match_id, type="shot", side="own", outcome="goal", t_ms=1000)
    save = await event(api, org, match_id, type="shot", side="own", outcome="save", t_ms=95_000)
    await owner_conn.execute(
        "UPDATE events SET source = 'official_report' WHERE id = ANY($1::uuid[])",
        [report["id"], early["id"]],
    )
    await owner_conn.execute("UPDATE events SET t_ms = -5000 WHERE id = $1", early["id"])

    g = (await api.get(f"{base}/graphics")).json()
    missing = {x["event_id"] for x in g["goals"] if x["spot_missing"]}
    assert tagged["id"] in missing and report["id"] in missing
    assert early["id"] not in missing  # before the video: not asked

    for goal_id, zone in ((tagged["id"], "la"), (report["id"], "rr")):
        r = await api.put(f"{base}/goals/{goal_id}/spot", json={"shot_zone": zone})
        assert r.status_code == 200, r.text
    g = (await api.get(f"{base}/graphics")).json()
    assert _goal(g, tagged["id"])["zone"] == "la"
    assert _goal(g, report["id"])["zone"] == "rr" and g["has_report"] is True
    assert not any(x["spot_missing"] for x in g["goals"] if x["event_id"] != early["id"])
    # the report goal stays the report's
    ev = next(e for e in (await api.get(f"{base}/events")).json() if e["id"] == report["id"])
    assert ev["source"] == "official_report"

    # only goals of this match, only goals
    assert (
        await api.put(f"{base}/goals/{save['id']}/spot", json={"shot_zone": "la"})
    ).status_code == 422
    other = await setup_club(api, email="andere@hc-test.ch")
    r = await api.put(
        f"/v1/orgs/{other['org']}/matches/{match_id}/goals/{tagged['id']}/spot",
        json={"shot_zone": "la"},
    )
    assert r.status_code in (403, 404)
    actions = await owner_conn.fetch(
        "SELECT data FROM audit_logs WHERE action = 'match.shot_spot_set'"
    )
    assert len(actions) == 2
