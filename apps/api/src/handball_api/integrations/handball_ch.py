"""handball.ch match centre: the public GraphQL API behind https://www.handball.ch/de/matchcenter.

One client for everything the API reads there: clubs and their registered teams, the season, a
team's games, the registered players, the standing of a group, per-game player stats and the
game report (game log). Before, the same queries lived in ml/eval/fetch_handball_ch.py,
ml/data/match_official.py and services/official_report.py.

- Fixed host only: the endpoint is a constant; callers pass ids, never URLs.
- Polite: requests start at least MIN_INTERVAL_S apart per process (a reserved start time, no
  lock held during the request), a timeout on every request, and
  after an error (timeout, 429, 5xx) no request for COOLDOWN_S (Retry-After is respected).
- Cached: answers are kept in the `official_cache` table; each reader says how old an answer may
  be (club list a week, a played game's stats forever, a team's schedule a few hours).
- Tests never hit the network: they install a transport that answers from recorded fixtures
  (`set_transport`, apps/api/tests/fixtures/handball_ch).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import time
import unicodedata
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import delete, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from handball_api.integrations.base import AdapterError
from handball_api.models import OfficialCache

PROVIDER = "handball_ch"
API = "https://www.handball.ch/Umbraco/Api/MatchCenter/Query"
GAME_PAGE = "https://www.handball.ch/de/matchcenter/spiele/{}"
HEADERS = {"User-Agent": "handball-ai/1.0 (club onboarding)", "Accept-Language": "de"}
TIMEOUT = httpx.Timeout(15.0, connect=5.0)
TZ = ZoneInfo("Europe/Zurich")
MIN_INTERVAL_S = 0.5
COOLDOWN_S = 120.0
# the game log and per-player stats exist from season 2023/24 on
FIRST_LOG_SEASON = 2023
PLAYED = 2  # gameStatusId of a played game

# ---- queries -------------------------------------------------------------------------------

Q_SEASONS = "query getSeasons { season { objectId name dateFrom dateTo isActual } }"
Q_CLUBS = "query getClubs { club { clubId name city canton } }"
Q_CLUB = """query getClubDetail($clubId: Int, $seasonId: Int) {
  clubDetail(clubId: $clubId, seasonId: $seasonId) { clubId name city canton website email
    teams { teamId clubId currentGroupId currentGroupName seasonId name shortName leagueId
      leagueName leagueShortName sortOrder } } }"""
Q_TEAM_GAMES = """query getTeamGames($teamId: Int) { games(teamId: $teamId) { objectId gameNumber
  seasonId gameDateTime homeTeamId homeTeamName homeTeamClubId homeTeamScore homeTeamScoreInterval
  awayTeamId awayTeamName awayTeamClubId awayTeamScore awayTeamScoreInterval gameStatusId venueId
  venueName leagueShortName groupName gameGroupOrCupId } }"""
# players only: the staff list (names of coaches and officials) is not needed
Q_TEAM_PLAYERS = """query getTeamPlayers($teamId: Int) { playerStaff(teamId: $teamId) { teamId
  player { playerId firstName lastName } } }"""
Q_STANDING = """query getStanding($groupId: Int) { standing(groupId: $groupId) { teamId clubId
  name rank games won drawn lost goalsFor goalsAgainst goalDifference points } }"""
# per player and game: goals, 7 m goals and attempts, 2-minute suspensions, keeper saves and the
# shots a keeper faced (missing for some games: None then)
Q_GAME_PLAYERS = """query getGamePlayers($gameId: Int, $isLive: Boolean) {
  gamePlayerStats(gameId: $gameId, isLive: $isLive) { playerId teamId dressNr playerName isHome
    function totalScore totalScore7m totalShots7m total2Minutes totalSaves totalShotsGK } }"""
Q_REPORT = """query getReport($gameId: Int, $isLive: Boolean) {
  game(gameId: $gameId) { homeTeamName awayTeamName homeTeamScore awayTeamScore
    homeTeamScoreInterval awayTeamScoreInterval gameDateTime leagueName }
  gameLog(gameId: $gameId, isLive: $isLive) { actionText homeTeamActionLCID awayTeamActionLCID
    homeTeamPlayerStaffName homeTeamPlayerStaffNrDesc awayTeamPlayerStaffName
    awayTeamPlayerStaffNrDesc result timeInt timeString }
  gamePlayerStats(gameId: $gameId, isLive: $isLive) { dressNr isHome function } }"""

FRESH = timedelta(0)
WEEK = timedelta(days=7)
DAY = timedelta(days=1)
HOURS_6 = timedelta(hours=6)
# how long an answer is kept at all (official_cache retention, purged by the hourly tick): the
# readers want younger answers, an older one only stands in while handball.ch does not answer.
# Player names and statistics are not kept for ever: a played game's player stats (asked once,
# kept for the roster suggestions of its season) a year, everything else a month.
KEEP = timedelta(days=30)
KEEP_BY_OPERATION = {"getGamePlayers": timedelta(days=365)}


class UpstreamUnavailableError(AdapterError):
    """handball.ch did not answer (or we are waiting after an error)."""


# ---- transport, pacing, cache --------------------------------------------------------------

_transport: httpx.AsyncBaseTransport | None = None
_pace: dict[str, float] = {"next": 0.0, "blocked_until": 0.0}


def set_transport(transport: httpx.AsyncBaseTransport | None, min_interval_s: float = 0.0) -> None:
    """Tests: answer from recorded data instead of the network (None restores the network)."""
    global _transport, MIN_INTERVAL_S
    _transport = transport
    MIN_INTERVAL_S = min_interval_s if transport is not None else 0.5
    _pace.update(next=0.0, blocked_until=0.0)


def _resting() -> None:
    if time.monotonic() < _pace["blocked_until"]:
        raise UpstreamUnavailableError("handball.ch is resting after an error")


async def _take_slot() -> None:
    """Rate limit without holding a lock during the request: each caller reserves the next free
    start time (MIN_INTERVAL_S after the one before) and sleeps until then. The reservation
    has no await in it, so callers on the event loop never get the same slot; a slow answer
    no longer holds up the requests after it."""
    _resting()
    now = time.monotonic()
    slot = max(now, _pace["next"])
    _pace["next"] = slot + MIN_INTERVAL_S
    if slot > now:
        await asyncio.sleep(slot - now)
        _resting()  # an error while this one waited: no request either


def _operation(q: str) -> str:
    m = re.search(r"query\s+(\w+)", q)
    return m.group(1) if m else "query"


def cache_key(q: str, variables: dict[str, Any]) -> str:
    raw = json.dumps([PROVIDER, " ".join(q.split()), variables], sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def _cool_down(seconds: float) -> None:
    _pace["blocked_until"] = max(_pace["blocked_until"], time.monotonic() + seconds)


async def _post(q: str, variables: dict[str, Any]) -> dict[str, Any]:
    await _take_slot()
    try:
        async with httpx.AsyncClient(
            timeout=TIMEOUT, headers=HEADERS, transport=_transport
        ) as client:
            r = await client.post(API, json={"query": q, "variables": variables})
    except httpx.HTTPError as exc:
        _cool_down(COOLDOWN_S)
        raise UpstreamUnavailableError(f"handball.ch: {type(exc).__name__}") from exc
    if r.status_code == 429 or r.status_code >= 500:
        retry = r.headers.get("retry-after", "")
        _cool_down(float(retry) if retry.isdigit() else COOLDOWN_S)
        raise UpstreamUnavailableError(f"handball.ch answered {r.status_code}")
    if r.status_code != 200:
        raise UpstreamUnavailableError(f"handball.ch answered {r.status_code}")
    try:
        payload = r.json()
    except ValueError as exc:
        raise UpstreamUnavailableError("handball.ch answered no JSON") from exc
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        raise UpstreamUnavailableError("handball.ch answered without data")
    if payload.get("errors") and not any(data.values()):
        raise UpstreamUnavailableError("handball.ch answered with errors")
    return data


async def query(
    q: str,
    variables: dict[str, Any] | None = None,
    *,
    db: AsyncSession | None = None,
    max_age: timedelta | None = DAY,
) -> dict[str, Any]:
    """POST a query; with `db` the answer is cached (max_age None = keep forever, FRESH = always
    ask). A stale cache entry is still used when handball.ch does not answer, except for FRESH."""
    variables = variables or {}
    key = cache_key(q, variables)
    hit: OfficialCache | None = None
    if db is not None:
        hit = await db.get(OfficialCache, key)
        if hit is not None and (max_age is None or datetime.now(UTC) - hit.fetched_at < max_age):
            return dict(hit.data)
    try:
        data = await _post(q, variables)
    except UpstreamUnavailableError:
        if hit is not None and max_age != FRESH:
            return dict(hit.data)
        raise
    if db is not None:
        stmt = insert(OfficialCache).values(
            key=key,
            provider=PROVIDER,
            operation=_operation(q),
            variables=variables,
            data=data,
            fetched_at=datetime.now(UTC),
        )
        await db.execute(
            stmt.on_conflict_do_update(
                index_elements=[OfficialCache.key],
                set_={"data": stmt.excluded.data, "fetched_at": stmt.excluded.fetched_at},
            )
        )
    return data


async def purge_cache(db: AsyncSession, now: datetime | None = None) -> int:
    """Delete the cached answers older than they are useful (KEEP, KEEP_BY_OPERATION)."""
    now = now or datetime.now(UTC)
    longer = list(KEEP_BY_OPERATION)
    expired = (
        OfficialCache.operation.not_in(longer) & (OfficialCache.fetched_at < now - KEEP)
    ) | or_(
        *(
            (OfficialCache.operation == op) & (OfficialCache.fetched_at < now - keep)
            for op, keep in KEEP_BY_OPERATION.items()
        )
    )
    result = await db.execute(
        delete(OfficialCache).where(expired).execution_options(synchronize_session=False)
    )
    return int(getattr(result, "rowcount", 0) or 0)


async def cached_at(db: AsyncSession, q: str, variables: dict[str, Any]) -> datetime | None:
    return await db.scalar(
        select(OfficialCache.fetched_at).where(OfficialCache.key == cache_key(q, variables))
    )


# ---- data ----------------------------------------------------------------------------------


@dataclass(frozen=True)
class Season:
    id: int
    label: str
    starts_on: date
    ends_on: date
    current: bool


@dataclass(frozen=True)
class Club:
    id: int
    name: str
    city: str | None


@dataclass(frozen=True)
class ClubDetail:
    id: int
    name: str
    city: str | None
    website: str | None
    email: str | None
    teams: list[OfficialTeam]


@dataclass(frozen=True)
class OfficialTeam:
    id: int
    club_id: int  # the club that registered the team (a joint team belongs to one club)
    name: str
    league: str | None
    league_short: str | None
    group_id: int | None
    group_name: str | None
    season_id: int
    sort_order: int


@dataclass(frozen=True)
class OfficialGame:
    id: int
    season_id: int
    kickoff_at: datetime
    home_team_id: int
    home_name: str
    away_team_id: int
    away_name: str
    home_score: int | None
    away_score: int | None
    home_half: int | None
    away_half: int | None
    played: bool
    venue: str | None
    competition: str | None
    group_id: int | None


@dataclass(frozen=True)
class OfficialPlayer:
    id: int
    first_name: str
    last_name: str


@dataclass(frozen=True)
class GameAppearance:
    player_id: int
    team_id: int
    number: int | None
    name: str | None
    goals: int
    goalkeeper: bool = False
    # None when the official data has no value for the game
    goals_7m: int | None = None
    attempts_7m: int | None = None
    suspensions: int | None = None
    saves: int | None = None
    shots_faced: int | None = None


def fold(s: str | None) -> str:
    """Lower case without accents (Thalwil, thalwil, Thälwil all match)."""
    s = (s or "").replace("ß", "ss")
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


def parse_kickoff(value: str) -> datetime:
    """handball.ch gives Swiss local time without offset."""
    return datetime.fromisoformat(value).replace(tzinfo=TZ)


def _int(v: Any) -> int | None:
    return int(v) if isinstance(v, int | float) and not isinstance(v, bool) else None


async def seasons(db: AsyncSession | None) -> list[Season]:
    rows = (await query(Q_SEASONS, db=db, max_age=WEEK)).get("season") or []
    return [
        Season(
            id=int(s["objectId"]),
            label=str(s.get("name") or s["objectId"]),
            starts_on=datetime.fromisoformat(s["dateFrom"]).date(),
            ends_on=datetime.fromisoformat(s["dateTo"]).date(),
            current=bool(s.get("isActual")),
        )
        for s in rows
    ]


async def current_season(db: AsyncSession | None) -> Season:
    all_ = await seasons(db)
    current = [s for s in all_ if s.current]
    if not current:
        raise UpstreamUnavailableError("handball.ch has no current season")
    return max(current, key=lambda s: s.id)


async def clubs(db: AsyncSession | None) -> list[Club]:
    rows = (await query(Q_CLUBS, db=db, max_age=WEEK)).get("club") or []
    return [
        Club(id=int(c["clubId"]), name=str(c.get("name") or ""), city=c.get("city"))
        for c in rows
        if c.get("clubId")
    ]


async def club(
    db: AsyncSession | None, club_id: int, season_id: int, max_age: timedelta = DAY
) -> ClubDetail | None:
    rows = (
        await query(Q_CLUB, {"clubId": club_id, "seasonId": season_id}, db=db, max_age=max_age)
    ).get("clubDetail") or []
    if not rows:
        return None
    c = rows[0]
    teams = [
        OfficialTeam(
            id=int(t["teamId"]),
            club_id=int(t.get("clubId") or club_id),
            name=str(t.get("name") or ""),
            league=t.get("leagueName"),
            league_short=t.get("leagueShortName"),
            group_id=_int(t.get("currentGroupId")),
            group_name=t.get("currentGroupName"),
            season_id=int(t.get("seasonId") or season_id),
            sort_order=int(t.get("sortOrder") or 0),
        )
        for t in c.get("teams") or []
        if t.get("teamId")
    ]
    return ClubDetail(
        id=int(c.get("clubId") or club_id),
        name=str(c.get("name") or ""),
        city=c.get("city"),
        website=c.get("website") or None,
        email=c.get("email") or None,
        teams=sorted(teams, key=lambda t: t.sort_order),
    )


def _game(g: dict[str, Any]) -> OfficialGame:
    played = g.get("gameStatusId") == PLAYED
    group = g.get("groupName") or None
    league = g.get("leagueShortName") or None
    return OfficialGame(
        id=int(g["objectId"]),
        season_id=int(g.get("seasonId") or 0),
        kickoff_at=parse_kickoff(str(g["gameDateTime"])),
        home_team_id=int(g.get("homeTeamId") or 0),
        home_name=str(g.get("homeTeamName") or "").strip(),
        away_team_id=int(g.get("awayTeamId") or 0),
        away_name=str(g.get("awayTeamName") or "").strip(),
        home_score=_int(g.get("homeTeamScore")) if played else None,
        away_score=_int(g.get("awayTeamScore")) if played else None,
        home_half=_int(g.get("homeTeamScoreInterval")) if played else None,
        away_half=_int(g.get("awayTeamScoreInterval")) if played else None,
        played=played,
        venue=g.get("venueName") or None,
        competition=group or league,
        group_id=_int(g.get("gameGroupOrCupId")),
    )


async def team_games(
    db: AsyncSession | None, team_id: int, max_age: timedelta = HOURS_6
) -> list[OfficialGame]:
    rows = (await query(Q_TEAM_GAMES, {"teamId": team_id}, db=db, max_age=max_age)).get(
        "games"
    ) or []
    games = [_game(g) for g in rows if g.get("objectId") and g.get("gameDateTime")]
    return sorted(games, key=lambda g: g.kickoff_at)


async def team_players(
    db: AsyncSession | None, team_id: int, max_age: timedelta = DAY
) -> list[OfficialPlayer]:
    rows = (await query(Q_TEAM_PLAYERS, {"teamId": team_id}, db=db, max_age=max_age)).get(
        "playerStaff"
    ) or []
    out: dict[int, OfficialPlayer] = {}
    for t in rows:
        for p in t.get("player") or []:
            if p.get("playerId") and (p.get("firstName") or p.get("lastName")):
                out[int(p["playerId"])] = OfficialPlayer(
                    id=int(p["playerId"]),
                    first_name=str(p.get("firstName") or "").strip(),
                    last_name=str(p.get("lastName") or "").strip(),
                )
    return list(out.values())


async def standing(
    db: AsyncSession | None, group_id: int, max_age: timedelta = HOURS_6
) -> list[dict[str, Any]]:
    rows = (await query(Q_STANDING, {"groupId": group_id}, db=db, max_age=max_age)).get(
        "standing"
    ) or []
    keys = (
        *("teamId", "clubId", "name", "rank", "games", "won", "drawn", "lost"),
        *("goalsFor", "goalsAgainst", "goalDifference", "points"),
    )
    return sorted(
        [{k: r.get(k) for k in keys} for r in rows], key=lambda r: int(r.get("rank") or 0)
    )


async def game_players(db: AsyncSession | None, game_id: int) -> list[GameAppearance]:
    """Players of a played game with shirt number (kept forever: a played game does not change;
    callers only ask for played games)."""
    rows = (
        await query(Q_GAME_PLAYERS, {"gameId": game_id, "isLive": False}, db=db, max_age=None)
    ).get("gamePlayerStats") or []
    return [
        GameAppearance(
            player_id=int(p["playerId"]),
            team_id=int(p.get("teamId") or 0),
            number=_int(p.get("dressNr")),
            name=p.get("playerName"),
            goals=int(p.get("totalScore") or 0),
            goalkeeper=p.get("function") == "goalkeeper",
            goals_7m=_int(p.get("totalScore7m")),
            attempts_7m=_int(p.get("totalShots7m")),
            suspensions=_int(p.get("total2Minutes")),
            saves=_int(p.get("totalSaves")),
            shots_faced=_int(p.get("totalShotsGK")),
        )
        for p in rows
        # team officials carry placeholder ids shared across teams: players only
        if p.get("playerId") and p.get("function") in ("player", "goalkeeper")
    ]


async def report(game_id: int, db: AsyncSession | None = None) -> dict[str, Any]:
    """Game, game log and keepers of a game (parsed by official_reports/handball_ch.py). Not
    cached without `db`; with `db` for an hour (a fresh game may still get corrections)."""
    return await query(
        Q_REPORT, {"gameId": game_id, "isLive": False}, db=db, max_age=timedelta(hours=1)
    )


def mail_domains(detail: ClubDetail) -> list[str]:
    """Domains of the club's website and e-mail address (for the verification by mail domain)."""
    out: list[str] = []
    if detail.website:
        host = re.sub(r"^https?://", "", detail.website.strip().lower()).split("/")[0]
        host = host.split(":")[0].removeprefix("www.")
        if "." in host:
            out.append(host)
    if detail.email and "@" in detail.email:
        out.append(detail.email.strip().lower().rsplit("@", 1)[1])
    return list(dict.fromkeys(out))
