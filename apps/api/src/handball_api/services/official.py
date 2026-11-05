"""Clubs and teams from the official league data, Switzerland first (handball.ch).

docs/plans/federation-onboarding.md, phases 1 and 3:
- search: club name or town, the hits are the registered teams of the current season;
- claim: creates or links the organisation (one per official club) and the team with the
  official ids and prefills the season schedule with results, the standing, roster suggestions
  (name, shirt number, appearances and the official statistics the coach may show; the coach
  confirms) and the past games with a game log as importable reports. Official games count toward
  the plan's matches per season: over the limit they stay suggestions (reason plan_limit).
  Someone claiming a club or team that is already in the app asks its admins for access instead
  (org_access_requests);
- sync: daily (worker tick) and on demand. Moved and new games, roster changes and the next
  season come in as suggestions; results are taken over; after each game the official report is
  imported automatically.

Data protection: names from the official data are only suggestions for the team's organisers;
an accepted roster entry from the official data stays hidden from the other team members until
the person joins or a consent is recorded (services/roster.py). No public profiles from it.
"""

from __future__ import annotations

import re
import uuid
from collections import Counter
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select, text

from handball_api.core.db import disable_system_access, enable_system_access, set_tenant
from handball_api.core.errors import ProblemError
from handball_api.integrations import handball_ch as ch
from handball_api.models import (
    Match,
    Membership,
    OfficialSuggestion,
    Opponent,
    OrgAccessRequest,
    Organization,
    OrgMembership,
    Player,
    RosterEntry,
    Season,
    Team,
    User,
)
from handball_api.models.enums import MatchFormatKey, MatchStatus, OrgRole, TeamGender, TeamRole
from handball_api.schemas.official import AccessApproveIn, ClaimIn, SuggestionAcceptIn
from handball_api.schemas.orgs import OrgCreate
from handball_api.services import (
    audit,
    billing,
    match_formats,
    official_report,
    org_verification,
    training,
)
from handball_api.services import orgs as org_service
from handball_api.services.context import Ctx
from handball_api.services.policies import Action, Actor, authorize, can

PROVIDER = ch.PROVIDER
MIN_QUERY = 3
MAX_CLUBS = 5
# shirt numbers and appearances from the last played games (cached forever once played)
STATS_GAMES = 10
SYNC_EVERY = timedelta(hours=20)
SYNC_BATCH = 20
REPORT_AFTER = timedelta(minutes=90)  # a game is over and the log complete
REPORT_WINDOW = timedelta(days=7)
REPORT_BATCH = 20
SYSTEM_USER = uuid.UUID(int=0)
# reason of a match_new suggestion made at the claim instead of a match: the plan's match limit
PLAN_LIMIT = "plan_limit"
# team preference (team.settings): show the official statistics in roster suggestions
ROSTER_STATS = "official_roster_stats"


def _now() -> datetime:
    return datetime.now(UTC)


def _unavailable(exc: Exception) -> ProblemError:
    return ProblemError(
        503, "official-unavailable", "handball.ch does not answer right now, try again later"
    )


# ---- search ------------------------------------------------------------------------------------


def _tokens(q: str) -> list[str]:
    return [t for t in re.split(r"[^\w]+", ch.fold(q)) if t]


async def search(ctx: Ctx, user: User, q: str) -> list[dict[str, Any]]:
    tokens = _tokens(q)
    if len("".join(tokens)) < MIN_QUERY:
        raise ProblemError(422, "query-too-short", "Type at least three letters")
    try:
        season = await ch.current_season(ctx.db)
        found = []
        for c in await ch.clubs(ctx.db):
            text = ch.fold(f"{c.name} {c.city or ''}")
            if all(t in text for t in tokens):
                # clubs whose name starts with the query first, then the town
                found.append((not ch.fold(c.name).startswith(tokens[0]), c.name, c))
        found.sort(key=lambda x: (x[0], x[1]))
        hits: list[dict[str, Any]] = []
        for _, _, c in found[:MAX_CLUBS]:
            detail = await ch.club(ctx.db, c.id, season.id)
            for t in detail.teams if detail else []:
                hits.append(
                    {
                        "official_id": t.id,
                        "name": t.name,
                        "league": t.league,
                        "league_short": t.league_short,
                        "group_name": t.group_name,
                        "season_id": t.season_id,
                        "club": {"id": c.id, "name": c.name, "city": c.city},
                        "registered_club_id": t.club_id,
                        "status": "available",
                    }
                )
    except ch.UpstreamUnavailableError as exc:
        raise _unavailable(exc) from exc
    if not hits:
        return []
    await enable_system_access(ctx.db, reason="official team search: which teams are claimed")
    try:
        linked = {
            tid: (team_id, org_id)
            for tid, team_id, org_id in await ctx.db.execute(
                select(Team.official_team_id, Team.id, Team.organization_id).where(
                    Team.official_provider == PROVIDER,
                    Team.official_team_id.in_([h["official_id"] for h in hits]),
                )
            )
        }
        mine = set(
            (
                await ctx.db.scalars(
                    select(OrgMembership.organization_id).where(OrgMembership.user_id == user.id)
                )
            ).all()
        )
    finally:
        await disable_system_access(ctx.db)
    for h in hits:
        if h["official_id"] in linked:
            team_id, org_id = linked[h["official_id"]]
            h["team_id"] = team_id
            h["status"] = "member" if org_id in mine else "claimed"
            h["organization_id"] = org_id if org_id in mine else None
    return hits


# ---- claim -------------------------------------------------------------------------------------


def gender_of(t: ch.OfficialTeam) -> TeamGender:
    league = ch.fold(t.league)
    if "frauen" in league or "juniorinnen" in league or (t.league_short or "").startswith("F"):
        return TeamGender.WOMEN
    if "mixed" in league or "gemischt" in league:
        return TeamGender.MIXED
    return TeamGender.MEN


