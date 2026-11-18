"""The goalkeeper module is part of Team and Verein, not of the free plan (owner decision
18.11.2026, reverses A9's "in every plan"): the figures per goalkeeper, the keeper card of the
scouting report and the shot export for the goalkeeper trainer need the plan feature
`goalkeepers`. Marking who keeps goal and recording saves stay in every plan (data entry)."""

from __future__ import annotations

import dataclasses
from collections.abc import Callable, Iterator
from typing import Any

import asyncpg
import pytest
from fastapi import FastAPI

from handball_api.models.enums import Plan
from handball_api.services.plans import PLANS

from .conftest import Api, setup_club
from .test_matches import new_match
from .test_roster import roster_url

pytestmark = pytest.mark.usefixtures("clean_db")


@pytest.fixture
def enforce(db_app: FastAPI) -> Iterator[None]:
    s = db_app.state.settings
    old = s.billing_enforce
    s.billing_enforce = True
    yield
    s.billing_enforce = old


def test_goalkeepers_only_from_team() -> None:
    assert "goalkeepers" not in PLANS[Plan.FREE].features
    assert "goalkeepers" in PLANS[Plan.TEAM].features
    assert "goalkeepers" in PLANS[Plan.CLUB].features


async def _keeper_match(api: Api, ids: dict[str, str]) -> tuple[str, str]:
    """A played match with two saves and a goal against, credited to the marked keeper."""
    org = ids["org"]
    entry = (
        await api.post(
            roster_url(ids), json={"first_name": "Mia", "last_name": "Probst", "jersey_number": 1}
        )
    ).json()
    # marking who keeps goal is data entry: every plan
    r = await api.patch(
        f"/v1/orgs/{org}/teams/{ids['team']}/roster/{entry['id']}", json={"main_position": "TW"}
    )
    assert r.status_code == 200, r.text
    m = (await new_match(api, ids, kickoff_at="2026-09-05T18:00:00+02:00"))["id"]
    keeper = {"goalkeeper_id": entry["player_id"]}
    for clock, outcome in ((100, "save"), (200, "save"), (300, "goal")):
        # recording saves is data entry too
        r = await api.post(
            f"/v1/orgs/{org}/matches/{m}/events",
            json={
                "type": "shot",
                "side": "opponent",
                "outcome": outcome,
                "clock_s": clock,
                "goal_zone": "TL",
                "attributes": keeper,
            },
        )
        assert r.status_code == 201, r.text
    r = await api.post(
        f"/v1/orgs/{org}/matches/{m}/events",
        json={"type": "shot", "side": "own", "outcome": "goal", "clock_s": 400},
    )
    assert r.status_code == 201, r.text
    r = await api.patch(f"/v1/orgs/{org}/matches/{m}", json={"score_own": 1, "score_opponent": 1})
    assert r.status_code == 200, r.text
    return m, str(entry["player_id"])


def _keeper(stats: dict[str, Any], pid: str) -> dict[str, Any]:
    return dict(stats["goalkeepers"][f"own:p:{pid}"])


@pytest.mark.usefixtures("enforce")
async def test_free_plan_has_no_goalkeeper_figures_team_has(
    make_api: Callable[[], Api], owner_conn: asyncpg.Connection
) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    m, pid = await _keeper_match(api, ids)

    # free: the club knows it has no goalkeeper module
    assert "goalkeepers" not in (await api.get(f"/v1/orgs/{org}")).json()["features"]
    # the match statistics keep their shape, the figures per goalkeeper are empty; the team's
    # saves stay (like the score)
    stats = (await api.get(f"/v1/orgs/{org}/matches/{m}/stats")).json()
    assert stats["goalkeepers"] == {}
    assert (stats["own"]["saves"], stats["own"]["goals_against"]) == (2, 1)
    # the saves stay readable as events (scenes, clips)
    saves = (
        await api.get(
            f"/v1/orgs/{org}/matches/{m}/events",
            params={"side": "opponent", "outcome": "save"},
        )
    ).json()
    assert len(saves) == 2
    # the dedicated goalkeeper endpoints refuse
    r = await api.get(f"/v1/orgs/{org}/matches/{m}/exports/shots")
    assert r.status_code == 402 and r.json()["type"].endswith("plan-required")
    rep = await api.post(f"/v1/orgs/{org}/matches/{m}/scouting")
    assert rep.status_code == 201, rep.text
    rid = rep.json()["id"]
    r = await api.get(f"/v1/orgs/{org}/scouting/{rid}/goalkeeper-card")
    assert r.status_code == 402 and r.json()["type"].endswith("plan-required")
    # the preparation report itself is no goalkeeper function
    assert (await api.get(f"/v1/orgs/{org}/scouting/{rid}/pdf")).status_code == 200

    # Team: the goalkeeper figures
    await owner_conn.execute(
        "UPDATE organizations SET plan = 'team', subscription_status = 'active'"
    )
    assert "goalkeepers" in (await api.get(f"/v1/orgs/{org}")).json()["features"]
    stats = (await api.get(f"/v1/orgs/{org}/matches/{m}/stats")).json()
    k = _keeper(stats, pid)
    assert (k["faced"], k["saves"], k["goals_against"]) == (3, 2, 1)
    assert k["goal_zones"]["TL"] == {"faced": 3, "saves": 2}
    export = await api.get(f"/v1/orgs/{org}/matches/{m}/exports/shots")
    assert export.status_code == 200 and len(export.json()["shots"]) == 4
    card = await api.get(f"/v1/orgs/{org}/scouting/{rid}/goalkeeper-card")
    assert card.status_code == 200 and card.content.startswith(b"%PDF")
    season = f"/v1/orgs/{org}/teams/{ids['team']}/seasons/{ids['season']}"
    line = (await api.get(f"{season}/players/{pid}/line")).json()
    assert (line["totals"]["saves"], line["totals"]["faced"]) == (2, 3)
    players = (await api.get(f"{season}/stats")).json()["players"]
    assert next(p for p in players if p["player_id"] == pid)["saves"] == 2


