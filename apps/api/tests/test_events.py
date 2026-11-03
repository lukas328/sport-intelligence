from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import pytest

from .conftest import Api, setup_club
from .test_matches import new_match

pytestmark = pytest.mark.usefixtures("clean_db")


async def roster(api: Api, ids: dict[str, Any]) -> dict[int, str]:
    url = f"/v1/orgs/{ids['org']}/teams/{ids['team']}/seasons/{ids['season']}/roster"
    out = {}
    for n, name in ((7, "Lena"), (9, "Mia"), (1, "Tina")):
        r = await api.post(url, json={"first_name": name, "last_name": "X", "jersey_number": n})
        out[n] = r.json()["player_id"]
    return out


async def test_events_crud_filters_corrections_and_stats(
    make_api: Callable[[], Api], owner_conn: Any
) -> None:
    api = make_api()
    ids = await setup_club(api)
    players = await roster(api, ids)
    org, m = ids["org"], (await new_match(api, ids))["id"]
    url = f"/v1/orgs/{org}/matches/{m}/events"
    goal = {
        "type": "shot",
        "side": "own",
        "outcome": "goal",
        "player_id": players[7],
        "x": 34.5,
        "y": 10.0,
        "goal_zone": "TL",
        "t_ms": 65_000,
    }
    r = await api.post(url, json=goal)
    assert r.status_code == 201, r.text
    e1 = r.json()
    assert e1["shot_zone"] == "circle_centre" and e1["source"] == "user_correction"
    assert e1["clock_s"] is None  # no throw-off time known yet
    await api.post(
        url,
        json={
            "type": "shot",
            "side": "own",
            "outcome": "save",
            "player_id": players[9],
            "x": 29,
            "y": 15,
            "t_ms": 90_000,
        },
    )
    await api.post(
        url,
        json={"type": "turnover", "side": "own", "turnover_type": "steps", "player_id": players[9]},
    )
    await api.post(
        url,
        json={
            "type": "shot",
            "side": "opponent",
            "outcome": "goal",
            "number": 11,
            "goal_zone": "BR",
        },
    )
    # validation
    assert (await api.post(url, json={"type": "shot", "side": "own"})).status_code == 422
    assert (
        await api.post(url, json={"type": "turnover", "side": "own", "outcome": "goal"})
    ).status_code == 422
    assert (
        await api.post(url, json={"type": "shot", "side": "own", "outcome": "goal", "x": 3})
    ).status_code == 422
    other = await api.post(url, json={**goal, "player_id": ids["team"]})
    assert other.status_code == 422 and other.json()["type"].endswith(":player-not-in-team")

    assert len((await api.get(url, params={"side": "own", "type": "shot"})).json()) == 2
    assert [
        e["outcome"] for e in (await api.get(url, params={"player_id": players[9]})).json()
    ] == ["save", None]
    assert len((await api.get(url, params={"zone": "circle_centre"})).json()) == 1

    stats = (await api.get(f"/v1/orgs/{org}/matches/{m}/stats")).json()
    assert (
        stats["own"]["goals"] == 1 and stats["own"]["shots"] == 2 and stats["own"]["turnovers"] == 1
    )
    assert stats["opponent"]["goals"] == 1
    assert stats["players"][f"p:{players[7]}"]["goals"] == 1
    assert stats["possessions_source"] == "heuristic_estimate"
    assert stats["own"]["possessions"] == 3
    # cached until events change
    version = await owner_conn.fetchval("SELECT version FROM stats_cache")
    await api.get(f"/v1/orgs/{org}/matches/{m}/stats")
    assert await owner_conn.fetchval("SELECT version FROM stats_cache") == version

    upd = await api.patch(f"/v1/orgs/{org}/events/{e1['id']}", json={"outcome": "post"})
    assert upd.json()["outcome"] == "post"
    stats = (await api.get(f"/v1/orgs/{org}/matches/{m}/stats")).json()
    assert stats["own"]["goals"] == 0 and stats["own"]["posts"] == 1
    assert await owner_conn.fetchval("SELECT version FROM stats_cache") != version
    assert (await api.delete(f"/v1/orgs/{org}/events/{e1['id']}")).status_code == 204
    actions = [
        r["action"]
        for r in await owner_conn.fetch("SELECT action FROM corrections ORDER BY created_at")
    ]
    assert actions.count("create") == 4 and actions[-2:] == ["update", "delete"]