def is_youth(t: ch.OfficialTeam) -> bool:
    return "junior" in ch.fold(t.league) or bool(re.match(r"^[MF]?U\d", t.league_short or ""))


async def _request_access(
    ctx: Ctx,
    user: User,
    org_id: uuid.UUID,
    team_id: uuid.UUID | None,
    official_team_id: int,
    message: str | None,
) -> OrgAccessRequest:
    """System access: the person is not a member of the club asked."""
    req = await ctx.db.scalar(
        select(OrgAccessRequest).where(
            OrgAccessRequest.organization_id == org_id,
            OrgAccessRequest.user_id == user.id,
            OrgAccessRequest.status == "pending",
        )
    )
    if req is None:
        req = OrgAccessRequest(
            organization_id=org_id,
            user_id=user.id,
            team_id=team_id,
            official_team_id=official_team_id,
            message=message,
        )
        ctx.db.add(req)
        await ctx.db.flush()
        admins = (
            await ctx.db.scalars(
                select(OrgMembership.user_id).where(
                    OrgMembership.organization_id == org_id,
                    OrgMembership.role == OrgRole.ORG_ADMIN,
                )
            )
        ).all()
        await training.notify(
            ctx,
            org_id,
            list(admins),
            "access_request",
            {"request_id": str(req.id)},
            f"/app/{org_id}/settings/access-requests",
        )
        await audit.record(
            ctx,
            "org.access_requested",
            org_id=org_id,
            target_type="org_access_request",
            target_id=req.id,
            actor_id=user.id,
            data={"official_team_id": official_team_id},
        )
    return req


async def _official_team(
    ctx: Ctx, club_id: int, official_team_id: int
) -> tuple[ch.Season, ch.ClubDetail, ch.OfficialTeam]:
    try:
        season = await ch.current_season(ctx.db)
        detail = await ch.club(ctx.db, club_id, season.id)
    except ch.UpstreamUnavailableError as exc:
        raise _unavailable(exc) from exc
    team = next((t for t in detail.teams if t.id == official_team_id), None) if detail else None
    if detail is None or team is None:
        raise ProblemError(404, "official-team-not-found", "This team is not registered there")
    return season, detail, team


async def claim(ctx: Ctx, user: User, official_team_id: int, data: ClaimIn) -> dict[str, Any]:
    season, detail, oteam = await _official_team(ctx, data.club_id, official_team_id)
    # two people claiming the same club at the same moment: the second waits here until the first
    # committed, then finds the club taken and gets an access request (not a unique-key error)
    await ctx.db.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:k))"),
        {"k": f"official-club:{PROVIDER}:{detail.id}"},
    )
    await enable_system_access(ctx.db, reason="official claim: one club per official club id")
    try:
        mine = set(
            (
                await ctx.db.scalars(
                    select(OrgMembership.organization_id).where(OrgMembership.user_id == user.id)
                )
            ).all()
        )
        linked = await ctx.db.scalar(
            select(Team).where(
                Team.official_provider == PROVIDER, Team.official_team_id == official_team_id
            )
        )
        if linked is not None:
            if linked.organization_id in mine:
                return {
                    "status": "already_member",
                    "organization_id": linked.organization_id,
                    "team_id": linked.id,
                }
            req = await _request_access(
                ctx, user, linked.organization_id, linked.id, official_team_id, data.message
            )
            return {"status": "access_requested", "access_request_id": req.id}
        club_org = await ctx.db.scalar(
            select(Organization).where(
                Organization.official_provider == PROVIDER,
                Organization.official_club_id == detail.id,
            )
        )
        if club_org is not None and club_org.id not in mine:
            req = await _request_access(
                ctx, user, club_org.id, None, official_team_id, data.message
            )
            return {"status": "access_requested", "access_request_id": req.id}
    finally:
        await disable_system_access(ctx.db)

    created = False
    if club_org is not None:
        org = club_org
    elif data.org_id is not None:
        actor, org = await org_service.build_actor(ctx, user, data.org_id)
        ctx.actor = actor
        authorize(actor, Action.ORG_UPDATE, two_factor=ctx.two_factor)
        if org.official_club_id is not None:
            raise ProblemError(409, "org-linked", "This club is linked to another official club")
    else:
        org = await org_service.create_org(ctx, user, OrgCreate(name=detail.name[:120]))
        created = True
    if org.official_club_id is None:
        org.official_provider, org.official_club_id = PROVIDER, detail.id
        org.official_domains = ch.mail_domains(detail)
        org.verification = org_verification.UNVERIFIED
        org.claimed_by_id = user.id
    actor, org = await org_service.build_actor(ctx, user, org.id)
    ctx.actor = actor
    authorize(actor, Action.TEAM_CREATE, two_factor=ctx.two_factor)
    team = await _create_team(ctx, org, season, oteam, user.id, data.team_name)
    counts = await sync_team(ctx, team, initial=True)
    await org_verification.evaluate(ctx, org)
    await audit.record(
        ctx,
        "official.team_claimed",
        target_type="team",
        target_id=team.id,
        data={"provider": PROVIDER, "club_id": detail.id, "team_id": oteam.id, "new_org": created},
    )
    return {
        "status": "claimed",
        "organization_id": org.id,
        "team_id": team.id,
        "created_organization": created,
        "verification": org.verification,
        "prefill": counts,
    }


async def _season_row(ctx: Ctx, org_id: uuid.UUID, team_id: uuid.UUID, season: ch.Season) -> Season:
    row = await ctx.db.scalar(
        select(Season).where(Season.team_id == team_id, Season.label == season.label)
    )
    if row is None:
        row = Season(
            organization_id=org_id,
            team_id=team_id,
            label=season.label,
            starts_on=season.starts_on,
            ends_on=season.ends_on,
        )
        ctx.db.add(row)
        await ctx.db.flush()
    return row


