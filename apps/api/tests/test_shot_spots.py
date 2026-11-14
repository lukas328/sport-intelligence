"""Where the shot of a goal came from (fourth real-video test H7): Prüfen asks «Von wo?» after a
confirmed goal; the coach's tap is written on the goal, the estimate from the tracks is only the
fallback, and goals without a place (older matches, the match report) are filled in later."""

from __future__ import annotations

import json
import uuid
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
    assert goal["shot"] == [5.2, 6.0]
    # an estimate is shown, but it is no place the coach gave: still asked, in no thing (V1)
    assert goal["spot_by_coach"] is False and goal["spot_missing"] is True

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
    assert goal["spot_by_coach"] is True and goal["spot_missing"] is False
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
    # «Weiss nicht»: the estimate stays in the data, the place counts as missing and is asked again
    assert goal["zone_source"] == "unknown" and goal["spot_by_coach"] is False
    assert goal["spot_missing"] is True

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
    assert not any(
        x["spot_missing"] for x in g["goals"] if x["event_id"] in (tagged["id"], report["id"])
    )
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


def _homography(
    court: list[tuple[float, float]], image: list[tuple[float, float]]
) -> list[list[float]]:
    """Court-to-image homography from four correspondences (DLT)."""
    rows = []
    for (x, y), (u, v) in zip(court, image, strict=True):
        rows.append([x, y, 1, 0, 0, 0, -u * x, -u * y, -u])
        rows.append([0, 0, 0, x, y, 1, -v * x, -v * y, -v])
    _, _, vt = np.linalg.svd(np.array(rows, dtype=float))
    h = vt[-1].reshape(3, 3)
    out: list[list[float]] = (h / h[2, 2]).tolist()
    return out


CORNERS = [(0.0, 0.0), (40.0, 0.0), (40.0, 20.0), (0.0, 20.0)]
# the camera on the long side y = 0: the end x = 0 on the left of the picture
NEAR_Y0 = _homography(CORNERS, [(100, 700), (1180, 700), (900, 300), (380, 300)])
# the camera on the other long side (y = 20): the end x = 40 on the left
NEAR_Y20 = _homography(CORNERS, [(900, 300), (380, 300), (100, 700), (1180, 700)])


def test_where_the_attacked_goal_stands_in_the_video_in_all_four_positions() -> None:
    from handball_api.services.shot_positions import side_in_image

    assert side_in_image(NEAR_Y0, 0.0) == "left" and side_in_image(NEAR_Y0, 40.0) == "right"
    assert side_in_image(NEAR_Y20, 0.0) == "right" and side_in_image(NEAR_Y20, 40.0) == "left"
    flat = [[0.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    assert side_in_image(flat, 40.0) is None  # both ends on one point: nothing to say


async def test_the_court_of_von_wo_turns_as_the_camera_sees_it(
    make_api: Callable[[], Api], owner_conn: Any
) -> None:
    api = make_api()
    ids = await setup_club(api)
    base, _, second, cand = await _second_half_with_tracks(api, ids)
    row = (
        await api.put(
            f"{base}/goal-candidates/{cand['id']}/review",
            json={"status": "confirmed", "side": "own"},
        )
    ).json()
    view = f"{base}/goals/{row['event_id']}/view"
    # no court a person confirmed: drawn with the goal at the top
    assert (await api.get(view)).json()["goal_in_video"] is None

    async def court(h: list[list[float]], source: str = "user_correction") -> None:
        await owner_conn.execute(
            "INSERT INTO calibrations (id, organization_id, video_asset_id, homography, image_size,"
            " confidence, reprojection_px, source, pipeline_version) VALUES ($1, $2, $3, $4::jsonb,"
            " '[1280, 720]'::jsonb, 1, 0, $5, 'test')",
            uuid.uuid4(),
            uuid.UUID(ids["org"]),
            uuid.UUID(second),
            json.dumps(h),
            source,
        )

    await court(NEAR_Y0, "heuristic")
    assert (await api.get(view)).json()["goal_in_video"] is None  # recognised, not confirmed
    # the second half attacks the goal at x = 0: with the camera on y = 0 it is on the left
    await court(NEAR_Y0)
    assert (await api.get(view)).json() == {"event_id": row["event_id"], "goal_in_video": "left"}
    await court(NEAR_Y20)
    assert (await api.get(view)).json()["goal_in_video"] == "right"
    # the ends the analysis found for the half count before the attackers' places: before a fast
    # break the scorers stood at the goal they defended (seventh real-video test)
    await owner_conn.execute(
        "UPDATE video_assets SET analysis = jsonb_set(analysis, '{auto_events}',"
        ' \'{"sides": [{"from_ms": 0, "home_defends": "left"}]}\'::jsonb) WHERE id = $1',
        uuid.UUID(second),
    )
    assert (await api.get(view)).json()["goal_in_video"] == "left"  # own attacks x = 40


def test_one_scene_window_for_every_view() -> None:
    """V6: a goal from a candidate gets 12 s before its time and 5 s after (candidate times lie
    4 to 7 s after the goal); a report goal or one marked by hand keeps the usual window, the
    same length in Szenen and Sammlung."""
    from handball_api.services.matches import scene_lead, scene_window

    cand = Event(t_ms=20_000, source="goal_candidate", attributes={})
    pinned = Event(
        t_ms=20_000,
        source="official_report",
        attributes={"video": {"source": "goal_candidate", "t_ms": 20_000}},
    )
    report = Event(t_ms=20_000, source="official_report", attributes={})
    hand = Event(t_ms=20_000, source="user_correction", attributes={})
    assert scene_window(cand, None) == (8_000, 25_000)
    assert scene_window(pinned, None) == (8_000, 25_000)
    assert scene_window(report, None) == scene_window(hand, None) == (14_000, 23_000)
    assert scene_window(cand, 21_000) == (8_000, 21_000)  # cut at the video's end
    assert scene_lead(hand, (8_000, 2_000)) == (8_000, 2_000)  # the camera's own lead
    assert scene_lead(cand, (8_000, 2_000)) == (12_000, 5_000)
