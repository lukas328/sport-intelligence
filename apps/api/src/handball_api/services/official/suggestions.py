"""Suggestions of the sync: list, accept, dismiss; the official report import."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select

from handball_api.core.errors import ProblemError
from handball_api.integrations import handball_ch as ch
from handball_api.models import (
    Match,
    OfficialSuggestion,
    Player,
    RosterEntry,
    Season,
    Team,
)
from handball_api.models.enums import (
    Position,
)
from handball_api.schemas.official import SuggestionAcceptIn
from handball_api.services import (
    audit,
    billing,
    official_report,
    org_verification,
)
from handball_api.services import orgs as org_service
from handball_api.services import roster as roster_service
from handball_api.services.context import Ctx
from handball_api.services.official._base import (
    PLAN_LIMIT,
    PROVIDER,
    REPORT_AFTER,
    _now,
    _unavailable,
)
from handball_api.services.official.sync import (
    _new_match,
    _opponents,
    _season_row,
    _Suggester,
    _suggestions,
    sync_team,
)
from handball_api.services.policies import Action

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
    raw = p.get("stats")
    stats: dict[str, Any] = raw if isinstance(raw, dict) else {}
    player = Player(
        organization_id=team.organization_id,
        first_name=str(p.get("first_name") or "?")[:80],
        last_name=str(p.get("last_name") or "?")[:80],
        # a goalkeeper in the federation's statistics is the roster's goalkeeper (R4)
        main_position=Position.TW if stats.get("goalkeeper") else None,
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
    # the reports read before the player was in the roster count for the player now (R3)
    await roster_service.link_numbers(ctx, season.id, team.id)
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
        await ctx.db.flush()
        await roster_service.link_numbers(ctx, entry.season_id, entry.team_id)
        out["player_id"] = entry.player_id
    elif s.kind in ("match_new", "match_moved", "report"):
        if s.kind == "match_new":
            season = await _team_season(ctx, team)
            # official games count toward the plan's matches per season (402 plan-limit-matches)
            await billing.check_new_match(ctx, team.organization_id, team.id, season.id)
            m = await _new_match(ctx, team, season, p, await _opponents(ctx, team.organization_id))
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