async def _create_team(
    ctx: Ctx,
    org: Organization,
    season: ch.Season,
    oteam: ch.OfficialTeam,
    coach_id: uuid.UUID,
    name: str | None = None,
    role: TeamRole = TeamRole.COACH,
) -> Team:
    await billing.check_new_team(ctx, org.id)
    youth = is_youth(oteam)
    team = Team(
        organization_id=org.id,
        name=(name or oteam.name)[:120],
        league=(oteam.league or None) and str(oteam.league)[:120],
        is_youth=youth,
        gender=gender_of(oteam),
        settings={"players_see_team_stats": not youth},
        official_provider=PROVIDER,
        official_team_id=oteam.id,
        official_club_id=oteam.club_id,
        official_group_id=oteam.group_id,
        official_season_id=oteam.season_id,
        official_state={"league": oteam.league, "group_name": oteam.group_name},
    )
    ctx.db.add(team)
    await ctx.db.flush()
    await _season_row(ctx, org.id, team.id, season)
    ctx.db.add(Membership(organization_id=org.id, team_id=team.id, user_id=coach_id, role=role))
    actor = ctx.require_actor()
    if actor.user_id == coach_id:
        ctx.actor = replace(actor, team_roles={**actor.team_roles, team.id: role})
    await audit.record(ctx, "team.created", target_type="team", target_id=team.id)
    await ctx.db.flush()
    return team


# ---- sync (prefill at claim, daily, on demand) -------------------------------------------------


async def _suggestions(ctx: Ctx, team_id: uuid.UUID) -> dict[tuple[str, str], OfficialSuggestion]:
    rows = await ctx.db.scalars(
        select(OfficialSuggestion).where(OfficialSuggestion.team_id == team_id)
    )
    return {(s.kind, s.official_key): s for s in rows.all()}


class _Suggester:
    def __init__(
        self, ctx: Ctx, team: Team, known: dict[tuple[str, str], OfficialSuggestion]
    ) -> None:
        self.ctx, self.team, self.known = ctx, team, known
        self.created: Counter[str] = Counter()

    def __call__(self, kind: str, key: str, payload: dict[str, Any]) -> None:
        """One suggestion per team, kind and key: an open one gets the newest data, a decided
        one is not proposed again."""
        key = key[:80]  # as stored (official_key), so that a known one is found again
        s = self.known.get((kind, key))
        if s is not None:
            if s.status == "open":
                # a game held back by the plan limit keeps its reason
                reason = {"reason": s.payload["reason"]} if "reason" in s.payload else {}
                s.payload = {**payload, **reason}
            return
        s = OfficialSuggestion(
            organization_id=self.team.organization_id,
            team_id=self.team.id,
            kind=kind,
            official_key=key,
            payload=payload,
        )
        self.ctx.db.add(s)
        self.known[(kind, key)] = s
        self.created[kind] += 1


def _game_payload(g: ch.OfficialGame, team: Team) -> dict[str, Any]:
    home = g.home_team_id == team.official_team_id
    return {
        "game_id": g.id,
        "kickoff_at": g.kickoff_at.isoformat(),
        "is_home": home,
        "opponent": g.away_name if home else g.home_name,
        "venue": g.venue,
        "competition": g.competition,
        "played": g.played,
        "score_own": g.home_score if home else g.away_score,
        "score_opponent": g.away_score if home else g.home_score,
    }


def _scores(m: Match, g: ch.OfficialGame, home: bool) -> bool:
    """Takes over the official result when the match has none."""
    if not g.played or g.home_score is None or g.away_score is None or m.score_own is not None:
        return False
    own, opp = (g.home_score, g.away_score) if home else (g.away_score, g.home_score)
    m.score_own, m.score_opponent = own, opp
    if g.home_half is not None and g.away_half is not None:
        h_own, h_opp = (g.home_half, g.away_half) if home else (g.away_half, g.home_half)
        m.halftime_own, m.halftime_opponent = h_own, h_opp
    return True


async def _opponent(ctx: Ctx, org_id: uuid.UUID, name: str, cache: dict[str, Opponent]) -> Opponent:
    key = ch.fold(name)
    if key not in cache:
        opp = Opponent(organization_id=org_id, name=name[:120] or "?")
        ctx.db.add(opp)
        await ctx.db.flush()
        cache[key] = opp
    return cache[key]


async def _new_match(
    ctx: Ctx, team: Team, season: Season, payload: dict[str, Any], cache: dict[str, Opponent]
) -> Match:
    opp = await _opponent(ctx, team.organization_id, str(payload["opponent"]), cache)
    try:
        key, period_s, periods = match_formats.resolve(MatchFormatKey(team.default_format or ""))
    except ValueError:  # no or a custom default: the template of the age group
        key, period_s, periods = match_formats.resolve(match_formats.default_for(team.is_youth))
    m = Match(
        organization_id=team.organization_id,
        team_id=team.id,
        season_id=season.id,
        opponent_id=opp.id,
        kickoff_at=datetime.fromisoformat(str(payload["kickoff_at"])),
        is_home=bool(payload["is_home"]),
        competition=(payload.get("competition") or None) and str(payload["competition"])[:120],
        venue=(payload.get("venue") or None) and str(payload["venue"])[:160],
        status=MatchStatus.SCHEDULED,
        source="official",
        format=key,
        period_s=period_s,
        periods=periods,
        official_provider=PROVIDER,
        official_game_id=int(payload["game_id"]),
    )
    ctx.db.add(m)
    await ctx.db.flush()
    return m


def _split_name(official: str | None) -> tuple[str, str]:
    """'MUSTER Luca' (game stats) -> ('Luca', 'Muster')."""
    words = (official or "").split()
    last = [w for w in words if w.isupper() and len(w) > 1]
    first = [w for w in words if w not in last]
    return " ".join(first), " ".join(w.capitalize() for w in last)


def _add(total: int | None, value: int | None) -> int | None:
    return total if value is None else (total or 0) + value


