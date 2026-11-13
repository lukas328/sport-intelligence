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
    # the goal sequence of the report, in order, misses left out
    assert g["report_goals"] == [
        {"minute": 1.58, "team": "own"},
        {"minute": 3.33, "team": "opp"},
        {"minute": 5.5, "team": "own"},
    ]
    # only the goal with a spot is drawn: no run without tracking, the spot as marked
    assert len(g["goals"]) == 1
    goal = g["goals"][0]
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

    tracks = [
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
