"""Import of paper match reports as matches without video (BRIEF 15, source "paper_report").

Format: docs/schemas/paper-report.schema.json (assumed until the club's schema arrives, Q-DATA-2).
Counts become events without clock time, so all statistics and the season view use them.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, time
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select

from handball_api.core.errors import ProblemError
from handball_api.models import Event, Match, RosterEntry, Season
from handball_api.models.enums import MatchStatus
from handball_api.schemas.matches import OpponentCreate
from handball_api.services import audit
from handball_api.services.context import Ctx
from handball_api.services.matches import create_opponent
from handball_api.services.orgs import current_seasons, get_team
from handball_api.services.policies import Action

ZONES = ("TL", "TC", "TR", "ML", "MC", "MR", "BL", "BC", "BR")
FAULTS = (
    "bad_pass",
    "catch_error",
    "steps",
    "double_dribble",
    "offensive_foul",
    "line_violation",
    "passive_play",
    "other",
)


class _Score(BaseModel):
    own: int = Field(ge=0, le=99)
    opponent: int = Field(ge=0, le=99)


class _Player(BaseModel):
    number: int = Field(ge=1, le=99)
    name: str | None = None
    goals: int = Field(default=0, ge=0, le=40)
    misses: int = Field(default=0, ge=0, le=40)
    posts: int = Field(default=0, ge=0, le=40)
    blocked: int = Field(default=0, ge=0, le=40)
    seven_m_goals: int = Field(default=0, ge=0, le=20)
    seven_m_misses: int = Field(default=0, ge=0, le=20)
    technical_faults: dict[str, int] = Field(default_factory=dict)
    suspensions: int = Field(default=0, ge=0, le=3)
    assists: int = Field(default=0, ge=0, le=40)


class _Keeper(BaseModel):
    number: int
    name: str | None = None
    saves: int = Field(default=0, ge=0, le=60)
    goals_against_by_zone: dict[str, list[int | None]] = Field(default_factory=dict)


class _Progress(BaseModel):
    minute: int = Field(ge=0, le=70)
    own: int = Field(ge=0)
    opponent: int = Field(ge=0)


class PaperReport(BaseModel):
    schema_: str = Field(alias="schema", pattern=r"^handball-paper-report/1$")
    date: str
    kickoff: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    opponent: str = Field(min_length=1, max_length=120)
    home: bool = True
    competition: str | None = None
    venue: str | None = None
    score: _Score
    halftime: _Score | None = None
    players: list[_Player] = Field(max_length=40)
    goalkeepers: list[_Keeper] = Field(default_factory=list, max_length=6)
    score_progression: list[_Progress] = Field(default_factory=list, max_length=30)
    tactics_notes: dict[str, str] = Field(default_factory=dict)


async def import_report(ctx: Ctx, team_id: uuid.UUID, data: bytes) -> dict[str, Any]:
    team = await get_team(ctx, team_id, Action.MATCH_WRITE)
    try:
        report = PaperReport.model_validate(json.loads(data.decode("utf-8-sig")))
    except (ValueError, ValidationError) as exc:
        raise ProblemError(
            422, "invalid-report", f"Not a valid paper report: {str(exc)[:300]}"
        ) from exc
    for p in report.players:
        unknown = set(p.technical_faults) - set(FAULTS)
        if unknown:
            raise ProblemError(
                422, "invalid-report", f"Unknown technical fault types: {sorted(unknown)}"
            )
    for gk in report.goalkeepers:
        if set(gk.goals_against_by_zone) - set(ZONES):
            raise ProblemError(422, "invalid-report", "Unknown goal zone in goals_against_by_zone")
    hh, mm = (int(v) for v in (report.kickoff or "18:00").split(":"))
    kickoff = datetime.combine(
        datetime.fromisoformat(report.date).date(), time(hh, mm), tzinfo=ZoneInfo("Europe/Zurich")
    ).astimezone(UTC)
    # the season that contains the match date, else the current one
    season = await ctx.db.scalar(
        select(Season).where(
            Season.team_id == team.id,
            Season.starts_on <= kickoff.date(),
            Season.ends_on >= kickoff.date(),
        )
    ) or (await current_seasons(ctx, [team.id])).get(team.id)
    if season is None:
        raise ProblemError(409, "no-season", "The team has no season")
    opp = await create_opponent(ctx, OpponentCreate(name=report.opponent))
    match = Match(
        organization_id=team.organization_id,
        team_id=team.id,
        season_id=season.id,
        opponent_id=opp.id,
        kickoff_at=kickoff,
        is_home=report.home,
        competition=report.competition,
        venue=report.venue,
        score_own=report.score.own,
        score_opponent=report.score.opponent,
        halftime_own=report.halftime.own if report.halftime else None,
        halftime_opponent=report.halftime.opponent if report.halftime else None,
        status=MatchStatus.READY,
        source="paper_report",
        report_extra={
            "score_progression": [p.model_dump() for p in report.score_progression],
            "tactics_notes": report.tactics_notes,
            # names as written on the sheet, used where a number is not in the roster
            "names": {
                **{str(k.number): k.name for k in report.goalkeepers if k.name},
                **{str(p.number): p.name for p in report.players if p.name},
            },
        },
    )
    ctx.db.add(match)
    await ctx.db.flush()
    numbers = {
        n: pid
        for n, pid in (
            await ctx.db.execute(
                select(RosterEntry.jersey_number, RosterEntry.player_id).where(
                    RosterEntry.season_id == season.id, RosterEntry.active.is_(True)
                )
            )
        ).all()
        if n is not None
    }

    def ev(**kw: Any) -> Event:
        return Event(
            organization_id=team.organization_id,
            match_id=match.id,
            source="paper_report",
            confidence=1.0,
            period=1,
            attributes={},
            **kw,
        )

    events: list[Event] = []
    unmatched: list[int] = []
    for p in report.players:
        pid = numbers.get(p.number)
        if pid is None:
            unmatched.append(p.number)
        base = {"side": "own", "player_id": pid, "number": p.number}
        events += [ev(type="shot", outcome="goal", **base) for _ in range(p.goals)]
        events += [ev(type="shot", outcome="miss", **base) for _ in range(p.misses)]
        events += [ev(type="shot", outcome="post", **base) for _ in range(p.posts)]
        events += [ev(type="shot", outcome="blocked", **base) for _ in range(p.blocked)]
        events += [
            ev(type="shot", outcome="goal", shot_type="penalty", shot_zone="penalty", **base)
            for _ in range(p.seven_m_goals)
        ]
        events += [
            ev(type="shot", outcome="miss", shot_type="penalty", shot_zone="penalty", **base)
            for _ in range(p.seven_m_misses)
        ]
        for kind, n in p.technical_faults.items():
            events += [ev(type="turnover", turnover_type=kind, **base) for _ in range(n)]
        events += [ev(type="suspension_2min", **base) for _ in range(p.suspensions)]
    for gk in report.goalkeepers:
        gk_pid = numbers.get(gk.number)
        attrs = {"goalkeeper_id": str(gk_pid)} if gk_pid else {"goalkeeper_number": gk.number}
        for _ in range(gk.saves):
            e = ev(type="shot", side="opponent", outcome="save")
            e.attributes = dict(attrs)
            events.append(e)
        for zone, shooters in gk.goals_against_by_zone.items():
            for num in shooters:
                e = ev(type="shot", side="opponent", outcome="goal", goal_zone=zone, number=num)
                e.attributes = dict(attrs)
                events.append(e)
    own_goals = sum(p.goals + p.seven_m_goals for p in report.players)
    zone_goals = sum(len(v) for gk in report.goalkeepers for v in gk.goals_against_by_zone.values())
    # opponent goals that are not broken down by zone still count for the score
    for _ in range(max(0, report.score.opponent - zone_goals)):
        events.append(ev(type="shot", side="opponent", outcome="goal"))
    ctx.db.add_all(events)
    warnings = []
    if own_goals != report.score.own:
        warnings.append(
            f"player goals ({own_goals}) differ from the final score ({report.score.own})"
        )
    if zone_goals > report.score.opponent:
        warnings.append(
            f"goals by zone ({zone_goals}) exceed the opponent score ({report.score.opponent})"
        )
    if unmatched:
        warnings.append(f"numbers not in the roster: {sorted(set(unmatched))}")
    await audit.record(
        ctx,
        "match.paper_report_imported",
        target_type="match",
        target_id=match.id,
        data={"events": len(events), "warnings": len(warnings)},
    )
    return {"match_id": str(match.id), "events": len(events), "warnings": warnings}