class _Stats:
    """A player's official statistics over the games read for the roster (STATS_GAMES): shown in
    the roster suggestion if the coach wants them (only organisers see suggestions)."""

    def __init__(self) -> None:
        self.games = self.goals = 0
        self.goalkeeper = False
        self.goals_7m: int | None = None
        self.attempts_7m: int | None = None
        self.suspensions: int | None = None
        self.saves: int | None = None
        self.shots_faced: int | None = None

    def add(self, a: ch.GameAppearance) -> None:
        self.games += 1
        self.goals += a.goals
        self.goalkeeper = self.goalkeeper or a.goalkeeper
        self.goals_7m = _add(self.goals_7m, a.goals_7m)
        self.attempts_7m = _add(self.attempts_7m, a.attempts_7m)
        self.suspensions = _add(self.suspensions, a.suspensions)
        if a.goalkeeper:
            self.saves = _add(self.saves, a.saves)
            self.shots_faced = _add(self.shots_faced, a.shots_faced)

    def payload(self) -> dict[str, Any]:
        return {
            "games": self.games,
            "goals": self.goals,
            "goals_7m": self.goals_7m,
            "attempts_7m": self.attempts_7m,
            "suspensions_2min": self.suspensions,
            "goalkeeper": self.goalkeeper,
            "saves": self.saves if self.goalkeeper else None,
            "shots_faced": self.shots_faced if self.goalkeeper else None,
        }


async def _roster(
    ctx: Ctx, team: Team, season: Season, games: list[ch.OfficialGame], suggest: _Suggester
) -> None:
    assert team.official_team_id is not None
    max_age = ch.DAY if not team.official_synced_at else ch.FRESH
    registered = {p.id: p for p in await ch.team_players(ctx.db, team.official_team_id, max_age)}
    players = dict(registered)
    played = [g for g in games if g.played and g.season_id >= ch.FIRST_LOG_SEASON]
    numbers: dict[int, int] = {}
    seen: Counter[int] = Counter()
    stats: dict[int, _Stats] = {}
    for g in played[-STATS_GAMES:]:  # oldest first: the newest number wins
        for a in await ch.game_players(ctx.db, g.id):
            if a.team_id != team.official_team_id:
                continue
            seen[a.player_id] += 1
            stats.setdefault(a.player_id, _Stats()).add(a)
            if a.number is not None:
                numbers[a.player_id] = a.number
            if not registered and a.player_id not in players and a.name:
                # no registered player list: the players of the games instead
                first, last = _split_name(a.name)
                players[a.player_id] = ch.OfficialPlayer(a.player_id, first, last)
    entries = {
        e.official_player_id: (e, p)
        for e, p in await ctx.db.execute(
            select(RosterEntry, Player)
            .join(Player, Player.id == RosterEntry.player_id)
            .where(
                RosterEntry.season_id == season.id,
                RosterEntry.official_provider == PROVIDER,
            )
        )
    }
    for pid, p in players.items():
        number = numbers.get(pid)
        if pid not in entries:
            suggest(
                "roster_add",
                f"player:{pid}",
                {
                    "official_player_id": pid,
                    "first_name": p.first_name,
                    "last_name": p.last_name,
                    "jersey_number": number,
                    "appearances": seen.get(pid, 0),
                    "stats": stats[pid].payload() if pid in stats else None,
                },
            )
            continue
        entry, player = entries[pid]
        if number is not None and entry.jersey_number != number:
            suggest(
                "roster_number",
                f"player:{pid}:{number}",
                {
                    "roster_entry_id": str(entry.id),
                    "player_id": str(player.id),
                    "first_name": player.first_name,
                    "last_name": player.last_name,
                    "from": entry.jersey_number,
                    "to": number,
                },
            )
    for left, (entry, player) in entries.items():
        if left is not None and left not in players and entry.active:
            suggest(
                "roster_left",
                f"player:{left}:left",
                {
                    "roster_entry_id": str(entry.id),
                    "player_id": str(player.id),
                    "first_name": player.first_name,
                    "last_name": player.last_name,
                    "jersey_number": entry.jersey_number,
                },
            )


async def _next_season(ctx: Ctx, team: Team, current: ch.Season, suggest: _Suggester) -> None:
    """Season change: the club's team of the new season with the same name (or the same place in
    the club's list) is proposed."""
    if team.official_season_id is None or team.official_season_id >= current.id:
        return
    detail = await ch.club(ctx.db, team.official_club_id or 0, current.id)
    if detail is None or not detail.teams:
        return
    org = await ctx.db.get(Organization, team.organization_id)
    old_name = ch.fold(team.name)
    candidates = [t for t in detail.teams if ch.fold(t.name) == old_name] or [
        t for t in detail.teams if org is not None and ch.fold(t.name) == ch.fold(org.name)
    ]
    if not candidates:
        return
    t = candidates[0]
    suggest(
        "season_new",
        f"season:{current.id}",
        {
            "official_team_id": t.id,
            "club_id": t.club_id,
            "season_id": current.id,
            "label": current.label,
            "starts_on": current.starts_on.isoformat(),
            "ends_on": current.ends_on.isoformat(),
            "name": t.name,
            "league": t.league,
            "group_id": t.group_id,
            "group_name": t.group_name,
        },
    )


