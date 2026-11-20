"""Sync: prefill at the claim, daily (worker tick) and on demand; changes come in as
suggestions."""

from __future__ import annotations

import uuid
from collections import Counter
from datetime import datetime
from typing import Any

from sqlalchemy import func, select

from handball_api.core.errors import ProblemError
from handball_api.integrations import handball_ch as ch
from handball_api.models import (
    Match,
    OfficialSuggestion,
    Opponent,
    Organization,
    Player,
    RosterEntry,
    Season,
    Team,
)
from handball_api.models.enums import (
    MatchFormatKey,
    MatchStatus,
)
from handball_api.services import (
    audit,
    billing,
    match_formats,
)
from handball_api.services import orgs as org_service
from handball_api.services.context import Ctx
from handball_api.services.official._base import (
    PLAN_LIMIT,
    PROVIDER,
    REPORT_AFTER,
    ROSTER_STATS,
    STATS_GAMES,
    _now,
    _unavailable,
)
from handball_api.services.policies import Action, can


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


async def _opponents(ctx: Ctx, org_id: uuid.UUID) -> dict[str, Opponent]:
    """The club's opponents by name key: «X 1» and «X (M2)» are one opponent (review R7). Of two
    rows with the same key (made before the key existed) the oldest stays the one used."""
    rows = await ctx.db.scalars(
        select(Opponent)
        .where(Opponent.organization_id == org_id)
        .order_by(Opponent.created_at.desc())
    )
    return {ch.opponent_key(o.name): o for o in rows.all()}


async def _opponent(ctx: Ctx, org_id: uuid.UUID, name: str, cache: dict[str, Opponent]) -> Opponent:
    key = ch.opponent_key(name)
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
    # our shirts: the club's colour, as for a match made by hand (review R16: synced matches
    # showed the default blue at the upload of a club in green)
    org = await ctx.db.get(Organization, team.organization_id)
    kit = {"kit_own": org.club_colour} if org is not None else {}
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
        **kit,
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
        opponents = await _opponents(ctx, team.organization_id)
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
