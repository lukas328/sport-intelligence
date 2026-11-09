"""A player's season line: per played match the player's figures with the events behind them.

Figures come from the match statistics (`events.stats_for`, one source per goal), so they
agree with the match page; the event ids from `handball_metrics.stats.player_event_ids`,
which applies the same rules to the same events. Matches as in the season statistics: every
played match of the team's season (a result stored or events)."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from sqlalchemy import select

from handball_api.core.errors import ProblemError
from handball_api.models import Attendance, Event, Match, Opponent, Player, RosterEntry
from handball_api.models.enums import AttendanceStatus
from handball_api.schemas.season_line import (
    LineEvents,
    LineFigures,
    SeasonLine,
    SeasonLineMatch,
    SeasonLineTotals,
)
from handball_api.services import billing, roster
from handball_api.services import events as events_service
from handball_api.services.context import Ctx
from handball_api.services.events import _to_metric
from handball_api.services.insights import _played_matches
from handball_api.services.orgs import get_season, get_team
from handball_api.services.policies import Action, can
from handball_metrics.stats import LINE_KEYS, player_event_ids

# figures the match statistics count per field player (`players`) and per goalkeeper
FIELD_KEYS = (
    "goals",
    "shots",
    "misses",
    "posts",
    "saved",
    "blocked",
    "seven_m_goals",
    "seven_m_shots",
    "assists",
    "turnovers",
    "suspensions",
)
PRESENT = (AttendanceStatus.PRESENT, AttendanceStatus.LATE)


def _ratio(a: int, b: int) -> float | None:
    return round(a / b, 4) if b else None


def _figures(stats: dict[str, Any], pid: str, ids: dict[str, list[str]]) -> LineFigures:
    """From the match statistics; cards (not counted per player there) from the events."""
    field = stats["players"].get(f"p:{pid}", {})
    keeper = stats["goalkeepers"].get(f"own:p:{pid}", {})
    seven = keeper.get("seven_m", {})
    return LineFigures(
        **{k: field.get(k, 0) for k in FIELD_KEYS},
        yellow_cards=len(ids["yellow_cards"]),
        red_cards=len(ids["red_cards"]),
        faced=keeper.get("faced", 0),
        saves=keeper.get("saves", 0),
        goals_against=keeper.get("goals_against", 0),
        seven_m_faced=seven.get("faced", 0),
        seven_m_saves=seven.get("saves", 0),
    )


def _result(own: int | None, opp: int | None) -> Literal["win", "draw", "loss"] | None:
    if own is None or opp is None:
        return None
    return "win" if own > opp else "loss" if own < opp else "draw"


async def season_line(
    ctx: Ctx, team_id: uuid.UUID, season_id: uuid.UUID, player_id: uuid.UUID
) -> SeasonLine:
    """The staff read every player of the team, a player only their own line; entries from
    the official data follow the roster list's rule (`roster.visible_players`)."""
    team = await get_team(ctx, team_id, Action.MATCH_READ)
    await billing.require_feature(ctx, "season", team.organization_id)
    await get_season(ctx, team_id, season_id)
    row = (
        await ctx.db.execute(
            select(RosterEntry, Player)
            .join(Player, Player.id == RosterEntry.player_id)
            .where(
                RosterEntry.season_id == season_id,
                RosterEntry.team_id == team_id,
                RosterEntry.player_id == player_id,
            )
        )
    ).first()
    if row is None:
        raise ProblemError(404, "not-found", "Player not found in this season")
    entry, player = row
    if not can(ctx.require_actor(), Action.PLAYER_LINE_READ_ALL, team_id) and (
        player.user_id is None or player.user_id != ctx.user_id
    ):
        raise ProblemError(403, "forbidden", "Players see only their own season line")
    visible = await roster.visible_players(ctx, team_id, season_id)
    if visible is not None and player.id not in visible:
        raise ProblemError(404, "not-found", "Player not found in this season")

    matches = await _played_matches(ctx, team_id, season_id)
    match_ids = [m.id for m in matches]
    names: dict[uuid.UUID, str] = {}
    events: dict[uuid.UUID, list[Event]] = {}
    attendance: dict[uuid.UUID, Attendance] = {}
    if matches:
        names = {
            o.id: o.name
            for o in await ctx.db.scalars(
                select(Opponent).where(Opponent.id.in_([m.opponent_id for m in matches]))
            )
        }
        for e in await ctx.db.scalars(select(Event).where(Event.match_id.in_(match_ids))):
            events.setdefault(e.match_id, []).append(e)
        attendance = {
            a.match_id: a
            for a in await ctx.db.scalars(
                select(Attendance).where(
                    Attendance.match_id.in_(match_ids), Attendance.player_id == player.id
                )
            )
            if a.match_id is not None
        }
    pid = str(player.id)
    lines: list[SeasonLineMatch] = []
    for m in matches:
        lines.append(await _match_line(ctx, m, pid, events.get(m.id, []), names, attendance))
    return SeasonLine(
        player_id=player.id,
        team_id=team_id,
        season_id=season_id,
        first_name=player.first_name,
        last_name=player.last_name,
        jersey_number=entry.jersey_number,
        main_position=player.main_position,
        matches=lines,
        totals=_totals(lines),
    )


async def _match_line(
    ctx: Ctx,
    m: Match,
    pid: str,
    rows: list[Event],
    names: dict[uuid.UUID, str],
    attendance: dict[uuid.UUID, Attendance],
) -> SeasonLineMatch:
    stats = await events_service.stats_for(ctx, m)
    ids = player_event_ids([_to_metric(e) for e in rows], pid)
    figures = _figures(stats, pid, ids)
    own = m.score_own if m.score_own is not None else stats["own"]["goals"]
    opp = m.score_opponent if m.score_opponent is not None else stats["opponent"]["goals"]
    tagged = bool(stats["quality"]["events"])
    att = attendance.get(m.id)
    return SeasonLineMatch(
        match_id=m.id,
        kickoff_at=m.kickoff_at,
        opponent=names.get(m.opponent_id, "") if m.opponent_id else "",
        is_home=m.is_home,
        competition=m.competition,
        score_own=own,
        score_opponent=opp,
        result=_result(own, opp),
        tagged=tagged,
        involved=any(ids[k] for k in LINE_KEYS),
        attendance=att.status if att else None,
        response=att.response if att else None,
        figures=figures,
        shooting_pct=_ratio(figures.goals, figures.shots),
        save_pct=_ratio(figures.saves, figures.faced),
        events=LineEvents(**{k: [uuid.UUID(i) for i in v] for k, v in ids.items()}),
    )


def _totals(lines: list[SeasonLineMatch]) -> SeasonLineTotals:
    sums = {k: sum(getattr(line.figures, k) for line in lines) for k in LINE_KEYS}
    return SeasonLineTotals(
        **sums,
        matches=len(lines),
        tagged_matches=sum(line.tagged for line in lines),
        matches_involved=sum(line.involved for line in lines),
        matches_present=sum(line.attendance in PRESENT for line in lines),
        shooting_pct=_ratio(sums["goals"], sums["shots"]),
        save_pct=_ratio(sums["saves"], sums["faced"]),
    )