async def sync_team(ctx: Ctx, team: Team, *, initial: bool = False) -> dict[str, int]:
    """Prefill (initial) or sync one team. Network errors become 503 for callers."""
    if team.official_team_id is None:
        raise ProblemError(409, "not-linked", "The team is not linked to the official data")
    # the claim may use what the search just read; a sync asks handball.ch again
    max_age = ch.HOURS_6 if initial else ch.FRESH
    try:
        current = await ch.current_season(ctx.db)
        games = [
            g
            for g in await ch.team_games(ctx.db, team.official_team_id, max_age=max_age)
            if g.season_id == team.official_season_id or not g.season_id
        ]
        season = await _season_row(
            ctx,
            team.organization_id,
            team.id,
            next((s for s in await ch.seasons(ctx.db) if s.id == team.official_season_id), current),
        )
        suggest = _Suggester(ctx, team, await _suggestions(ctx, team.id))
        counts = Counter[str]()
        existing = {
            m.official_game_id: m
            for m in (
                await ctx.db.scalars(
                    select(Match).where(
                        Match.team_id == team.id, Match.official_provider == PROVIDER
                    )
                )
            ).all()
        }
        opponents = {
            ch.fold(o.name): o
            for o in (
                await ctx.db.scalars(
                    select(Opponent).where(Opponent.organization_id == team.organization_id)
                )
            ).all()
        }
        now = _now()
        held = await _held_back(ctx, team, season, games, existing, now) if initial else set()
        held_new = 0
        for g in games:
            payload = _game_payload(g, team)
            home = bool(payload["is_home"])
            m = existing.get(g.id)
            if m is None:
                if g.id in held:  # over the plan's match limit: a suggestion instead
                    held_new += ("match_new", f"game:{g.id}") not in suggest.known
                    suggest("match_new", f"game:{g.id}", {**payload, "reason": PLAN_LIMIT})
                    continue
                if not initial:
                    suggest("match_new", f"game:{g.id}", payload)
                    continue
                m = await _new_match(ctx, team, season, payload, opponents)
                counts["matches_created"] += 1
            elif abs((m.kickoff_at - g.kickoff_at).total_seconds()) >= 60 or (
                g.venue and m.venue != g.venue
            ):
                suggest(
                    "match_moved",
                    f"game:{g.id}:{g.kickoff_at.isoformat()}:{g.venue or ''}",
                    {
                        **payload,
                        "match_id": str(m.id),
                        "from": {"kickoff_at": m.kickoff_at.isoformat(), "venue": m.venue},
                        "to": {"kickoff_at": g.kickoff_at.isoformat(), "venue": g.venue},
                    },
                )
            if _scores(m, g, home):
                counts["results"] += 1
            # past games with a game log: importable reports; later games are imported
            # automatically after the final whistle (run_due)
            if (
                initial
                and g.played
                and g.season_id >= ch.FIRST_LOG_SEASON
                and m.official_report_at is None
                and g.kickoff_at < now - REPORT_AFTER
            ):
                suggest("report", f"game:{g.id}", {**payload, "match_id": str(m.id)})
        await _roster(ctx, team, season, games, suggest)
        await _next_season(ctx, team, current, suggest)
        if team.official_group_id:
            state = dict(team.official_state or {})
            state["standing"] = await ch.standing(ctx.db, team.official_group_id, max_age)
            team.official_state = state
    except ch.UpstreamUnavailableError as exc:
        raise _unavailable(exc) from exc
    team.official_synced_at = _now()
    await ctx.db.flush()
    created = suggest.created
    return {
        "matches_created": counts["matches_created"],
        "matches_held_back": len(held),
        "results": counts["results"],
        "roster_suggestions": created["roster_add"]
        + created["roster_number"]
        + created["roster_left"],
        "report_suggestions": created["report"],
        "other_suggestions": created["match_new"]
        - held_new
        + created["match_moved"]
        + created["season_new"],
    }


async def _held_back(
    ctx: Ctx,
    team: Team,
    season: Season,
    games: list[ch.OfficialGame],
    existing: dict[int | None, Match],
    now: datetime,
) -> set[int]:
    """Games of the prefill that would exceed the plan's matches per season (enforcement on): the
    next upcoming games become matches first, then the most recent played ones; the rest are
    held back as match_new suggestions with reason plan_limit (acceptable after an upgrade)."""
    new = [g for g in games if g.id not in existing]
    left = await billing.matches_left(ctx, team.organization_id, team.id, season.id)
    if left is None or len(new) <= left:
        return set()
    upcoming = sorted(
        (g for g in new if not g.played and g.kickoff_at >= now), key=lambda g: g.kickoff_at
    )
    first = {g.id for g in upcoming}
    past = sorted((g for g in new if g.id not in first), key=lambda g: g.kickoff_at, reverse=True)
    return {g.id for g in (upcoming + past)[left:]}


async def sync_now(ctx: Ctx, team_id: uuid.UUID) -> dict[str, Any]:
    team = await org_service.get_team(ctx, team_id, Action.OFFICIAL_MANAGE)
    counts = await sync_team(ctx, team)
    await audit.record(ctx, "official.synced", target_type="team", target_id=team.id, data=counts)
    return {**counts, "synced_at": team.official_synced_at}


async def link(ctx: Ctx, team_id: uuid.UUID) -> dict[str, Any]:
    team = await org_service.get_team(ctx, team_id)
    if team.official_team_id is None:
        return {"linked": False}
    actor = ctx.require_actor()
    open_count = 0
    if can(actor, Action.OFFICIAL_MANAGE, team.id):
        open_count = int(
            await ctx.db.scalar(
                select(func.count(OfficialSuggestion.id)).where(
                    OfficialSuggestion.team_id == team.id, OfficialSuggestion.status == "open"
                )
            )
            or 0
        )
    state = team.official_state or {}
    return {
        "linked": True,
        "provider": team.official_provider,
        "official_team_id": team.official_team_id,
        "official_club_id": team.official_club_id,
        "official_group_id": team.official_group_id,
        "official_season_id": team.official_season_id,
        "league": state.get("league"),
        "group_name": state.get("group_name"),
        "synced_at": team.official_synced_at,
        "standing": state.get("standing") or [],
        "open_suggestions": open_count,
        "roster_stats": bool((team.settings or {}).get(ROSTER_STATS, False)),
    }