async def test_kickoff_maps_clock_and_video(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    org, m = ids["org"], (await new_match(api, ids))["id"]
    url = f"/v1/orgs/{org}/matches/{m}/events"
    feed_like = await api.post(
        url, json={"type": "timeout", "side": "own", "period": 2, "clock_s": 2000}
    )
    assert feed_like.json()["t_ms"] is None
    assert (
        await api.put(f"/v1/orgs/{org}/matches/{m}/kickoff", json={"period": 1, "t_ms": 30_000})
    ).status_code == 204
    await api.put(f"/v1/orgs/{org}/matches/{m}/kickoff", json={"period": 2, "t_ms": 2_000_000})
    # a click in the video at 10 min of the first half
    e = (
        await api.post(
            url, json={"type": "shot", "side": "own", "outcome": "goal", "t_ms": 630_000}
        )
    ).json()
    assert (e["period"], e["clock_s"]) == (1, 600.0)
    e2 = (
        await api.post(
            url, json={"type": "shot", "side": "own", "outcome": "miss", "t_ms": 2_060_000}
        )
    ).json()
    assert (e2["period"], e2["clock_s"]) == (2, 1860.0)
    timeout = next(x for x in (await api.get(url)).json() if x["type"] == "timeout")
    assert timeout["t_ms"] == 2_000_000 + 200_000  # aligned when the second-half throw-off was set
    match = (await api.get(f"/v1/orgs/{org}/matches/{m}")).json()
    assert match["kickoff_ms"] == {"1": 30_000, "2": 2_000_000}


async def test_feed_import(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    players = await roster(api, ids)
    org, m = ids["org"], (await new_match(api, ids))["id"]
    await api.put(f"/v1/orgs/{org}/matches/{m}/kickoff", json={"period": 1, "t_ms": 10_000})
    csv = (
        "period;clock;team;event;number\n1;01:30;own;goal;7\n1;02:10;gegner;tor;5\n1;03:00;own;7m_goal;9\n"
        "1;04:00;own;2min;9\n1;05:00;own;unknown;1\n1;xx;own;goal;7\n1;06:00;mars;goal;7\n"
    )
    r = await api.post(
        f"/v1/orgs/{org}/matches/{m}/events/import",
        files={"file": ("feed.csv", csv.encode(), "text/csv")},
    )
    res = r.json()
    assert (res["created"], res["skipped"]) == (4, 1)
    assert len(res["errors"]) == 2
    events = (await api.get(f"/v1/orgs/{org}/matches/{m}/events")).json()
    first = events[0]
    assert (first["source"], first["clock_s"], first["t_ms"], first["player_id"]) == (
        "official_feed",
        90,
        100_000,
        players[7],
    )
    stats = (await api.get(f"/v1/orgs/{org}/matches/{m}/stats")).json()
    assert (
        stats["own"]["goals"] == 2
        and stats["own"]["seven_m_goals"] == 1
        and stats["own"]["suspensions"] == 1
    )
    j = json.dumps(
        {"events": [{"period": 2, "clock": "31:00", "team": "own", "event": "goal", "number": 7}]}
    )
    r = await api.post(
        f"/v1/orgs/{org}/matches/{m}/events/import",
        files={"file": ("f.json", j.encode(), "application/json")},
    )
    assert r.json()["created"] == 1
    bad = await api.post(
        f"/v1/orgs/{org}/matches/{m}/events/import",
        files={"file": ("f.json", b"{nope", "application/json")},
    )
    assert bad.status_code == 422


REPORT = {
    "schema": "handball-paper-report/1",
    "date": "2026-09-20",
    "kickoff": "17:30",
    "opponent": "TV Papier",
    "home": False,
    "competition": "3. Liga",
    "score": {"own": 6, "opponent": 4},
    "halftime": {"own": 3, "opponent": 2},
    "players": [
        {
            "number": 7,
            "goals": 3,
            "misses": 2,
            "posts": 1,
            "technical_faults": {"bad_pass": 2},
            "suspensions": 1,
        },
        {"number": 9, "goals": 2, "seven_m_goals": 1, "seven_m_misses": 1, "blocked": 1},
        {"number": 33, "name": "Gast", "misses": 1},
    ],
    "goalkeepers": [{"number": 1, "saves": 8, "goals_against_by_zone": {"TL": [5, 5], "BR": [11]}}],
    "score_progression": [
        {"minute": 5, "own": 1, "opponent": 0},
        {"minute": 60, "own": 6, "opponent": 4},
    ],
    "tactics_notes": {"back_left": "Nr. 5 wirft immer hoch"},
}


async def test_paper_report_import(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    players = await roster(api, ids)
    org = ids["org"]
    url = f"/v1/orgs/{org}/teams/{ids['team']}/paper-reports"
    r = await api.post(
        url, files={"file": ("r.json", json.dumps(REPORT).encode(), "application/json")}
    )
    assert r.status_code == 201, r.text
    res = r.json()
    assert res["warnings"] == ["numbers not in the roster: [33]"]
    match = (await api.get(f"/v1/orgs/{org}/matches/{res['match_id']}")).json()
    assert (match["source"], match["status"], match["is_home"]) == ("paper_report", "ready", False)
    assert match["report_extra"]["tactics_notes"]["back_left"].startswith("Nr. 5")
    stats = (await api.get(f"/v1/orgs/{org}/matches/{res['match_id']}/stats")).json()
    own = stats["own"]
    assert own["goals"] == 6 and own["shots_blocked"] == 1 and own["seven_m_shots"] == 2
    assert own["turnovers_by_type"] == {"bad_pass": 2}
    assert own["saves"] == 8 and own["goals_against"] == 4
    assert own["save_pct"] == pytest.approx(8 / 12, abs=1e-4)
    assert stats["opponent"]["goal_zones"]["TL"] == {"shots": 2, "goals": 2}
    assert stats["players"][f"p:{players[1]}"]["saves"] == 8
    assert stats["players"]["opponent#5"]["goals"] == 2
    lst = (await api.get(f"/v1/orgs/{org}/teams/{ids['team']}/matches")).json()
    assert lst[0]["opponent_name"] == "TV Papier"
    for bad in (
        {**REPORT, "schema": "x"},
        {**REPORT, "players": [{"number": 7, "technical_faults": {"fly": 1}}]},
    ):
        r = await api.post(
            url, files={"file": ("r.json", json.dumps(bad).encode(), "application/json")}
        )
        assert r.status_code == 422
    mismatch = {**REPORT, "score": {"own": 9, "opponent": 4}}
    r = await api.post(
        url, files={"file": ("r.json", json.dumps(mismatch).encode(), "application/json")}
    )
    assert any("differ from the final score" in w for w in r.json()["warnings"])
