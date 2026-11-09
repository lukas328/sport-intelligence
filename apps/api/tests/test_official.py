"""Clubs and teams from the official league data (docs/plans/federation-onboarding.md).

The network is never used: handball.ch answers come from tests/fixtures/handball_ch, recorded
from the real match centre (TV Thalwil, men's 2nd league, season 2026/27) with pseudonymised
player names. Tests change copies of them to simulate moved games, new players or a new season.
"""

from __future__ import annotations

import asyncio
import copy
import json
import re
from collections.abc import Callable, Iterator
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import asyncpg
import httpx
import pytest
from fastapi import FastAPI

from handball_api.core.email import MemoryEmailSender
from handball_api.core.errors import ProblemError
from handball_api.core.ratelimit import MemoryRateLimiter
from handball_api.integrations import handball_ch
from handball_api.services import official_report

from .conftest import Api, setup_club

pytestmark = pytest.mark.usefixtures("clean_db")

FIXTURES = Path(__file__).parent / "fixtures" / "handball_ch"
CLUB, TEAM, GROUP = 140371, 40742, 17627
PLAYERS = 23  # registered players of the team in the fixture
PLAYED = 8  # played games of the season in the fixture
GAMES = 21


def _key(operation: str, variables: dict[str, Any]) -> str:
    return json.dumps(
        [operation, {k: v for k, v in variables.items() if k != "isLive"}], sort_keys=True
    )