async def set_preferences(ctx: Ctx, team_id: uuid.UUID, roster_stats: bool) -> dict[str, Any]:
    """The organisers' choice whether the roster suggestions show the official statistics (a
    display preference for all organisers of the team; the data is in the payload either way)."""
    team = await org_service.get_team(ctx, team_id, Action.OFFICIAL_MANAGE)
    team.settings = {**(team.settings or {}), ROSTER_STATS: roster_stats}
    await audit.record(
        ctx,
        "official.preferences_updated",
        target_type="team",
        target_id=team.id,
        data={"roster_stats": roster_stats},
    )
    await ctx.db.flush()
    return await link(ctx, team_id)


# ---- suggestions -------------------------------------------------------------------------------


def _out(s: OfficialSuggestion, blocked: str | None = None) -> dict[str, Any]:
    return {
        "id": s.id,
        "kind": s.kind,
        "status": s.status,
        "payload": s.payload,
        "created_at": s.created_at,
        "resolved_at": s.resolved_at,
        "blocked": blocked,
    }


async def list_suggestions(
    ctx: Ctx, team_id: uuid.UUID, status: str | None = "open", kind: str | None = None
) -> list[dict[str, Any]]:
    """Open match_new suggestions carry blocked "plan_limit" while accepting them would exceed the
    plan's matches per season (gone after an upgrade)."""
    team = await org_service.get_team(ctx, team_id, Action.OFFICIAL_MANAGE)
    q = select(OfficialSuggestion).where(OfficialSuggestion.team_id == team_id)
    if status:
        q = q.where(OfficialSuggestion.status == status)
    if kind:
        q = q.where(OfficialSuggestion.kind == kind)
    rows = list(
        (
            await ctx.db.scalars(q.order_by(OfficialSuggestion.kind, OfficialSuggestion.created_at))
        ).all()
    )
    full = False
    if any(s.kind == "match_new" and s.status == "open" for s in rows):
        season = (await org_service.current_seasons(ctx, [team.id])).get(team.id)
        if season is not None:
            left = await billing.matches_left(ctx, team.organization_id, team.id, season.id)
            full = left is not None and left <= 0
    return [
        _out(s, PLAN_LIMIT if full and s.kind == "match_new" and s.status == "open" else None)
        for s in rows
    ]


async def _suggestion(
    ctx: Ctx, team_id: uuid.UUID, suggestion_id: uuid.UUID
) -> tuple[Team, OfficialSuggestion]:
    team = await org_service.get_team(ctx, team_id, Action.OFFICIAL_MANAGE)
    s = await ctx.db.get(OfficialSuggestion, suggestion_id)
    if s is None or s.team_id != team.id:
        raise ProblemError(404, "not-found", "Suggestion not found")
    if s.status != "open":
        raise ProblemError(409, "suggestion-resolved", "This suggestion was already decided")
    return team, s


async def _team_season(ctx: Ctx, team: Team) -> Season:
    season = (await org_service.current_seasons(ctx, [team.id])).get(team.id)
    if season is None:
        raise ProblemError(409, "no-season", "The team has no season")
    return season


async def number_free(ctx: Ctx, season_id: uuid.UUID, number: int | None) -> int | None:
    if number is None:
        return None
    taken = await ctx.db.scalar(
        select(RosterEntry.id).where(
            RosterEntry.season_id == season_id,
            RosterEntry.jersey_number == number,
            RosterEntry.active.is_(True),
        )
    )
    return None if taken else number


async def add_from_suggestion(
    ctx: Ctx, team: Team, s: OfficialSuggestion, number: int | None
) -> Player:
    p = s.payload
    season = await _team_season(ctx, team)
    player = Player(
        organization_id=team.organization_id,
        first_name=str(p.get("first_name") or "?")[:80],
        last_name=str(p.get("last_name") or "?")[:80],
    )
    ctx.db.add(player)
    await ctx.db.flush()
    ctx.db.add(
        RosterEntry(
            organization_id=team.organization_id,
            player_id=player.id,
            team_id=team.id,
            season_id=season.id,
            jersey_number=await number_free(ctx, season.id, number),
            active=True,
            official_provider=PROVIDER,
            official_player_id=int(p["official_player_id"]),
        )
    )
    await ctx.db.flush()
    return player


async def _resolve(ctx: Ctx, s: OfficialSuggestion, status: str) -> None:
    s.status, s.resolved_by_id, s.resolved_at = status, ctx.user_id, _now()
    await audit.record(
        ctx,
        f"official.suggestion_{status}",
        target_type="official_suggestion",
        target_id=s.id,
        data={"kind": s.kind},
    )


async def import_report(ctx: Ctx, match: Match) -> dict[str, Any]:
    """The official report of a linked match; opponent names stay out while the club is not
    verified (numbers only)."""
    assert match.official_game_id is not None
    report = official_report.parse_handball_ch(
        match.official_game_id, await official_report.fetch_handball_ch(match.official_game_id)
    )
    if not report.entries:
        raise ProblemError(422, "report-empty", "The report has no game log yet")
    if await org_verification.is_unverified(ctx, match.organization_id):
        report = official_report.without_opponent_names(report, match.is_home)
    result = await official_report.apply(ctx, match, report)
    match.official_report_at = _now()
    pending = await ctx.db.scalar(
        select(OfficialSuggestion).where(
            OfficialSuggestion.team_id == match.team_id,
            OfficialSuggestion.kind == "report",
            OfficialSuggestion.official_key == f"game:{match.official_game_id}",
            OfficialSuggestion.status == "open",
        )
    )
    if pending is not None:  # imported: the suggestion is done
        pending.status, pending.resolved_at = "accepted", _now()
    if report.final and match.score_own is None:
        own, opp = report.final if match.is_home else report.final[::-1]
        match.score_own, match.score_opponent = own, opp
    return result