@pytest.mark.usefixtures("enforce")
async def test_season_figures_without_the_goalkeeper_module(
    make_api: Callable[[], Api], owner_conn: asyncpg.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A plan with the season statistics but without the goalkeeper module: the season line and
    the season statistics keep their shape, the goalkeeper's figures are empty."""
    team = PLANS[Plan.TEAM]
    monkeypatch.setitem(
        PLANS,
        Plan.TEAM,
        dataclasses.replace(team, features=team.features - {"goalkeepers"}),
    )
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    m, pid = await _keeper_match(api, ids)
    await owner_conn.execute(
        "UPDATE organizations SET plan = 'team', subscription_status = 'active'"
    )
    season = f"/v1/orgs/{org}/teams/{ids['team']}/seasons/{ids['season']}"
    line = (await api.get(f"{season}/players/{pid}/line")).json()
    one = line["matches"][0]
    assert one["match_id"] == m and one["involved"]  # whether she played stays
    for key in ("faced", "saves", "goals_against", "seven_m_faced", "seven_m_saves"):
        assert one["figures"][key] == 0 and one["events"][key] == [] and line["totals"][key] == 0
    assert one["save_pct"] is None and line["totals"]["save_pct"] is None
    data = (await api.get(f"{season}/stats")).json()
    assert next(p for p in data["players"] if p["player_id"] == pid)["saves"] is None
    assert data["totals"]["saves"] == 2  # the team's figure stays


@pytest.mark.usefixtures("enforce")
async def test_public_profile_shows_saves_only_with_the_goalkeeper_module(
    make_api: Callable[[], Api], owner_conn: asyncpg.Connection
) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    entry = (
        await api.post(
            roster_url(ids),
            json={
                "first_name": "Mia",
                "last_name": "Probst",
                "jersey_number": 1,
                "birth_year": 1998,
            },
        )
    ).json()
    pid = entry["player_id"]
    user_id = await owner_conn.fetchval("SELECT id FROM users LIMIT 1")
    await owner_conn.execute("UPDATE players SET user_id = $1 WHERE id = $2::uuid", user_id, pid)
    r = await api.post(f"/v1/orgs/{org}/me/consents/{pid}", json={"kind": "public_profile"})
    assert r.status_code == 201, r.text
    r = await api.put(
        f"/v1/orgs/{org}/players/{pid}/profile", json={"active": True, "stats": ["saves"]}
    )
    assert r.status_code == 200, r.text
    slug = r.json()["slug"]
    m = await new_match(api, ids)
    r = await api.post(
        f"/v1/orgs/{org}/matches/{m['id']}/events",
        json={
            "type": "shot",
            "side": "opponent",
            "outcome": "save",
            "attributes": {"goalkeeper_id": pid},
        },
    )
    assert r.status_code == 201, r.text
    anon = make_api()
    assert (await anon.get(f"/v1/public/profiles/{slug}")).json()["stats"] == {"saves": None}
    await owner_conn.execute(
        "UPDATE organizations SET plan = 'team', subscription_status = 'active'"
    )
    assert (await anon.get(f"/v1/public/profiles/{slug}")).json()["stats"] == {"saves": 1}
