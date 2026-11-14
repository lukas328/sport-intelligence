"""The data of the Anlauf graphics (ANLAUF.md section 10): only what is measured or marked."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .conftest import Api, setup_club
from .test_matches import new_match


async def event(api: Api, org: str, match_id: str, **body: Any) -> dict[str, Any]:
    r = await api.post(f"/v1/orgs/{org}/matches/{match_id}/events", json=body)
    assert r.status_code == 201, r.text
    return dict(r.json())


async def test_graphics_from_the_report_without_video(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    m = await new_match(api, ids)
    # two goals of ours (one with a marked spot from the left wing), one of theirs, a penalty
    await event(
        api,
        org,
        m["id"],
        type="shot",
        side="own",
        outcome="goal",
        clock_s=95,
        x=38.5,
        y=18.5,
        shot_zone="wing_left",
        number=7,
    )
    await event(api, org, m["id"], type="shot", side="opponent", outcome="goal", clock_s=200)
    await event(api, org, m["id"], type="suspension_2min", side="opponent", clock_s=300)
    await event(
        api,
        org,
        m["id"],
        type="shot",
        side="own",
        outcome="goal",
        clock_s=330,
        shot_type="penalty",
        number=9,
    )
    await event(api, org, m["id"], type="shot", side="own", outcome="miss", clock_s=400)

    r = await api.get(f"/v1/orgs/{org}/matches/{m['id']}/graphics")
    assert r.status_code == 200, r.text
    g = r.json()
    assert g["has_video"] is False and g["field_confirmed"] is None and g["source"] == "analysis"
    assert g["has_report"] is False  # goals entered by hand are no match report
    # the goal sequence of the report, in order, misses left out
    assert g["report_goals"] == [
        {"minute": 1.5833, "team": "own"},
        {"minute": 3.3333, "team": "opp"},
        {"minute": 5.5, "team": "own"},
    ]
    # every goal is listed (E01); only the goal with a spot can be drawn: no run without
    # tracking, the spot as marked
    assert len(g["goals"]) == 3 and not any(x["has_video"] for x in g["goals"])
    drawn = [x for x in g["goals"] if x["shot"] is not None]
    assert len(drawn) == 1
    goal = drawn[0]
    assert goal["run"] == [] and goal["source"] == "marked" and goal["confirmed"] is True
    assert goal["zone"] == "la"
    # half court: attacker's left is small u, the goal line is v = 0
    assert goal["shot"] == [1.5, 1.5]
    # power play from the opponent's penalty, the penalty goal inside it
    pp = next(p for p in g["phases"] if p["kind"] == "power_play")
    assert (pp["count"], pp["goals_us"], pp["goals_them"], pp["estimated"]) == (1, 1, 0, False)
    assert pp["windows"] == [[5.0, 7.0]]
    assert g["checks"] == []

    # the tactics camera has nothing without a video, and never a ball
    scene = await api.get(f"/v1/orgs/{org}/matches/{m['id']}/scenes/{goal['event_id']}/camera")
    assert scene.status_code == 200, scene.text
    s = scene.json()
    assert s["tracks"] == [] and s["ball"] == [] and s["field_confirmed"] is None
    assert s["scorer"] == {"team": "own", "number": 7}


async def test_demo_match_draws_demo_positions(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    demo = (await api.post(f"/v1/orgs/{org}/teams/{ids['team']}/demo-match")).json()
    g = (await api.get(f"/v1/orgs/{org}/matches/{demo['id']}/graphics")).json()
    assert g["source"] == "demo" and g["field_confirmed"] is True
    assert g["goals"] and all(x["source"] == "demo" for x in g["goals"])
    # every run ends at its shot spot, inside the half court
    for x in g["goals"]:
        assert x["run"][-1] == x["shot"]
        assert all(0 <= u <= 20 and 0 <= v <= 20 for u, v in x["run"])
    # the same positions on every call
    again = (await api.get(f"/v1/orgs/{org}/matches/{demo['id']}/graphics")).json()
    assert again["goals"] == g["goals"]

    one = g["goals"][0]
    s = (
        await api.get(f"/v1/orgs/{org}/matches/{demo['id']}/scenes/{one['event_id']}/camera")
    ).json()
    assert s["source"] == "demo" and s["field_confirmed"] is True
    teams = [t["team"] for t in s["tracks"]]
    # six attackers, six defenders and the keeper, one referee
    assert teams.count("ref") == 1 and len(teams) == 14
    # the scorer's way ends where the shot was taken; the ball is not detected, so not drawn
    assert s["shot"] == s["tracks"][0]["xy"][-1]
    assert s["ball"] == []


async def test_scene_of_another_match_is_not_found(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    a = await new_match(api, ids)
    b = await new_match(api, ids, opponent_name="TV Anders")
    e = await event(api, org, a["id"], type="shot", side="own", outcome="goal", clock_s=60)
    r = await api.get(f"/v1/orgs/{org}/matches/{b['id']}/scenes/{e['id']}/camera")
    assert r.status_code == 404


def test_a_read_number_is_shown_once_per_team() -> None:
    from handball_api.services.graphics import unique_numbers

    tracks: list[dict[str, Any]] = [
        {"team": "own", "number": 15, "xy": [(0, 0), (1, 1)]},
        {"team": "own", "number": 15, "xy": [(0, 0), (1, 1), (2, 2)]},
        {"team": "opp", "number": 15, "xy": [(0, 0)]},
        {"team": "own", "number": None, "xy": [(0, 0)]},
    ]
    out = unique_numbers(tracks)
    assert [t["number"] for t in out] == [None, 15, 15, None]


def test_demo_positions_wait_for_an_open_court_question() -> None:
    from types import SimpleNamespace

    from handball_api.services.graphics import _shown_field

    video = SimpleNamespace()
    assert _shown_field(True, None, False, None) is True  # demo without a video of its own
    assert _shown_field(True, video, True, False) is False  # type: ignore[arg-type]  # court is still asked
    assert _shown_field(True, video, True, True) is True  # type: ignore[arg-type]
    assert _shown_field(False, video, True, False) is False  # type: ignore[arg-type]


async def test_prufen_asks_for_the_throw_off_until_it_is_set(make_api: Callable[[], Api]) -> None:
    """UX test B10: the throw-off is a question in Prüfen, not a setup step in the tab Video."""
    from .test_themes import ready_video

    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    m = await new_match(api, ids)
    await ready_video(api, ids, m["id"])
    g = (await api.get(f"/v1/orgs/{org}/matches/{m['id']}/graphics")).json()
    assert [c["kind"] for c in g["checks"]].count("kickoff") == 1
    r = await api.put(
        f"/v1/orgs/{org}/matches/{m['id']}/kickoff", json={"period": 1, "t_ms": 12_000}
    )
    assert r.status_code < 300, r.text
    g = (await api.get(f"/v1/orgs/{org}/matches/{m['id']}/graphics")).json()
    assert all(c["kind"] != "kickoff" for c in g["checks"])


async def test_a_throw_off_not_in_the_video_is_not_asked_again(
    make_api: Callable[[], Api],
) -> None:
    """Third real-video test G8: a clip without the throw-off left «Prüfen 1» standing with no
    way out. «Der Anwurf ist nicht im Video» ends the question; the minute the video's start
    shows, when given, sets the clock."""
    from .test_themes import ready_video

    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    base = f"/v1/orgs/{org}/matches"
    m = await new_match(api, ids)
    await ready_video(api, ids, m["id"])
    r = await api.put(f"{base}/{m['id']}/kickoff", json={"period": 1, "t_ms": 0, "absent": True})
    assert r.status_code == 204, r.text
    g = (await api.get(f"{base}/{m['id']}/graphics")).json()
    assert all(c["kind"] != "kickoff" for c in g["checks"])
    assert (await api.get(f"{base}/{m['id']}")).json()["kickoff_ms"] is None
    # another match: the start of the video shows minute 12
    other = await new_match(api, ids, opponent_name="TV Spaeter")
    await ready_video(api, ids, other["id"])
    r = await api.put(
        f"{base}/{other['id']}/kickoff",
        json={"period": 1, "t_ms": 0, "absent": True, "clock_s": 720},
    )
    assert r.status_code == 204, r.text
    assert (await api.get(f"{base}/{other['id']}")).json()["kickoff_ms"] == {"1": -720_000}
    g = (await api.get(f"{base}/{other['id']}/graphics")).json()
    assert all(c["kind"] != "kickoff" for c in g["checks"])


async def test_a_goal_names_its_scorer_for_the_confirmed_column(
    make_api: Callable[[], Api],
) -> None:
    """UX test N12: the column «Bestätigt» in Zahlen follows the goals of a person; a goal knows
    its scorer by person, not only by shirt number."""
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    team = (await api.get(f"/v1/orgs/{org}/teams/{ids['team']}")).json()
    player = (
        await api.post(
            f"/v1/orgs/{org}/teams/{ids['team']}/seasons/{team['current_season']['id']}/roster",
            json={"first_name": "Tim", "last_name": "Baumann", "jersey_number": 11},
        )
    ).json()
    m = await new_match(api, ids)
    await event(
        api,
        org,
        m["id"],
        type="shot",
        side="own",
        outcome="goal",
        clock_s=95,
        x=38.5,
        y=18.5,
        player_id=player["player_id"],
    )
    g = (await api.get(f"/v1/orgs/{org}/matches/{m['id']}/graphics")).json()
    assert [x["player_id"] for x in g["goals"]] == [player["player_id"]]


async def test_a_confirmed_goal_without_spot_reaches_score_course_and_scene(
    make_api: Callable[[], Api], owner_conn: Any
) -> None:
    """Real-video test E01, E10: goals confirmed in Prüfen before the throw-off is set have no
    spot, no number and no clock. They are goals all the same; once the throw-off is set they
    get their match clock and stand in the course, which spans what the video covers."""
    from handball_api.core.jobs import MemoryJobQueue

    from .test_goal_candidates import FOUND
    from .test_identity_sync import _finish, _ingest, _tracks
    from .test_matches import upload

    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    m = await new_match(api, ids)
    base = f"/v1/orgs/{org}/matches/{m['id']}"
    vid = (await upload(api, ids, m["id"], b"v" * 100))["id"]
    jobs: MemoryJobQueue = api.app.state.jobs
    await _ingest(api, jobs.jobs[-1][2], jobs.jobs[-1][3]["prefix"])
    # no automatic events: no throw-off, no goal of the analysis
    await _finish(
        api,
        jobs.jobs[-1][2],
        {"tracks": _tracks(), "detector": "heuristic", "goal_candidates": FOUND},
    )
    await owner_conn.execute("UPDATE video_assets SET duration_s = 330 WHERE id = $1", vid)
    rows = (await api.get(f"{base}/goal-candidates")).json()["candidates"]
    for c, side in zip(rows[:3], ("own", "opponent", "opponent"), strict=True):
        r = await api.put(
            f"{base}/goal-candidates/{c['id']}/review", json={"status": "confirmed", "side": side}
        )
        assert r.status_code == 200, r.text

    g = (await api.get(f"{base}/graphics")).json()
    assert len(g["goals"]) == 3
    assert all(x["shot"] is None and x["minute"] is None for x in g["goals"])
    assert all(x["has_video"] and x["t_ms"] is not None for x in g["goals"])
    assert g["report_goals"] == [] and g["span"] is None
    # the video's goals are no match report (real-video test F6)
    assert g["has_report"] is False

    # the throw-off of the first half at 0:20 of the video
    r = await api.put(f"{base}/kickoff", json={"period": 1, "t_ms": 20_000})
    assert r.status_code == 204, r.text
    g = (await api.get(f"{base}/graphics")).json()
    minutes = sorted(x["minute"] for x in g["goals"])
    assert minutes == [
        round((61_500 - 20_000) / 60_000, 4),
        round(128.5 / 60, 4),
        round(178.5 / 60, 4),
    ]
    assert [x["team"] for x in g["report_goals"]] == ["own", "opp", "opp"]
    assert g["span"] == [0.0, round(310 / 60, 2)]
    # every event of the video has its clock now, the scene too
    camera = (await api.get(f"{base}/scenes/{g['goals'][0]['event_id']}/camera")).json()
    assert camera["clock_s"] is not None and camera["video_s"] is not None
    # the scene lies before the goal, not the way back (G3): a goal confirmed from a candidate
    # from 12 s before its time to 2 s after, because candidate times come late (V6)
    first = min(g["goals"], key=lambda x: x["t_ms"])
    camera = (await api.get(f"{base}/scenes/{first['event_id']}/camera")).json()
    assert camera["duration_s"] == 14.0
    assert camera["video_s"] == (first["t_ms"] - 12_000) / 1000
    assert first["scene"] == [first["t_ms"] - 12_000, first["t_ms"] + 2000]


def test_a_corner_outside_the_picture_is_accepted() -> None:
    """Real-video test E03: with a panning camera the near corners lie outside the hall image;
    the points are taken, only absurd ones are refused."""
    import pytest
    from pydantic import ValidationError

    from handball_api.schemas.matches import CalibrationIn

    points: list[dict[str, Any]] = [
        {"image": [-240.5, 1310.0], "court": [0, 0]},
        {"image": [1720.0, 1250.0], "court": [40, 0]},
        {"image": [1300.0, 210.0], "court": [40, 20]},
        {"image": [290.0, 205.0], "court": [0, 20]},
    ]
    body = {"space": "panorama", "points": points}
    assert CalibrationIn.model_validate(body).points[0].image == (-240.5, 1310.0)
    points[0]["image"] = [-1e9, 0]
    with pytest.raises(ValidationError):
        CalibrationIn.model_validate(body)


async def test_one_question_per_moment_and_the_rest_offered(
    make_api: Callable[[], Api], owner_conn: Any
) -> None:
    """Real-video test E07, E12: overlapping candidate windows are one moment, asked once; the
    strongest candidates are the questions (the one count of mail, start and Prüfen), the weaker
    ones are offered as more; a moment with a confirmed goal is not asked again."""
    from handball_api.core.jobs import MemoryJobQueue

    from .test_goal_candidates import FOUND, _cand
    from .test_identity_sync import _finish, _ingest, _tracks
    from .test_matches import upload

    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    m = await new_match(api, ids)
    base = f"/v1/orgs/{org}/matches/{m['id']}"
    await upload(api, ids, m["id"], b"v" * 100)
    jobs: MemoryJobQueue = api.app.state.jobs
    await _ingest(api, jobs.jobs[-1][2], jobs.jobs[-1][3]["prefix"])
    found = {**FOUND, "candidates": [*list(FOUND["candidates"]), _cand(66_000, 2)]}  # type: ignore[call-overload]
    await _finish(
        api,
        jobs.jobs[-1][2],
        {"tracks": _tracks(), "detector": "heuristic", "goal_candidates": found},
    )
    rows = {r["t_ms"]: r for r in (await api.get(f"{base}/goal-candidates")).json()["candidates"]}
    g = (await api.get(f"{base}/graphics")).json()
    goals = [c["id"] for c in g["checks"] if c["kind"] == "goal"]
    # 63 s and 66 s are 3 s apart: one goal, one question (the stronger, rate 1); 200 s (rate 4)
    # is offered
    assert goals == [rows[63_000]["id"], rows[150_000]["id"], rows[305_000]["id"]]
    assert [c["id"] for c in g["more_checks"]] == [rows[200_000]["id"]]
    assert {c["kind"] for c in g["checks"]} <= {"field", "kickoff", "goal"}
    # once the goal at 63 s is confirmed, the same goal at 66 s is not asked again
    r = await api.put(
        f"{base}/goal-candidates/{rows[63_000]['id']}/review",
        json={"status": "confirmed", "side": "own"},
    )
    assert r.status_code == 200, r.text
    g = (await api.get(f"{base}/graphics")).json()
    asked = {c["id"] for c in g["checks"]} | {c["id"] for c in g["more_checks"]}
    assert rows[66_000]["id"] not in asked and rows[63_000]["id"] not in asked
    assert g["analysis"] == "ready"
    # when it finished: the start puts a fresh analysis in its head
    assert g["analysis_at"] is not None


def test_goals_twelve_seconds_apart_are_two_goals() -> None:
    """Real-video test F4: the eight goals of clip 1, with 14 s clips that overlap their
    neighbours. Each is its own moment; two candidates are one goal only within 5 s and for the
    same side, and no chain of neighbours merges goals."""
    import uuid as _uuid

    from handball_api.models import GoalCandidate
    from handball_api.services.graphics import _windows

    goals = [
        (47.9, "opponent"),
        (61.1, "own"),
        (92.7, "opponent"),
        (134.5, "opponent"),
        (161.5, "own"),
        (212.5, "opponent"),
        (229.3, "own"),
        (241.1, "opponent"),
    ]

    def cand(s: float, side: str | None) -> GoalCandidate:
        ms = round(s * 1000)
        return GoalCandidate(
            id=_uuid.uuid4(),
            kind="goal",
            goal_ms=ms,
            t_ms=ms + 1500,
            start_ms=ms - 8500,
            end_ms=ms + 5500,
            score=2.0,
            rate=1,
            rank=0,
            suggested_side=side,
            status="open",
        )

    rows = [cand(s, side) for s, side in goals]
    # a chain of neighbours from 126.1 to 171.9 s, and a second look at 47.9 s two seconds later
    rows += [cand(s, None) for s in (126.1, 140.0, 150.0, 171.9)]
    rows.append(cand(49.9, "opponent"))
    groups = _windows(rows)
    firsts = {round(g[0].goal_ms / 1000, 1) for g in groups}
    assert all(s in firsts for s, _ in goals)
    # the second look at 47.9 s is the same goal; 61.1 s (other side, 13 s later) is not
    assert next(g for g in groups if g[0].goal_ms == 47_900)[1:][0].goal_ms == 49_900
    # without a suggested side the same rule holds: different times stay apart
    assert len(_windows([cand(229.3, None), cand(241.1, None)])) == 2


async def test_answers_survive_a_new_analysis_after_a_moved_court(
    make_api: Callable[[], Api],
) -> None:
    """Real-video test F3: saving moved corners runs the analysis again and rewrites the open
    candidates; a goal already confirmed keeps its answer and is not asked again, the others
    come back as questions."""
    from handball_api.core.jobs import MemoryJobQueue

    from .test_goal_candidates import FOUND
    from .test_identity_sync import _finish, _ingest, _tracks
    from .test_matches import upload

    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    m = await new_match(api, ids)
    base = f"/v1/orgs/{org}/matches/{m['id']}"
    vid = (await upload(api, ids, m["id"], b"v" * 100))["id"]
    jobs: MemoryJobQueue = api.app.state.jobs
    await _ingest(api, jobs.jobs[-1][2], jobs.jobs[-1][3]["prefix"])
    result = {"tracks": _tracks(), "detector": "heuristic", "goal_candidates": FOUND}
    await _finish(api, jobs.jobs[-1][2], result)
    first = (await api.get(f"{base}/goal-candidates")).json()["candidates"][0]
    r = await api.put(
        f"{base}/goal-candidates/{first['id']}/review", json={"status": "confirmed", "side": "own"}
    )
    assert r.status_code == 200, r.text

    # the coach moves a corner: the analysis runs again and finds the same candidates
    corners = [[100, 500], [1500, 500], [1300, 200], [300, 200]]
    court = [[0, 0], [40, 0], [40, 20], [0, 20]]
    pts = [{"image": i, "court": c} for i, c in zip(corners, court, strict=True)]

    async def notes() -> int:
        return len((await api.get(f"/v1/orgs/{org}/me/notifications")).json()["items"])

    before = await notes()
    r = await api.post(f"/v1/orgs/{org}/videos/{vid}/calibration", json={"points": pts})
    assert r.status_code == 202, r.text
    g = (await api.get(f"{base}/graphics")).json()
    assert g["analysis"] == "running" and g["analysis_at"] is None
    await _finish(api, jobs.jobs[-1][2], result)
    # the run after the corrected court sends no second mail and no notice (G4)
    assert await notes() == before

    rows = (await api.get(f"{base}/goal-candidates")).json()["candidates"]
    assert [r["goal_ms"] for r in rows if r["status"] == "confirmed"] == [first["goal_ms"]]
    assert not any(r["status"] == "open" and r["goal_ms"] == first["goal_ms"] for r in rows)
    g = (await api.get(f"{base}/graphics")).json()
    asked = {c["frame_ref"] for c in g["checks"] + g["more_checks"] if c["kind"] == "goal"}
    assert first["goal_ms"] not in asked and len(asked) == 3
    assert len([e for e in g["goals"] if e["has_video"]]) == 1


def test_scene_shows_only_the_court_unmirrored() -> None:
    """Third real-video test G3: spectators and the bench beside the court are not drawn; the
    attack on the goal at x = 40 stays there (right), not mirrored to x = 0."""
    import numpy as np

    from handball_api.services.graphics import SCENE_MS, scene_tracks

    start = 100_000.0
    rows = []
    for k in range(10):
        t = start + k * 500
        rows.append((t, 1, 30.0 + k * 0.5, 10.0))  # our player running to the goal at x = 40
        rows.append((t, 2, 35.0, 8.0))  # their defender
        rows.append((t, 3, 20.0, -4.0))  # a spectator in red beside the court
        rows.append((t, 4, 12.0, 22.5))  # the bench in white in front
    teams = {1: ("home", 7), 2: ("away", 3), 3: ("away", None), 4: ("home", None)}
    tracks, right = scene_tracks(np.array(rows, dtype=float), teams, start, ours=True)
    assert right is True
    assert sorted((t["team"], t["number"]) for t in tracks) == [("opp", 3), ("own", 7)]
    ours = next(t for t in tracks if t["team"] == "own")
    assert ours["xy"][0] == (30.0, 10.0) and ours["xy"][-1] == (34.5, 10.0)
    assert ours["ts"][0] == 0.0 and ours["ts"][-1] == round(4500 / SCENE_MS, 4)