async def accept(
    ctx: Ctx, team_id: uuid.UUID, suggestion_id: uuid.UUID, data: SuggestionAcceptIn
) -> dict[str, Any]:
    team, s = await _suggestion(ctx, team_id, suggestion_id)
    p = s.payload
    out: dict[str, Any] = {}
    if s.kind == "roster_add":
        number = data.jersey_number if "jersey_number" in data.model_fields_set else None
        if "jersey_number" not in data.model_fields_set:
            number = p.get("jersey_number")
        out["player_id"] = (await add_from_suggestion(ctx, team, s, number)).id
    elif s.kind in ("roster_number", "roster_left"):
        entry = await ctx.db.get(RosterEntry, uuid.UUID(str(p["roster_entry_id"])))
        if entry is None or entry.team_id != team.id:
            raise ProblemError(409, "suggestion-stale", "The roster entry no longer exists")
        if s.kind == "roster_left":
            entry.active = False
        else:
            number = await number_free(ctx, entry.season_id, int(p["to"]))
            if number is None:
                raise ProblemError(409, "jersey-number-taken", "The number is taken")
            entry.jersey_number = number
        out["player_id"] = entry.player_id
    elif s.kind in ("match_new", "match_moved", "report"):
        if s.kind == "match_new":
            season = await _team_season(ctx, team)
            # official games count toward the plan's matches per season (402 plan-limit-matches)
            await billing.check_new_match(ctx, team.organization_id, team.id, season.id)
            m = await _new_match(ctx, team, season, p, {})
            await _played_match(ctx, team, m, p)
        else:
            found = await ctx.db.get(Match, uuid.UUID(str(p["match_id"])))
            if found is None or found.team_id != team.id:
                raise ProblemError(409, "suggestion-stale", "The match no longer exists")
            m = found
        if s.kind == "match_moved":
            to = p["to"]
            m.kickoff_at = datetime.fromisoformat(str(to["kickoff_at"]))
            m.venue = (to.get("venue") or None) and str(to["venue"])[:160]
        if s.kind == "report":
            try:
                out["report"] = await import_report(ctx, m)
            except ch.UpstreamUnavailableError as exc:
                raise _unavailable(exc) from exc
        out["match_id"] = m.id
    elif s.kind == "season_new":
        out["season_id"] = await _start_season(ctx, team, p)
    await _resolve(ctx, s, "accepted")
    await ctx.db.flush()
    return {"suggestion": s, **out}


async def _played_match(ctx: Ctx, team: Team, m: Match, p: dict[str, Any]) -> None:
    """A past game accepted later (held back by the plan limit at the claim): its result, and
    its official report as a suggestion like at the claim."""
    if not p.get("played"):
        return
    own, opp = p.get("score_own"), p.get("score_opponent")
    if m.score_own is None and own is not None and opp is not None:
        m.score_own, m.score_opponent = int(own), int(opp)
    if m.kickoff_at < _now() - REPORT_AFTER:
        suggest = _Suggester(ctx, team, await _suggestions(ctx, team.id))
        payload = {k: v for k, v in p.items() if k != "reason"}
        suggest("report", f"game:{m.official_game_id}", {**payload, "match_id": str(m.id)})


async def _start_season(ctx: Ctx, team: Team, p: dict[str, Any]) -> uuid.UUID:
    clash = await ctx.db.scalar(
        select(Team.id).where(
            Team.official_provider == PROVIDER,
            Team.official_team_id == int(p["official_team_id"]),
            Team.id != team.id,
        )
    )
    if clash is not None:
        raise ProblemError(409, "team-already-linked", "Another team is linked to it")
    season = ch.Season(
        id=int(p["season_id"]),
        label=str(p["label"]),
        starts_on=datetime.fromisoformat(str(p["starts_on"])).date(),
        ends_on=datetime.fromisoformat(str(p["ends_on"])).date(),
        current=True,
    )
    row = await _season_row(ctx, team.organization_id, team.id, season)
    team.official_team_id = int(p["official_team_id"])
    team.official_group_id = p.get("group_id")
    team.official_season_id = season.id
    team.official_state = {"league": p.get("league"), "group_name": p.get("group_name")}
    if p.get("league"):
        team.league = str(p["league"])[:120]
    await ctx.db.flush()
    await sync_team(ctx, team, initial=True)
    return row.id


async def dismiss(ctx: Ctx, team_id: uuid.UUID, suggestion_id: uuid.UUID) -> OfficialSuggestion:
    _, s = await _suggestion(ctx, team_id, suggestion_id)
    await _resolve(ctx, s, "dismissed")
    return s


# ---- access requests (a second person finds a claimed club) ------------------------------------


async def list_access_requests(ctx: Ctx) -> list[tuple[OrgAccessRequest, User]]:
    authorize(ctx.require_actor(), Action.ORG_ACCESS_MANAGE, two_factor=ctx.two_factor)
    rows = await ctx.db.execute(
        select(OrgAccessRequest, User)
        .join(User, User.id == OrgAccessRequest.user_id)
        .where(OrgAccessRequest.status == "pending")
        .order_by(OrgAccessRequest.created_at)
    )
    return [(r, u) for r, u in rows]


async def _access_request(ctx: Ctx, request_id: uuid.UUID) -> OrgAccessRequest:
    actor = ctx.require_actor()
    authorize(actor, Action.ORG_ACCESS_MANAGE, two_factor=ctx.two_factor)
    req = await ctx.db.get(OrgAccessRequest, request_id)
    if req is None or req.organization_id != actor.organization_id:
        raise ProblemError(404, "not-found", "Request not found")
    if req.status != "pending":
        raise ProblemError(409, "request-decided", "This request was already decided")
    return req


