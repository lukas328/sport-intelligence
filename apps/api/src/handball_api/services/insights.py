"""Match insights, season statistics and summaries (M7)."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from handball_api.core.errors import ProblemError
from handball_api.core.text import numbers_ok
from handball_api.models import Event, Match, Opponent, RosterEntry
from handball_api.services import events as events_service
from handball_api.services.context import Ctx
from handball_api.services.matches import get_match
from handball_api.services.orgs import get_team
from handball_api.services.policies import Action
from handball_metrics.insights import VERSION, match_insights


async def _matches_with_events(ctx: Ctx, team_id: uuid.UUID, season_id: uuid.UUID) -> list[Match]:
    has_events = select(Event.match_id).distinct()
    return list(
        (
            await ctx.db.scalars(
                select(Match)
                .where(
                    Match.team_id == team_id,
                    Match.season_id == season_id,
                    Match.id.in_(has_events),
                )
                .order_by(Match.kickoff_at)
            )
        ).all()
    )


async def insights(ctx: Ctx, match_id: uuid.UUID) -> dict[str, Any]:
    match = await get_match(ctx, match_id)
    stats = await events_service.match_stats(ctx, match.id)
    others = [
        m
        for m in await _matches_with_events(ctx, match.team_id, match.season_id)
        if m.id != match.id
    ]
    baseline = [await events_service.match_stats(ctx, m.id) for m in others]
    items = match_insights(stats, baseline) if stats["quality"]["events"] else []
    summary = (match.report_extra or {}).get("summary")
    fingerprint = _fingerprint(items)
    return {
        "version": VERSION,
        "baseline_matches": len(baseline),
        "insights": items,
        "summary": summary if summary and summary.get("fingerprint") == fingerprint else None,
    }


def _fingerprint(items: list[dict[str, Any]]) -> str:
    return hashlib.sha256(json.dumps(items, sort_keys=True).encode()).hexdigest()[:24]


async def summarise(ctx: Ctx, match_id: uuid.UUID) -> dict[str, Any]:
    """Optional prose summary from the insights; only stored when every number checks out."""
    match = await get_match(ctx, match_id, Action.EVENT_WRITE)
    if ctx.text is None:
        raise ProblemError(503, "text-unavailable", "Text generation is not configured")
    data = await insights(ctx, match.id)
    if not data["insights"]:
        raise ProblemError(409, "no-insights", "Not enough data for a summary")
    numbers = await _jersey_numbers(ctx, match.season_id)
    opponent = await ctx.db.get(Opponent, match.opponent_id)
    facts = {
        "gegner": opponent.name if opponent else None,
        "resultat": {"wir": match.score_own, "gegner": match.score_opponent},
        "erkenntnisse": [_fact(i, numbers) for i in data["insights"]],
    }
    allowed: set[float] = {float(n) for i in data["insights"] for n in i["numbers"]}
    allowed |= {float(v) for v in (match.score_own, match.score_opponent) if v is not None}
    allowed |= {float(n) for n in numbers.values()}
    allowed |= {float(i["params"]["number"]) for i in data["insights"] if i["params"].get("number")}
    text = await ctx.text.summarise(facts)
    if text is None or not numbers_ok(text, allowed):
        raise ProblemError(502, "summary-rejected", "The summary could not be verified")
    summary = {
        "text": text,
        "model": ctx.text.model,
        "fingerprint": _fingerprint(data["insights"]),
        "created_at": datetime.now(UTC).isoformat(),
        "generated": True,
    }
    match.report_extra = {**(match.report_extra or {}), "summary": summary}
    return summary


async def _jersey_numbers(ctx: Ctx, season_id: uuid.UUID) -> dict[str, int]:
    rows = (
        await ctx.db.execute(
            select(RosterEntry.player_id, RosterEntry.jersey_number).where(
                RosterEntry.season_id == season_id
            )
        )
    ).all()
    return {str(pid): n for pid, n in rows if n is not None}


def _fact(item: dict[str, Any], numbers: dict[str, int]) -> dict[str, Any]:
    """Insight as a fact for the text model: no ids, no names, players as jersey numbers."""
    params = dict(item["params"])
    pid = params.pop("player_id", None)
    if pid:
        params["number"] = numbers.get(str(pid), params.get("number"))
    return {"art": item["kind"], "regel": item["key"].split(".")[-1], "werte": params}


async def season_stats(ctx: Ctx, team_id: uuid.UUID, season_id: uuid.UUID) -> dict[str, Any]:
    team = await get_team(ctx, team_id, Action.MATCH_READ)
    matches = await _matches_with_events(ctx, team.id, season_id)
    names = {
        o.id: o.name
        for o in (
            await ctx.db.scalars(
                select(Opponent).where(Opponent.id.in_([m.opponent_id for m in matches]))
            )
        ).all()
    }
    rows: list[dict[str, Any]] = []
    players: dict[str, dict[str, Any]] = {}
    totals = {"goals": 0, "shots": 0, "saves": 0, "goals_against": 0, "turnovers": 0, "xg": 0.0}
    for m in matches:
        s = await events_service.match_stats(ctx, m.id)
        own, opp = s["own"], s["opponent"]
        rows.append(
            {
                "match_id": str(m.id),
                "kickoff_at": m.kickoff_at.isoformat(),
                "opponent": names.get(m.opponent_id, ""),
                "is_home": m.is_home,
                "score_own": m.score_own if m.score_own is not None else own["goals"],
                "score_opponent": m.score_opponent
                if m.score_opponent is not None
                else opp["goals"],
                "goals": own["goals"],
                "shots": own["shots"],
                "shooting_pct": own["shooting_pct"],
                "save_pct": own["save_pct"],
                "turnovers": own["turnovers"],
                "xg": own["xg"],
                "xg_against": opp["xg"],
                "seven_m": [own["seven_m_goals"], own["seven_m_shots"]],
            }
        )
        for k in ("goals", "shots", "saves", "goals_against", "turnovers"):
            totals[k] += own[k]
        totals["xg"] = round(totals["xg"] + own["xg"], 2)
        for p in s["players"].values():
            if p["side"] != "own" or not p.get("player_id"):
                continue
            row = players.setdefault(
                p["player_id"],
                {
                    "player_id": p["player_id"],
                    "matches": 0,
                    "goals": 0,
                    "shots": 0,
                    "turnovers": 0,
                    "suspensions": 0,
                    "saves": 0,
                    "assists": 0,
                    "xg": 0.0,
                },
            )
            row["matches"] += 1
            for k in ("goals", "shots", "turnovers", "suspensions", "saves", "assists"):
                row[k] += p.get(k, 0)
            row["xg"] = round(row["xg"] + p.get("xg", 0.0), 2)
    for p in players.values():
        p["shooting_pct"] = round(p["goals"] / p["shots"], 4) if p["shots"] else None
    return {
        "season_id": str(season_id),
        "matches": rows,
        "totals": {
            **totals,
            "matches": len(rows),
            "shooting_pct": round(totals["goals"] / totals["shots"], 4)
            if totals["shots"]
            else None,
            "save_pct": round(totals["saves"] / (totals["saves"] + totals["goals_against"]), 4)
            if totals["saves"] + totals["goals_against"]
            else None,
        },
        "players": sorted(players.values(), key=lambda p: -p["goals"]),
    }