class Recorded:
    """Answers handball.ch requests from the recorded fixtures."""

    def __init__(self) -> None:
        self.answers: dict[str, dict[str, Any]] = {}
        for f in sorted(FIXTURES.glob("*.json")):
            r = json.loads(f.read_text())
            self.answers[_key(r["operation"], r["variables"])] = r["response"]
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.down = False

    def data(self, operation: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        d: dict[str, Any] = copy.deepcopy(self.answers[_key(operation, variables or {})]["data"])
        return d

    def set(self, operation: str, variables: dict[str, Any], data: dict[str, Any]) -> None:
        self.answers[_key(operation, variables)] = {"data": data}

    def handler(self, request: httpx.Request) -> httpx.Response:
        assert request.url.host == "www.handball.ch"  # fixed host only
        body = json.loads(request.content)
        op = re.search(r"query\s+(\w+)", body["query"])
        assert op
        variables = body.get("variables") or {}
        self.calls.append((op.group(1), variables))
        if self.down:
            return httpx.Response(503)
        found = self.answers.get(_key(op.group(1), variables))
        if found is not None:
            return httpx.Response(200, json=found)
        if op.group(1) == "getReport":
            return httpx.Response(200, json={"data": {"game": [], "gameLog": []}})
        if op.group(1) == "getGamePlayers":
            return httpx.Response(200, json={"data": {"gamePlayerStats": []}})
        return httpx.Response(404)  # not recorded: never the network


@pytest.fixture(autouse=True)
def hch() -> Iterator[Recorded]:
    rec = Recorded()
    handball_ch.set_transport(httpx.MockTransport(rec.handler))
    yield rec
    handball_ch.set_transport(None)


async def coach(make_api: Callable[[], Api], email: str = "coach@tvt-handball.ch") -> Api:
    api = make_api()
    api.app.state.rate_limiter = MemoryRateLimiter()
    assert (await api.register(email, name="Coach Carter")).status_code == 201
    return api


async def claim(api: Api, team: int = TEAM, **body: Any) -> dict[str, Any]:
    r = await api.post(f"/v1/official/teams/{team}/claim", json={"club_id": CLUB, **body})
    assert r.status_code in (200, 201, 202), r.text
    out: dict[str, Any] = r.json()
    out["_status"] = r.status_code
    return out


def base(c: dict[str, Any]) -> str:
    return f"/v1/orgs/{c['organization_id']}/teams/{c['team_id']}"


async def suggestions(api: Api, c: dict[str, Any], kind: str | None = None) -> list[Any]:
    r = await api.get(base(c) + "/official/suggestions", params={"kind": kind} if kind else {})
    assert r.status_code == 200, r.text
    rows: list[Any] = r.json()
    return rows


async def invite(
    admin: Api, make_api: Callable[[], Api], outbox: MemoryEmailSender, c: dict[str, Any], role: str
) -> Api:
    email = f"{role}@example.org"
    r = await admin.post(
        f"/v1/orgs/{c['organization_id']}/invitations",
        json={"email": email, "team_id": c["team_id"], "team_role": role},
    )
    assert r.status_code == 201, r.text
    token = re.search(r"/invite/([\w-]+)", outbox.outbox[-1].text)
    assert token
    api = make_api()
    api.app.state.rate_limiter = MemoryRateLimiter()
    assert (await api.register(email, invitation_token=token.group(1))).status_code == 201
    return api


# ---- client ------------------------------------------------------------------------------------


async def test_client_parses_caches_and_rests_after_errors(hch: Recorded) -> None:
    season = await handball_ch.current_season(None)
    assert (season.id, season.label, season.current) == (2026, "2026/27", True)
    detail = await handball_ch.club(None, CLUB, 2026)
    assert detail is not None
    assert detail.website == "https://www.tvt-handball.ch/"
    assert handball_ch.mail_domains(detail) == ["tvt-handball.ch"]
    first = next(t for t in detail.teams if t.id == TEAM)
    assert (first.name, first.league, first.group_id) == ("TV Thalwil", "Männer 2. Liga", GROUP)
    games = await handball_ch.team_games(None, TEAM)
    assert len(games) == GAMES and sum(g.played for g in games) == PLAYED
    g = next(g for g in games if g.id == 509192)
    assert (g.home_name, g.away_name, g.home_score, g.away_score) == (
        "TV Thalwil",
        "Grün-Weiss Effretikon 1",
        26,
        19,
    )
    assert g.kickoff_at.isoformat() == "2026-09-27T17:00:00+02:00"  # Swiss local time
    assert g.venue == "Thalwil Sonnenberg"
    # team officials (placeholder ids shared across teams) are not players
    appearances = await handball_ch.game_players(None, 509192)
    assert appearances and all(a.player_id < 10_000_000 for a in appearances)

    # after an error nothing is sent for a while, then it works again
    hch.down = True
    calls = len(hch.calls)
    with pytest.raises(handball_ch.UpstreamUnavailableError):
        await handball_ch.standing(None, GROUP)
    with pytest.raises(handball_ch.UpstreamUnavailableError):
        await handball_ch.standing(None, GROUP)
    assert len(hch.calls) == calls + 1
    hch.down = False
    handball_ch.set_transport(httpx.MockTransport(hch.handler))
    assert (await handball_ch.standing(None, GROUP))[0]["rank"] == 1

    # the report import of a single game goes through the same client
    report = official_report.parse_handball_ch(
        509192, await official_report.fetch_handball_ch(509192)
    )
    assert report.final == (26, 19) and report.entries
    hch.down = True
    handball_ch.set_transport(httpx.MockTransport(hch.handler))
    with pytest.raises(ProblemError) as err:
        await official_report.fetch_handball_ch(509192)
    assert err.value.code == "report-unavailable"


# ---- search ------------------------------------------------------------------------------------


async def test_search_lists_registered_teams(make_api: Callable[[], Api], hch: Recorded) -> None:
    api = await coach(make_api)
    r = await api.get("/v1/official/teams", params={"q": "thalwil"})
    assert r.status_code == 200, r.text
    hits = r.json()
    first = next(h for h in hits if h["official_id"] == TEAM)
    assert first["name"] == "TV Thalwil"
    assert first["league"] == "Männer 2. Liga"
    assert first["club"] == {"id": CLUB, "name": "TV Thalwil", "city": "Thalwil"}
    assert first["status"] == "available" and first["team_id"] is None
    assert len(hits) >= 5  # men, women, youth teams of the club
    # the answers are cached: a second search does not ask handball.ch again
    calls = len(hch.calls)
    assert (await api.get("/v1/official/teams", params={"q": "Thalwil"})).status_code == 200
    assert len(hch.calls) == calls
    assert (await api.get("/v1/official/teams", params={"q": "zzzzqqq"})).json() == []
    r = await api.get("/v1/official/teams", params={"q": "th"})
    assert r.status_code == 422 and r.json()["type"].endswith("query-too-short")
    anon = make_api()
    assert (await anon.get("/v1/official/teams", params={"q": "thalwil"})).status_code == 401


async def test_search_when_handball_ch_is_down(make_api: Callable[[], Api], hch: Recorded) -> None:
    api = await coach(make_api)
    hch.down = True
    r = await api.get("/v1/official/teams", params={"q": "thalwil"})
    assert r.status_code == 503 and r.json()["type"].endswith("official-unavailable")


# ---- claim and prefill -------------------------------------------------------------------------


async def test_claim_creates_club_and_team_and_prefills(
    make_api: Callable[[], Api], owner_conn: asyncpg.Connection
) -> None:
    api = await coach(make_api)
    c = await claim(api, team_name="Herren 1")
    assert c["_status"] == 201
    assert c["status"] == "claimed" and c["created_organization"] is True
    assert c["verification"] == "unverified"
    assert c["prefill"]["matches_created"] == GAMES
    assert c["prefill"]["matches_held_back"] == 0  # no plan limit without billing enforcement
    assert c["prefill"]["results"] == PLAYED
    assert c["prefill"]["roster_suggestions"] == PLAYERS
    assert c["prefill"]["report_suggestions"] == PLAYED

    org = (await api.get(f"/v1/orgs/{c['organization_id']}")).json()
    assert (org["name"], org["official_club_id"], org["verification"]) == (
        "TV Thalwil",
        CLUB,
        "unverified",
    )
    team = (await api.get(base(c))).json()
    assert team["name"] == "Herren 1" and team["official_team_id"] == TEAM
    assert team["league"] == "Männer 2. Liga" and team["gender"] == "men"
    assert team["my_role"] == "coach" and team["current_season"]["label"] == "2026/27"

    matches = (await api.get(base(c) + "/matches")).json()
    assert len(matches) == GAMES
    m = next(x for x in matches if x["kickoff_at"].startswith("2026-09-27"))
    assert m["opponent_name"] == "Grün-Weiss Effretikon 1"
    assert m["is_home"] is True and (m["score_own"], m["score_opponent"]) == (26, 19)
    assert m["kickoff_at"].startswith("2026-09-27T15:00:00")
    away = [x for x in matches if x["opponent_name"] == "SG Horgen/Wädenswil 1"]
    assert {x["is_home"] for x in away} == {True, False}
    row = await owner_conn.fetchrow(
        "SELECT venue, official_game_id, source FROM matches WHERE id = $1::uuid", m["id"]
    )
    assert dict(row) == {
        "venue": "Thalwil Sonnenberg",
        "official_game_id": 509192,
        "source": "official",
    }

    link = (await api.get(base(c) + "/official")).json()
    assert link["linked"] is True and link["official_group_id"] == GROUP
    assert link["standing"][0]["rank"] == 1 and len(link["standing"]) >= 10
    assert link["open_suggestions"] == PLAYERS + PLAYED

    roster = await suggestions(api, c, "roster_add")
    luca = next(s for s in roster if s["payload"]["first_name"] == "Luca")
    assert luca["payload"] == {
        "official_player_id": 329985,
        "first_name": "Luca",
        "last_name": "Muster",
        "jersey_number": 55,
        "appearances": 7,
        # the recorded answers have goals only; the other statistics are None (not available)
        "stats": {
            "games": 7,
            "goals": 5,
            "goals_7m": None,
            "attempts_7m": None,
            "suspensions_2min": None,
            "goalkeeper": False,
            "saves": None,
            "shots_faced": None,
        },
    }
    reports = await suggestions(api, c, "report")
    assert {s["payload"]["game_id"] for s in reports} >= {509192, 509203}
    # nothing is on the roster before the coach confirms
    season = team["current_season"]["id"]
    assert (await api.get(base(c) + f"/seasons/{season}/roster")).json() == []
    actions = {r["action"] for r in await owner_conn.fetch("SELECT action FROM audit_logs")}
    assert {"org.created", "team.created", "official.team_claimed"} <= actions

    # claiming again: already a member
    again = await claim(api)
    assert (again["_status"], again["status"], again["team_id"]) == (
        200,
        "already_member",
        c["team_id"],
    )
    # a team that does not belong to the club
    r = await api.post("/v1/official/teams/1/claim", json={"club_id": CLUB})
    assert r.status_code == 404 and r.json()["type"].endswith("official-team-not-found")


async def test_claim_links_an_existing_club_of_mine(
    make_api: Callable[[], Api], hch: Recorded
) -> None:
    api = make_api()
    ids = await setup_club(api)
    hch.set("getTeamGames", {"teamId": TEAM}, {"games": []})
    c = await claim(api, org_id=ids["org"])
    assert c["status"] == "claimed" and c["created_organization"] is False
    assert c["organization_id"] == ids["org"]
    org = (await api.get(f"/v1/orgs/{ids['org']}")).json()
    assert (org["official_club_id"], org["verification"]) == (CLUB, "unverified")


async def test_simultaneous_claims_one_wins_one_asks(
    make_api: Callable[[], Api], hch: Recorded
) -> None:
    a = await coach(make_api)
    b = await coach(make_api, "other@example.org")
    first, second = await asyncio.gather(claim(a), claim(b))
    assert sorted(x["status"] for x in (first, second)) == ["access_requested", "claimed"]


async def test_duplicate_claim_becomes_access_request(
    make_api: Callable[[], Api], hch: Recorded
) -> None:
    first = await coach(make_api)
    c = await claim(first)
    second = await coach(make_api, "other@example.org")
    hit = next(
        h
        for h in (await second.get("/v1/official/teams", params={"q": "thalwil"})).json()
        if h["official_id"] == TEAM
    )
    assert hit["status"] == "claimed" and hit["team_id"] == c["team_id"]
    assert hit["organization_id"] is None  # not their club
    req = await claim(second, message="Ich bin Co-Trainer")
    assert (req["_status"], req["status"]) == (202, "access_requested")
    # another team of the same club: the club is taken too, one pending request
    other = await claim(second, team=41042)
    assert other["status"] == "access_requested"
    assert other["access_request_id"] == req["access_request_id"]
    mine = (await second.get("/v1/me/access-requests")).json()
    assert [(m["organization_name"], m["status"]) for m in mine] == [("TV Thalwil", "pending")]
    # still only one organisation for the club, and the second person is not in it yet
    assert (await second.get("/v1/me")).json()["organizations"] == []

    org = c["organization_id"]
    pending = (await first.get(f"/v1/orgs/{org}/access-requests")).json()
    assert [(p["email"], p["official_team_id"]) for p in pending] == [("other@example.org", TEAM)]
    assert pending[0]["team_id"] == c["team_id"]
    r = await first.post(
        f"/v1/orgs/{org}/access-requests/{pending[0]['id']}/approve",
        json={"team_role": "coach"},
    )
    assert r.status_code == 200, r.text
    assert (await second.get(base(c))).json()["my_role"] == "coach"
    assert (await first.get(f"/v1/orgs/{org}/access-requests")).json() == []
    r = await first.post(f"/v1/orgs/{org}/access-requests/{pending[0]['id']}/decline")
    assert r.status_code == 409


async def test_access_request_for_a_new_team_creates_it(
    make_api: Callable[[], Api], hch: Recorded
) -> None:
    hch.set("getTeamGames", {"teamId": 41042}, {"games": []})
    hch.set("getTeamPlayers", {"teamId": 41042}, {"playerStaff": []})
    hch.set("getStanding", {"groupId": 17514}, {"standing": []})
    first = await coach(make_api)
    c = await claim(first)
    second = await coach(make_api, "two@example.org")
    req = await claim(second, team=41042)
    org = c["organization_id"]
    r = await first.post(f"/v1/orgs/{org}/access-requests/{req['access_request_id']}/approve")
    assert r.status_code == 200, r.text
    team_id = r.json()["team_id"]
    team = (await second.get(f"/v1/orgs/{org}/teams/{team_id}")).json()
    assert (team["official_team_id"], team["my_role"], team["name"]) == (
        41042,
        "coach",
        "TV Thalwil 2",
    )
    # a declined request
    third = await coach(make_api, "three@example.org")
    req = await claim(third)
    r = await first.post(f"/v1/orgs/{org}/access-requests/{req['access_request_id']}/decline")
    assert r.status_code == 200 and r.json()["status"] == "declined"
    assert (await third.get(base(c))).status_code == 404


# ---- suggestions -------------------------------------------------------------------------------


async def test_accept_roster_and_report_suggestions(
    make_api: Callable[[], Api], owner_conn: asyncpg.Connection
) -> None:
    api = await coach(make_api)
    c = await claim(api)
    roster = {s["payload"]["first_name"]: s for s in await suggestions(api, c, "roster_add")}
    r = await api.post(base(c) + f"/official/suggestions/{roster['Luca']['id']}/accept")
    assert r.status_code == 200, r.text
    assert r.json()["suggestion"]["status"] == "accepted" and r.json()["player_id"]
    r = await api.post(
        base(c) + f"/official/suggestions/{roster['Noah']['id']}/accept",
        json={"jersey_number": 9},
    )
    assert r.status_code == 200, r.text
    # Yves and Silvan both wore 15: the second one gets no number
    for name in ("Yves", "Silvan"):
        assert (
            await api.post(base(c) + f"/official/suggestions/{roster[name]['id']}/accept")
        ).status_code == 200
    r = await api.post(base(c) + f"/official/suggestions/{roster['Leon']['id']}/dismiss")
    assert r.status_code == 200 and r.json()["status"] == "dismissed"
    r = await api.post(base(c) + f"/official/suggestions/{roster['Leon']['id']}/accept")
    assert r.status_code == 409 and r.json()["type"].endswith("suggestion-resolved")

    team = (await api.get(base(c))).json()
    entries = (await api.get(base(c) + f"/seasons/{team['current_season']['id']}/roster")).json()
    numbers = {e["first_name"]: e["jersey_number"] for e in entries}
    assert numbers == {"Luca": 55, "Noah": 9, "Yves": 15, "Silvan": None}
    assert len(await suggestions(api, c, "roster_add")) == PLAYERS - 5

    # a past game's report: the official log becomes events; opponent names stay out while the
    # club is not verified (numbers only)
    report = next(
        s for s in await suggestions(api, c, "report") if s["payload"]["game_id"] == 509192
    )
    r = await api.post(base(c) + f"/official/suggestions/{report['id']}/accept")
    assert r.status_code == 200, r.text
    assert r.json()["report"]["created"] > 40
    match_id = r.json()["match_id"]
    rows = await owner_conn.fetch(
        "SELECT side, number, attributes FROM events WHERE match_id = $1::uuid "
        "AND source = 'official_report'",
        match_id,
    )
    named = {(r["side"], "name" in json.loads(r["attributes"])) for r in rows}
    assert ("own", True) in named and ("opponent", True) not in named
    assert any(r["side"] == "opponent" and r["number"] for r in rows)
    imported = await owner_conn.fetchval(
        "SELECT official_report_at IS NOT NULL FROM matches WHERE id = $1::uuid", match_id
    )
    assert imported is True


async def test_roster_from_official_data_hidden_until_join_or_consent(
    make_api: Callable[[], Api], outbox: MemoryEmailSender
) -> None:
    api = await coach(make_api)
    c = await claim(api)
    roster = {s["payload"]["first_name"]: s for s in await suggestions(api, c, "roster_add")}
    luca = (await api.post(base(c) + f"/official/suggestions/{roster['Luca']['id']}/accept")).json()
    team = (await api.get(base(c))).json()
    season = team["current_season"]["id"]
    manual = await api.post(
        base(c) + f"/seasons/{season}/roster", json={"first_name": "Hand", "last_name": "Erfasst"}
    )
    assert manual.status_code == 201
    player = await invite(api, make_api, outbox, c, "player")
    seen = {
        e["first_name"] for e in (await player.get(base(c) + f"/seasons/{season}/roster")).json()
    }
    assert seen == {"Hand"}  # the official entry stays with the coach
    assert {
        e["first_name"] for e in (await api.get(base(c) + f"/seasons/{season}/roster")).json()
    } == {
        "Hand",
        "Luca",
    }
    # player suggestions are not for players
    assert (await player.get(base(c) + "/official/suggestions")).status_code == 403
    # with a consent the entry is visible to the team
    r = await api.post(
        base(c) + f"/players/{luca['player_id']}/consents",
        json={
            "kind": "analysis",
            "given_by": "self",
            "given_by_name": "Luca Muster",
            "given_at": "2026-11-01T10:00:00+01:00",
        },
    )
    assert r.status_code == 201, r.text
    seen = {
        e["first_name"] for e in (await player.get(base(c) + f"/seasons/{season}/roster")).json()
    }
    assert seen == {"Hand", "Luca"}


async def test_roster_suggestions_carry_official_statistics(
    make_api: Callable[[], Api], hch: Recorded, outbox: MemoryEmailSender
) -> None:
    # the recorded answers predate the statistic fields: add them to every played game
    for f in FIXTURES.glob("getGamePlayers_*.json"):
        game = {"gameId": int(f.stem.split("_")[1])}
        data = hch.data("getGamePlayers", game)
        for p in data["gamePlayerStats"]:
            if p["teamId"] != TEAM:
                continue
            if p["playerName"] == "MUSTER Simon":
                p.update(totalScore7m=2, totalShots7m=3, total2Minutes=1)
            elif p["function"] == "goalkeeper":
                p.update(totalScore7m=0, totalShots7m=0, total2Minutes=0)
                p.update(totalSaves=5, totalShotsGK=20)
            else:
                p.update(totalScore7m=0, totalShots7m=0, total2Minutes=0, totalSaves=0)
        hch.set("getGamePlayers", game, data)
    api = await coach(make_api)
    c = await claim(api)
    roster = {
        s["payload"]["first_name"]: s["payload"] for s in await suggestions(api, c, "roster_add")
    }
    assert len(roster) == PLAYERS
    # name, number and appearances as before, the statistics next to them
    simon = roster["Simon"]
    assert simon["appearances"] == 8 and simon["jersey_number"] is not None
    assert simon["stats"] == {
        "games": 8,
        "goals": 39,
        "goals_7m": 16,
        "attempts_7m": 24,
        "suspensions_2min": 8,
        "goalkeeper": False,
        "saves": None,  # field players: no keeper statistics
        "shots_faced": None,
    }
    # goalkeepers: saves and shots faced (Elias kept goal in 6 of his 7 games)
    assert roster["Leon"]["stats"] == {
        "games": 7,
        "goals": 2,
        "goals_7m": 0,
        "attempts_7m": 0,
        "suspensions_2min": 0,
        "goalkeeper": True,
        "saves": 35,
        "shots_faced": 140,
    }
    elias = roster["Elias"]["stats"]
    assert (elias["games"], elias["goalkeeper"], elias["saves"], elias["shots_faced"]) == (
        7,
        True,
        30,
        120,
    )
    # registered but no game yet: no statistics
    assert all(p["stats"] is None for p in roster.values() if p["appearances"] == 0)

    # show or hide: the organisers' choice is kept per team (display only, the data is there)
    link = (await api.get(base(c) + "/official")).json()
    assert link["roster_stats"] is False
    r = await api.patch(base(c) + "/official", json={"roster_stats": True})
    assert r.status_code == 200, r.text
    assert r.json()["roster_stats"] is True and r.json()["linked"] is True
    assert (await api.get(base(c) + "/official")).json()["roster_stats"] is True

    # data protection: names and statistics only for organisers
    player = await invite(api, make_api, outbox, c, "player")
    assert (await player.get(base(c) + "/official/suggestions")).status_code == 403
    r = await player.patch(base(c) + "/official", json={"roster_stats": False})
    assert r.status_code == 403
    other = make_api()
    await setup_club(other, "coach@other-club.ch")
    assert (await other.get(base(c) + "/official/suggestions")).status_code == 404
    r = await other.patch(base(c) + "/official", json={"roster_stats": False})
    assert r.status_code == 404


# ---- plan limit --------------------------------------------------------------------------------


@pytest.fixture
def enforce(db_app: FastAPI) -> Iterator[None]:
    s = db_app.state.settings
    old = s.billing_enforce
    s.billing_enforce = True
    yield
    s.billing_enforce = old


@pytest.mark.usefixtures("enforce")
async def test_official_games_count_toward_the_plan_limit(
    make_api: Callable[[], Api], hch: Recorded, owner_conn: asyncpg.Connection
) -> None:
    # the played games and one upcoming game (next week)
    games = hch.data("getTeamGames", {"teamId": TEAM})
    upcoming = next(g for g in games["games"] if g["objectId"] == 509159)
    next_week = datetime.now(handball_ch.TZ) + timedelta(days=7)
    upcoming["gameDateTime"] = next_week.replace(tzinfo=None, microsecond=0).isoformat()
    games["games"] = [g for g in games["games"] if g["gameStatusId"] == 2] + [upcoming]
    hch.set("getTeamGames", {"teamId": TEAM}, games)

    api = await coach(make_api)
    c = await claim(api)
    # free plan, 2 matches per season: the next upcoming game, then the most recent played one
    assert c["prefill"]["matches_created"] == 2
    assert c["prefill"]["matches_held_back"] == PLAYED - 1
    assert c["prefill"]["results"] == 1 and c["prefill"]["report_suggestions"] == 1
    assert c["prefill"]["other_suggestions"] == 0
    rows = await owner_conn.fetch("SELECT official_game_id FROM matches")
    assert {r["official_game_id"] for r in rows} == {509159, 509203}
    held = {s["payload"]["game_id"]: s for s in await suggestions(api, c, "match_new")}
    assert len(held) == PLAYED - 1 and 509192 in held
    assert {(s["payload"]["reason"], s["blocked"]) for s in held.values()} == {
        ("plan_limit", "plan_limit")
    }
    assert all(s["blocked"] is None for s in await suggestions(api, c, "roster_add"))
    # accepting one, or a match by hand, is over the limit too
    r = await api.post(base(c) + f"/official/suggestions/{held[509192]['id']}/accept")
    assert r.status_code == 402 and r.json()["type"].endswith("plan-limit-matches")
    r = await api.post(
        base(c) + "/matches",
        json={"opponent_name": "Dritter", "kickoff_at": "2026-12-20T18:00:00+01:00"},
    )
    assert r.status_code == 402 and r.json()["type"].endswith("plan-limit-matches")
    # a sync keeps them as they are (reason and all), nothing new
    r = await api.post(base(c) + "/official/sync")
    assert r.status_code == 200, r.text
    assert (r.json()["other_suggestions"], r.json()["matches_held_back"]) == (0, 0)
    assert all(
        s["payload"]["reason"] == "plan_limit" for s in await suggestions(api, c, "match_new")
    )

    # after an upgrade the held-back games can be taken over: result and report come along
    await owner_conn.execute(
        "UPDATE organizations SET plan = 'team', subscription_status = 'active'"
    )
    held = {s["payload"]["game_id"]: s for s in await suggestions(api, c, "match_new")}
    assert all(s["blocked"] is None for s in held.values())
    r = await api.post(base(c) + f"/official/suggestions/{held[509192]['id']}/accept")
    assert r.status_code == 200, r.text
    match = (
        await api.get(f"/v1/orgs/{c['organization_id']}/matches/{r.json()['match_id']}")
    ).json()
    assert (match["score_own"], match["score_opponent"]) == (26, 19)
    report = next(
        s for s in await suggestions(api, c, "report") if s["payload"]["game_id"] == 509192
    )
    assert "reason" not in report["payload"]
    r = await api.post(base(c) + f"/official/suggestions/{report['id']}/accept")
    assert r.status_code == 200, r.text
    assert r.json()["report"]["created"] > 40


# ---- join requests -----------------------------------------------------------------------------


async def test_join_request_matches_roster_and_coach_approves(
    make_api: Callable[[], Api],
) -> None:
    api = await coach(make_api)
    c = await claim(api)
    roster = {s["payload"]["first_name"]: s for s in await suggestions(api, c, "roster_add")}
    luca = (await api.post(base(c) + f"/official/suggestions/{roster['Luca']['id']}/accept")).json()

    joiner = await coach(make_api, "luca@example.org")
    hit = next(
        h
        for h in (await joiner.get("/v1/official/teams", params={"q": "thalwil"})).json()
        if h["official_id"] == TEAM
    )
    r = await joiner.post(
        f"/v1/teams/{hit['team_id']}/join-requests",
        json={"first_name": "Luca", "last_name": "Müster", "jersey_number": 55},
    )
    assert r.status_code == 201, r.text
    req = r.json()
    assert (req["team_name"], req["organization_name"], req["status"]) == (
        "TV Thalwil",
        "TV Thalwil",
        "pending",
    )
    r = await joiner.post(
        f"/v1/teams/{hit['team_id']}/join-requests", json={"first_name": "L", "last_name": "M"}
    )
    assert r.status_code == 409 and r.json()["type"].endswith("join-request-pending")
    # the requester sees nothing of the club yet
    assert (await joiner.get(base(c) + "/join-requests")).status_code == 404

    pending = (await api.get(base(c) + "/join-requests")).json()
    assert len(pending) == 1
    assert pending[0]["email"] == "luca@example.org"
    assert pending[0]["suggested"] == {
        "kind": "player",
        "id": luca["player_id"],
        "first_name": "Luca",
        "last_name": "Muster",
        "jersey_number": 55,
    }
    r = await api.post(base(c) + f"/join-requests/{pending[0]['id']}/approve")
    assert r.status_code == 200, r.text
    assert r.json()["player_id"] == luca["player_id"]

    team = (await joiner.get(base(c))).json()
    assert team["my_role"] == "player"
    entries = (await joiner.get(base(c) + f"/seasons/{team['current_season']['id']}/roster")).json()
    assert [(e["first_name"], e["has_account"]) for e in entries] == [("Luca", True)]
    assert [m["status"] for m in (await joiner.get("/v1/me/join-requests")).json()] == ["approved"]
    r = await joiner.post(
        f"/v1/teams/{hit['team_id']}/join-requests", json={"first_name": "L", "last_name": "M"}
    )
    assert r.status_code == 409 and r.json()["type"].endswith("already-member")


async def test_double_clicks_on_join_and_access_requests_answer_409(
    make_api: Callable[[], Api],
) -> None:
    """Two clicks at the same moment: the first wins, the second answers 409 (not 500 from the
    unique pending request or a duplicate membership)."""
    api = await coach(make_api)
    c = await claim(api)
    joiner = await coach(make_api, "luca@example.org")
    url = f"/v1/teams/{c['team_id']}/join-requests"
    body = {"first_name": "Luca", "last_name": "Müster", "jersey_number": 55}
    created = await asyncio.gather(joiner.post(url, json=body), joiner.post(url, json=body))
    assert sorted(r.status_code for r in created) == [201, 409], [r.text for r in created]
    req = next(r.json() for r in created if r.status_code == 201)
    approve = base(c) + f"/join-requests/{req['id']}/approve"
    decided = await asyncio.gather(api.post(approve), api.post(approve))
    assert sorted(r.status_code for r in decided) == [200, 409], [r.text for r in decided]
    assert (await joiner.get(base(c))).json()["my_role"] == "player"

    second = await coach(make_api, "other@example.org")
    access = await claim(second)
    url = f"/v1/orgs/{c['organization_id']}/access-requests/{access['access_request_id']}/approve"
    decided = await asyncio.gather(
        api.post(url, json={"team_role": "coach"}), api.post(url, json={"team_role": "coach"})
    )
    assert sorted(r.status_code for r in decided) == [200, 409], [r.text for r in decided]
    assert (await second.get(base(c))).json()["my_role"] == "coach"


async def test_join_request_matches_an_open_suggestion(make_api: Callable[[], Api]) -> None:
    api = await coach(make_api)
    c = await claim(api)
    joiner = await coach(make_api, "nico@example.org")
    r = await joiner.post(
        f"/v1/teams/{c['team_id']}/join-requests",
        json={"first_name": "Nico", "last_name": "Muster", "role": "goalkeeper"},
    )
    assert r.status_code == 201, r.text
    pending = (await api.get(base(c) + "/join-requests")).json()
    assert pending[0]["suggested"]["kind"] == "suggestion"
    assert pending[0]["suggested"]["jersey_number"] == 52
    r = await api.post(base(c) + f"/join-requests/{pending[0]['id']}/approve", json={})
    assert r.status_code == 200, r.text
    team = (await joiner.get(base(c))).json()
    assert team["my_role"] == "goalkeeper"
    entries = (await joiner.get(base(c) + f"/seasons/{team['current_season']['id']}/roster")).json()
    assert [(e["first_name"], e["jersey_number"]) for e in entries] == [("Nico", 52)]
    left = {s["payload"]["first_name"] for s in await suggestions(api, c, "roster_add")}
    assert "Nico" not in left

    # no match: a new roster entry from the request; a decline; a withdrawal
    stranger = await coach(make_api, "new@example.org")
    await stranger.post(
        f"/v1/teams/{c['team_id']}/join-requests",
        json={"first_name": "Neu", "last_name": "Zugang", "jersey_number": 52},
    )
    other = await coach(make_api, "no@example.org")
    await other.post(
        f"/v1/teams/{c['team_id']}/join-requests", json={"first_name": "No", "last_name": "Body"}
    )
    late = await coach(make_api, "late@example.org")
    mine = (
        await late.post(
            f"/v1/teams/{c['team_id']}/join-requests",
            json={"first_name": "Late", "last_name": "Comer"},
        )
    ).json()
    assert (await late.delete(f"/v1/me/join-requests/{mine['id']}")).status_code == 204
    pending = {p["first_name"]: p for p in (await api.get(base(c) + "/join-requests")).json()}
    assert set(pending) == {"Neu", "No"} and pending["Neu"]["suggested"] is None
    r = await api.post(base(c) + f"/join-requests/{pending['Neu']['id']}/approve")
    assert r.status_code == 200, r.text
    r = await api.post(base(c) + f"/join-requests/{pending['No']['id']}/decline")
    assert r.status_code == 200 and r.json()["status"] == "declined"
    entries = (await api.get(base(c) + f"/seasons/{team['current_season']['id']}/roster")).json()
    numbers = {e["first_name"]: e["jersey_number"] for e in entries}
    assert numbers == {"Nico": 52, "Neu": None}  # 52 is taken
    assert (await other.get(base(c))).status_code == 404


# ---- permissions -------------------------------------------------------------------------------


async def test_permissions_other_club_player_and_unverified_club(
    make_api: Callable[[], Api],
    outbox: MemoryEmailSender,
    owner_conn: asyncpg.Connection,
    db_app: FastAPI,
) -> None:
    api = await coach(make_api)
    c = await claim(api)
    s = (await suggestions(api, c, "roster_add"))[0]
    jr = await coach(make_api, "join@example.org")
    await jr.post(
        f"/v1/teams/{c['team_id']}/join-requests", json={"first_name": "A", "last_name": "B"}
    )
    request_id = (await api.get(base(c) + "/join-requests")).json()[0]["id"]

    # the coach of another club sees nothing (404, no existence leak)
    other = make_api()
    await setup_club(other, "coach@other-club.ch")
    for path in (
        "/official",
        "/official/suggestions",
        "/join-requests",
    ):
        assert (await other.get(base(c) + path)).status_code == 404, path
    for path in (
        "/official/sync",
        f"/official/suggestions/{s['id']}/accept",
        f"/official/suggestions/{s['id']}/dismiss",
        f"/join-requests/{request_id}/approve",
        f"/join-requests/{request_id}/decline",
    ):
        assert (await other.post(base(c) + path)).status_code == 404, path
    assert (await other.get(f"/v1/orgs/{c['organization_id']}/access-requests")).status_code == 404

    # a player of the team reads the link and standing, but no suggestions or requests
    player = await invite(api, make_api, outbox, c, "player")
    assert (await player.get(base(c) + "/official")).json()["open_suggestions"] == 0
    for path in ("/official/suggestions", "/join-requests"):
        assert (await player.get(base(c) + path)).status_code == 403, path
    for path in (
        "/official/sync",
        f"/official/suggestions/{s['id']}/accept",
        f"/join-requests/{request_id}/approve",
    ):
        assert (await player.post(base(c) + path)).status_code == 403, path
    assert (await player.get(f"/v1/orgs/{c['organization_id']}/access-requests")).status_code == 403
    # a player cannot confirm the club
    r = await player.post(f"/v1/orgs/{c['organization_id']}/verification/confirm")
    assert r.status_code == 403

    # the unverified club shares nothing publicly
    match = (await api.get(base(c) + "/matches")).json()[0]
    share = {"kind": "match", "target_id": match["id"], "days": 7}
    r = await api.post(base(c) + "/share-links", json=share)
    assert r.status_code == 403 and r.json()["type"].endswith("org-unverified")
    # the claimant cannot confirm their own club
    r = await api.post(f"/v1/orgs/{c['organization_id']}/verification/confirm")
    assert r.status_code == 403 and r.json()["type"].endswith("second-person-required")
    # mail domain of the club: the admin's confirmed address at tvt-handball.ch
    await owner_conn.execute("UPDATE users SET email_verified_at = now()")
    r = await api.get(f"/v1/orgs/{c['organization_id']}/verification")
    assert r.json()["verification"] == "verified" and r.json()["verified_via"] == "mail_domain"
    assert (await api.post(base(c) + "/share-links", json=share)).status_code == 201


async def test_verification_by_second_official_and_operator(
    make_api: Callable[[], Api], db_app: FastAPI, outbox: MemoryEmailSender
) -> None:
    api = await coach(make_api, "coach@gmail.com")  # a public mail domain proves nothing
    c = await claim(api)
    org = c["organization_id"]
    r = await api.get(f"/v1/orgs/{org}/verification")
    assert r.json()["verification"] == "unverified"
    assert r.json()["club_domains"] == ["tvt-handball.ch"]
    second = await invite(api, make_api, outbox, c, "coach")  # the invitation confirms the mail
    r = await second.post(f"/v1/orgs/{org}/verification/confirm")
    assert r.status_code == 200, r.text
    assert (r.json()["verification"], r.json()["verified_via"]) == ("verified", "second_official")
    r = await second.post(f"/v1/orgs/{org}/verification/confirm")
    assert r.status_code == 409

    s = db_app.state.settings
    old = list(s.operator_emails)
    s.operator_emails = ["ops@handball-ops.ch"]
    try:
        op = await coach(make_api, "ops@handball-ops.ch")
        r = await op.post(f"/v1/ops/organizations/{org}/verification", json={"verified": False})
        assert r.status_code == 200 and r.json()["verification"] == "unverified"
        r = await op.post(f"/v1/ops/organizations/{org}/verification", json={"verified": True})
        assert (r.json()["verification"], r.json()["verified_via"]) == ("verified", "operator")
        assert (
            await api.post(f"/v1/ops/organizations/{org}/verification", json={"verified": True})
        ).status_code == 404
    finally:
        s.operator_emails = old
    # clubs created by hand are not affected
    plain = make_api()
    ids = await setup_club(plain, "plain@example.org")
    assert (await plain.get(f"/v1/orgs/{ids['org']}/verification")).json()["verification"] == (
        "none"
    )


# ---- sync --------------------------------------------------------------------------------------


async def test_sync_brings_changes_as_suggestions(
    make_api: Callable[[], Api], hch: Recorded
) -> None:
    api = await coach(make_api)
    c = await claim(api)
    roster = {s["payload"]["first_name"]: s for s in await suggestions(api, c, "roster_add")}
    for name in ("Luca", "Noah"):
        await api.post(base(c) + f"/official/suggestions/{roster[name]['id']}/accept")
    # nothing changed: nothing new
    r = await api.post(base(c) + "/official/sync")
    assert r.status_code == 200, r.text
    assert r.json()["roster_suggestions"] == 0 and r.json()["other_suggestions"] == 0

    games = hch.data("getTeamGames", {"teamId": TEAM})
    moved = next(g for g in games["games"] if g["objectId"] == 509159)
    moved["gameDateTime"] = "2026-11-16T19:30:00"
    moved["venueName"] = "Halle Neu"
    extra = dict(moved, objectId=599999, gameDateTime="2027-04-03T16:00:00", venueName="Cup Halle")
    games["games"].append(extra)
    hch.set("getTeamGames", {"teamId": TEAM}, games)
    players = hch.data("getTeamPlayers", {"teamId": TEAM})
    staff = players["playerStaff"][0]["player"]
    staff[:] = [p for p in staff if p["firstName"] != "Noah"]
    staff.append({"playerId": 399999, "firstName": "Neu", "lastName": "Zuzug"})
    hch.set("getTeamPlayers", {"teamId": TEAM}, players)
    r = await api.post(base(c) + "/official/sync")
    assert r.status_code == 200, r.text
    assert r.json()["other_suggestions"] == 2
    assert r.json()["roster_suggestions"] == 2  # Neu Zuzug joined, Noah left
    kinds = {
        (s["kind"], s["payload"].get("first_name") or s["payload"].get("game_id"))
        for s in await suggestions(api, c)
    }
    assert {
        ("match_moved", 509159),
        ("match_new", 599999),
        ("roster_add", "Neu"),
        ("roster_left", "Noah"),
    } <= kinds
    # idempotent: a second sync proposes nothing twice
    r = await api.post(base(c) + "/official/sync")
    assert r.json()["other_suggestions"] == 0 and r.json()["roster_suggestions"] == 0

    by_kind = {s["kind"]: s for s in await suggestions(api, c) if s["kind"] != "roster_add"}
    r = await api.post(base(c) + f"/official/suggestions/{by_kind['match_moved']['id']}/accept")
    assert r.status_code == 200, r.text
    moved_match = r.json()["match_id"]
    r = await api.post(base(c) + f"/official/suggestions/{by_kind['match_new']['id']}/accept")
    assert r.status_code == 200, r.text
    r = await api.post(base(c) + f"/official/suggestions/{by_kind['roster_left']['id']}/dismiss")
    assert r.status_code == 200
    matches = {m["id"]: m for m in (await api.get(base(c) + "/matches")).json()}
    assert matches[moved_match]["kickoff_at"].startswith("2026-11-16T18:30:00")
    assert len(matches) == GAMES + 1
    r = await api.post(base(c) + "/official/sync")
    assert r.json()["other_suggestions"] == 0 and r.json()["roster_suggestions"] == 0


async def test_new_season_is_proposed(
    make_api: Callable[[], Api], hch: Recorded, owner_conn: asyncpg.Connection
) -> None:
    api = await coach(make_api)
    c = await claim(api)
    seasons = hch.data("getSeasons")
    for s in seasons["season"]:
        s["isActual"] = False
    seasons["season"].append(
        {
            "objectId": 2027,
            "name": "2027/28",
            "dateFrom": "2027-07-01T00:00:00",
            "dateTo": "2028-06-30T00:00:00",
            "isActual": True,
        }
    )
    hch.set("getSeasons", {}, seasons)
    detail = hch.data("getClubDetail", {"clubId": CLUB, "seasonId": 2026})
    for t in detail["clubDetail"][0]["teams"]:
        t["seasonId"] = 2027
        t["teamId"] += 10000
    hch.set("getClubDetail", {"clubId": CLUB, "seasonId": 2027}, detail)
    hch.set("getTeamGames", {"teamId": TEAM + 10000}, {"games": []})
    hch.set("getTeamPlayers", {"teamId": TEAM + 10000}, {"playerStaff": []})
    # the season list is cached for a week; here the week is over
    await owner_conn.execute("DELETE FROM official_cache WHERE operation = 'getSeasons'")

    r = await api.post(base(c) + "/official/sync")
    assert r.status_code == 200, r.text
    new = await suggestions(api, c, "season_new")
    assert len(new) == 1 and new[0]["payload"]["label"] == "2027/28"
    assert new[0]["payload"]["official_team_id"] == TEAM + 10000
    r = await api.post(base(c) + f"/official/suggestions/{new[0]['id']}/accept")
    assert r.status_code == 200, r.text
    team = (await api.get(base(c))).json()
    assert team["official_team_id"] == TEAM + 10000
    assert team["current_season"]["label"] in ("2026/27", "2027/28")
    seasons_out = (await api.get(base(c) + "/seasons")).json()
    assert {s["label"] for s in seasons_out} == {"2026/27", "2027/28"}


async def test_daily_tick_syncs_and_imports_reports(
    make_api: Callable[[], Api], hch: Recorded, owner_conn: asyncpg.Connection
) -> None:
    api = await coach(make_api)
    c = await claim(api)
    token = {"x-internal-token": api.app.state.settings.internal_token.get_secret_value()}
    r = await api.http.post("/internal/official/sync", headers=token)
    assert r.json() == {"teams": 0, "suggestions": 0, "reports": 0, "failed": 0, "stopped": 0}
    # a day later: the daily sync finds a new player
    await owner_conn.execute("UPDATE teams SET official_synced_at = now() - interval '2 days'")
    players = hch.data("getTeamPlayers", {"teamId": TEAM})
    players["playerStaff"][0]["player"].append(
        {"playerId": 399999, "firstName": "Neu", "lastName": "Zuzug"}
    )
    hch.set("getTeamPlayers", {"teamId": TEAM}, players)
    r = await api.http.post("/internal/official/sync", headers=token)
    assert r.status_code == 200, r.text
    assert (r.json()["teams"], r.json()["suggestions"], r.json()["stopped"]) == (1, 1, 0)
    # a game ended three hours ago: its report is imported (the suggestion is done)
    await owner_conn.execute(
        "UPDATE matches SET kickoff_at = now() - interval '30 days' "
        "WHERE official_game_id <> 509192"
    )
    await owner_conn.execute(
        "UPDATE matches SET kickoff_at = now() - interval '3 hours' WHERE official_game_id = 509192"
    )
    r = await api.http.post("/internal/official/sync", headers=token)
    assert r.json() == {"teams": 0, "suggestions": 0, "reports": 1, "failed": 0, "stopped": 0}
    count = await owner_conn.fetchval(
        "SELECT count(*) FROM events e JOIN matches m ON m.id = e.match_id "
        "WHERE m.official_game_id = 509192 AND e.source = 'official_report'"
    )
    assert count > 40
    reports = {s["payload"]["game_id"] for s in await suggestions(api, c, "report")}
    assert 509192 not in reports and len(reports) == PLAYED - 1
    kinds = {r["kind"] for r in await owner_conn.fetch("SELECT kind FROM notifications")}
    assert {"official_suggestions", "official_report"} <= kinds
    r = await api.http.post("/internal/official/sync", headers=token)
    assert r.json() == {"teams": 0, "suggestions": 0, "reports": 0, "failed": 0, "stopped": 0}
    # when handball.ch is down the tick stops quietly
    await owner_conn.execute("UPDATE teams SET official_synced_at = now() - interval '2 days'")
    hch.down = True
    r = await api.http.post("/internal/official/sync", headers=token)
    assert r.status_code == 200 and r.json()["stopped"] == 1
    assert (await api.http.post("/internal/official/sync")).status_code == 403
    sync = await api.post(base(c) + "/official/sync")
    assert sync.status_code == 503


async def _tick(api: Api) -> dict[str, int]:
    token = {"x-internal-token": api.app.state.settings.internal_token.get_secret_value()}
    r = await api.http.post("/internal/official/sync", headers=token)
    assert r.status_code == 200, r.text
    out: dict[str, int] = r.json()
    return out


async def _ended(owner_conn: asyncpg.Connection, ago: dict[int, timedelta]) -> None:
    """Only these games ended lately (the others a month ago, outside the report window)."""
    await owner_conn.execute("UPDATE matches SET kickoff_at = now() - interval '30 days'")
    for game, interval in ago.items():
        await owner_conn.execute(
            "UPDATE matches SET kickoff_at = now() - $2::interval WHERE official_game_id = $1",
            game,
            interval,
        )


def _report_calls(hch: Recorded) -> list[int]:
    return [int(v["gameId"]) for op, v in hch.calls if op == "getReport"]


async def test_tick_asks_the_latest_game_first_and_backs_off_without_a_log(
    make_api: Callable[[], Api],
    hch: Recorded,
    owner_conn: asyncpg.Connection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A game whose game log is not online yet is not asked every hour for a week, and it does
    not keep the latest games waiting behind it."""
    from handball_api.services import official

    api = await coach(make_api)
    await claim(api)
    # 509181 ended two hours ago and has no game log yet; 509192 (with log) three hours ago
    await _ended(owner_conn, {509181: timedelta(hours=2), 509192: timedelta(hours=3)})
    monkeypatch.setattr(official, "REPORT_BATCH", 1)
    hch.calls.clear()
    assert (await _tick(api))["reports"] == 0
    assert _report_calls(hch) == [509181]  # the latest game first
    row = await owner_conn.fetchrow(
        "SELECT official_report_tries AS tries, official_report_retry_at - now() AS wait "
        "FROM matches WHERE official_game_id = 509181"
    )
    assert row["tries"] == 1 and timedelta(minutes=55) < row["wait"] <= timedelta(hours=1)
    # the next tick: 509181 waits, 509192 gets its turn
    assert (await _tick(api))["reports"] == 1
    assert _report_calls(hch) == [509181, 509192]
    assert (await _tick(api))["reports"] == 0
    assert _report_calls(hch) == [509181, 509192]  # nobody asked: 509181 still waits
    # an hour later it is asked again, then after two hours, ... up to a day
    await owner_conn.execute(
        "UPDATE matches SET official_report_retry_at = now() WHERE official_game_id = 509181"
    )
    await _tick(api)
    assert _report_calls(hch) == [509181, 509192, 509181]
    row = await owner_conn.fetchrow(
        "SELECT official_report_tries AS tries, official_report_retry_at - now() AS wait "
        "FROM matches WHERE official_game_id = 509181"
    )
    assert row["tries"] == 2 and timedelta(minutes=115) < row["wait"] <= timedelta(hours=2)
    assert official._retry_after(3) == timedelta(hours=4)
    assert official._retry_after(9) == official._retry_after(30) == timedelta(days=1)


async def test_tick_keeps_going_after_an_unexpected_error(
    make_api: Callable[[], Api],
    hch: Recorded,
    owner_conn: asyncpg.Connection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Each team and each game runs in its own savepoint: one failure is rolled back alone and
    the rest of the tick is kept."""
    from handball_api.services import official

    api = await coach(make_api)
    await claim(api)
    await _ended(owner_conn, {509181: timedelta(hours=2), 509192: timedelta(hours=3)})
    await owner_conn.execute("UPDATE teams SET official_synced_at = now() - interval '2 days'")
    real_import = official.import_report

    async def import_report(ctx: Any, m: Any) -> dict[str, Any]:
        if m.official_game_id == 509181:
            m.venue = "half written"
            await ctx.db.flush()
            raise RuntimeError("unexpected")
        return await real_import(ctx, m)

    async def sync_team(ctx: Any, team: Any, *, initial: bool = False) -> dict[str, int]:
        team.league = "half written"
        await ctx.db.flush()
        raise RuntimeError("unexpected")

    monkeypatch.setattr(official, "import_report", import_report)
    monkeypatch.setattr(official, "sync_team", sync_team)
    out = await _tick(api)
    assert out == {"teams": 0, "suggestions": 0, "reports": 1, "failed": 2, "stopped": 0}
    # the imported report stays; the failed game and team are rolled back and tried again later
    assert await owner_conn.fetchval(
        "SELECT count(*) FROM events e JOIN matches m ON m.id = e.match_id "
        "WHERE m.official_game_id = 509192 AND e.source = 'official_report'"
    )
    failed = await owner_conn.fetchrow(
        "SELECT venue, official_report_tries FROM matches WHERE official_game_id = 509181"
    )
    assert failed["venue"] != "half written" and failed["official_report_tries"] == 1
    team = await owner_conn.fetchrow("SELECT league, official_synced_at FROM teams")
    assert team["league"] != "half written"
    assert team["official_synced_at"] > datetime.now(team["official_synced_at"].tzinfo) - timedelta(
        minutes=1
    )
    assert await _tick(api) == {
        "teams": 0,
        "suggestions": 0,
        "reports": 0,
        "failed": 0,
        "stopped": 0,
    }


def test_public_mail_providers_prove_no_club_role() -> None:
    from handball_api.services.org_verification import club_domains

    # a club listed with a free-mail address: anyone could sign up there
    assert club_domains(["bluemail.ch", "GMX.at", "hotmail.de", "tvt-handball.ch"]) == [
        "tvt-handball.ch"
    ]


def test_long_suggestion_keys_are_found_again() -> None:
    """A moved game's key carries the venue; one longer than the column is stored cut, and the
    next sync must find it instead of inserting it again (unique key)."""
    import uuid
    from types import SimpleNamespace

    from handball_api.services.official import _Suggester

    added: list[Any] = []
    ctx: Any = SimpleNamespace(db=SimpleNamespace(add=added.append))
    team: Any = SimpleNamespace(organization_id=uuid.uuid4(), id=uuid.uuid4())
    key = "game:484345:2026-11-05T18:00:00+00:00:" + "Sportzentrum Krauer Dreifachhalle " * 3
    first = _Suggester(ctx, team, {})
    first("match_moved", key, {"n": 1})
    assert len(added) == 1 and len(added[0].official_key) == 80
    # the next sync loads the stored suggestions by their stored key
    added[0].status = "open"
    again = _Suggester(ctx, team, {("match_moved", added[0].official_key): added[0]})
    again("match_moved", key, {"n": 2})
    assert len(added) == 1 and added[0].payload == {"n": 2}


async def test_claims_are_rate_limited_per_user(make_api: Callable[[], Api], hch: Recorded) -> None:
    """A claim may ask handball.ch and an access request notifies the club admins."""

    class Spent:
        async def hit(self, key: str, limit: int, window: int) -> bool:
            return not key.startswith("official-claim:")

    api = await coach(make_api)
    api.app.state.rate_limiter = Spent()
    r = await api.post(f"/v1/official/teams/{TEAM}/claim", json={"club_id": CLUB})
    assert r.status_code == 429, r.text
    assert hch.calls == []  # handball.ch not asked