async def approve_access(
    ctx: Ctx, org: Organization, request_id: uuid.UUID, data: AccessApproveIn
) -> OrgAccessRequest:
    req = await _access_request(ctx, request_id)
    om = await ctx.db.scalar(
        select(OrgMembership).where(
            OrgMembership.organization_id == org.id, OrgMembership.user_id == req.user_id
        )
    )
    if om is None:
        ctx.db.add(OrgMembership(organization_id=org.id, user_id=req.user_id, role=data.org_role))
    elif data.org_role == OrgRole.ORG_ADMIN:
        om.role = OrgRole.ORG_ADMIN
    team_id = req.team_id
    if team_id is None and req.official_team_id is not None:
        # the team is not in the app yet: created from the official data, the person coaches it
        _, _, oteam = await _official_team(ctx, org.official_club_id or 0, req.official_team_id)
        season = await ch.current_season(ctx.db)
        team = await _create_team(ctx, org, season, oteam, req.user_id, role=data.team_role)
        await sync_team(ctx, team, initial=True)
        team_id = team.id
    elif team_id is not None:
        m = await ctx.db.scalar(
            select(Membership).where(
                Membership.team_id == team_id, Membership.user_id == req.user_id
            )
        )
        if m is None:
            ctx.db.add(
                Membership(
                    organization_id=org.id,
                    team_id=team_id,
                    user_id=req.user_id,
                    role=data.team_role,
                )
            )
    req.team_id = team_id
    req.status, req.decided_by_id, req.decided_at = "approved", ctx.user_id, _now()
    await training.notify(
        ctx,
        org.id,
        [req.user_id],
        "access_approved",
        {"organization_id": str(org.id)},
        f"/app/{org.id}",
    )
    await audit.record(
        ctx,
        "org.access_approved",
        target_type="org_access_request",
        target_id=req.id,
        data={"user_id": str(req.user_id), "org_role": data.org_role, "team_role": data.team_role},
    )
    await ctx.db.flush()
    return req


async def decline_access(ctx: Ctx, request_id: uuid.UUID) -> OrgAccessRequest:
    req = await _access_request(ctx, request_id)
    req.status, req.decided_by_id, req.decided_at = "declined", ctx.user_id, _now()
    await audit.record(
        ctx, "org.access_declined", target_type="org_access_request", target_id=req.id
    )
    return req


async def my_access_requests(ctx: Ctx, user: User) -> list[tuple[OrgAccessRequest, str]]:
    await enable_system_access(ctx.db, reason="own access requests")
    try:
        rows = await ctx.db.execute(
            select(OrgAccessRequest, Organization.name)
            .join(Organization, Organization.id == OrgAccessRequest.organization_id)
            .where(OrgAccessRequest.user_id == user.id)
            .order_by(OrgAccessRequest.created_at.desc())
        )
        return [(r, n) for r, n in rows]
    finally:
        await disable_system_access(ctx.db)


# ---- worker tick -------------------------------------------------------------------------------


def _system_actor(org_id: uuid.UUID) -> Actor:
    return Actor(user_id=SYSTEM_USER, organization_id=org_id, org_role=OrgRole.ORG_ADMIN)


async def _organisers(ctx: Ctx, team_id: uuid.UUID) -> list[uuid.UUID]:
    rows = await ctx.db.scalars(
        select(Membership.user_id).where(
            Membership.team_id == team_id,
            Membership.role.in_([TeamRole.COACH, TeamRole.TEAM_MANAGER]),
        )
    )
    return list(rows.all())


async def run_due(ctx: Ctx, now: datetime | None = None) -> dict[str, int]:
    """Hourly worker tick: each linked team once a day (schedule, roster, standing, next season
    as suggestions) and the official report of every linked game that ended. Stops at the first
    sign that handball.ch is not answering (no hammering)."""
    now = now or _now()
    await enable_system_access(ctx.db, reason="official data sync")
    try:
        teams = list(
            (
                await ctx.db.scalars(
                    select(Team)
                    .where(
                        Team.official_team_id.is_not(None),
                        (Team.official_synced_at.is_(None))
                        | (Team.official_synced_at < now - SYNC_EVERY),
                    )
                    .order_by(Team.official_synced_at.nulls_first())
                    .limit(SYNC_BATCH)
                )
            ).all()
        )
        games = list(
            (
                await ctx.db.scalars(
                    select(Match)
                    .where(
                        Match.official_game_id.is_not(None),
                        Match.official_report_at.is_(None),
                        Match.kickoff_at < now - REPORT_AFTER,
                        Match.kickoff_at > now - REPORT_WINDOW,
                    )
                    .order_by(Match.kickoff_at)
                    .limit(REPORT_BATCH)
                )
            ).all()
        )
    finally:
        await disable_system_access(ctx.db)
    out = Counter[str]()
    try:
        for team in teams:
            await set_tenant(ctx.db, team.organization_id)
            ctx.actor = _system_actor(team.organization_id)
            counts = await sync_team(ctx, team)
            out["teams"] += 1
            new = counts["roster_suggestions"] + counts["other_suggestions"]
            out["suggestions"] += new
            if new:
                await training.notify(
                    ctx,
                    team.organization_id,
                    await _organisers(ctx, team.id),
                    "official_suggestions",
                    {"team_id": str(team.id), "count": new},
                    f"/app/{team.organization_id}/teams/{team.id}/official",
                )
        for m in games:
            await set_tenant(ctx.db, m.organization_id)
            ctx.actor = _system_actor(m.organization_id)
            try:
                await import_report(ctx, m)
            except ProblemError as exc:
                if exc.code == "report-unavailable":
                    raise
                continue  # no log yet: next tick
            out["reports"] += 1
            await training.notify(
                ctx,
                m.organization_id,
                await training.staff_of(ctx, m.team_id),
                "official_report",
                {"match_id": str(m.id)},
                f"/app/{m.organization_id}/matches/{m.id}",
            )
    except ProblemError as exc:
        if exc.code not in ("official-unavailable", "report-unavailable"):
            raise
        out["stopped"] = 1
    finally:
        ctx.actor = None
    await ctx.db.flush()
    return {k: out[k] for k in ("teams", "suggestions", "reports", "stopped")}
