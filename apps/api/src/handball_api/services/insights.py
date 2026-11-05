"""Match insights, season statistics and summaries (M7)."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select

from handball_api.core.errors import ProblemError
from handball_api.core.text import numbers_ok
from handball_api.models import (
    Event,
    Match,
    Opponent,
    Organization,
    Player,
    RosterEntry,
    Team,
)
from handball_api.services import billing, report_pdf
from handball_api.services import events as events_service
from handball_api.services.context import Ctx
from handball_api.services.matches import get_match, opponent_of, timeline_video
from handball_api.services.orgs import get_team
from handball_api.services.policies import Action, visible_team_ids
from handball_metrics.insights import VERSION, match_insights
from handball_metrics.stats import METRICS_VERSION


async def _matches_with_events(ctx: Ctx, team_id: uuid.UUID, season_id: uuid.UUID) -> list[Match]:
    has_events = select(Event.match_id).distinct()
    return list(
        (
            await ctx.db.scalars(
                select(Match)
                .where(
                    Match.team_id == team_id,
                    Match.season_id == season_id,
                    Match.kind == "match",  # trainings stay out of match statistics (4.8)
                    Match.id.in_(has_events),
                )
                .order_by(Match.kickoff_at)
            )
        ).all()
    )


async def _played_matches(ctx: Ctx, team_id: uuid.UUID, season_id: uuid.UUID) -> list[Match]:
    """Matches of the season that were played: a result is stored or events are (tagged or not)."""
    has_events = select(Event.match_id).distinct()
    return list(
        (
            await ctx.db.scalars(
                select(Match)
                .where(
                    Match.team_id == team_id,
                    Match.season_id == season_id,
                    Match.kind == "match",
                    Match.score_own.is_not(None) | Match.id.in_(has_events),
                )
                .order_by(Match.kickoff_at)
            )
        ).all()
    )


async def _season_version(ctx: Ctx, team_id: uuid.UUID, season_id: uuid.UUID) -> str:
    """One aggregated query that changes whenever a match or an event of the season changes."""
    rows = (
        await ctx.db.execute(
            select(Match.id, Match.updated_at, func.count(Event.id), func.max(Event.updated_at))
            .outerjoin(Event, Event.match_id == Match.id)
            .where(Match.team_id == team_id, Match.season_id == season_id)
            .group_by(Match.id, Match.updated_at)
            .order_by(Match.id)
        )
    ).all()
    raw = "|".join(f"{a}:{b}:{c}:{d}" for a, b, c, d in rows)
    return hashlib.sha256(f"{raw}|{METRICS_VERSION}|{VERSION}".encode()).hexdigest()[:32]


async def insights(ctx: Ctx, match_id: uuid.UUID) -> dict[str, Any]:
    match = await get_match(ctx, match_id)
    await billing.require_feature(ctx, "insights", match.organization_id)
    version = await _season_version(ctx, match.team_id, match.season_id)
    cached = await events_service.cache_get(ctx, "insights", match.id, version)
    if cached is None:
        stats = await events_service.stats_for(ctx, match)
        others = [
            m
            for m in await _matches_with_events(ctx, match.team_id, match.season_id)
            if m.id != match.id
        ]
        baseline = [await events_service.stats_for(ctx, m) for m in others]
        cached = {
            "items": match_insights(stats, baseline) if stats["quality"]["events"] else [],
            "baseline": len(baseline),
        }
        await events_service.cache_put(
            ctx, match.organization_id, "insights", match.id, version, cached
        )
    items, baseline_n = cached["items"], cached["baseline"]
    summary = (match.report_extra or {}).get("summary")
    fingerprint = _fingerprint(items)
    return {
        "version": VERSION,
        "baseline_matches": baseline_n,
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
    opponent = await opponent_of(ctx, match)
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
    await billing.require_feature(ctx, "season", team.organization_id)
    version = await _season_version(ctx, team.id, season_id) + (":y" if team.is_youth else "")
    cached = await events_service.cache_get(ctx, "season", season_id, version)
    if cached is not None:
        return cached
    data = await _season_stats(ctx, team, season_id)
    await events_service.cache_put(ctx, team.organization_id, "season", season_id, version, data)
    return data


async def _season_stats(ctx: Ctx, team: Team, season_id: uuid.UUID) -> dict[str, Any]:
    """Every played match counts; goals per match from its events (one source per goal, see
    handball_metrics.stats.one_source_per_goal), from the stored result when nothing is tagged.
    Shots, saves and turnovers come from the tagged matches; the shooting and save percentages
    only from matches with recorded misses or saves; xG only covers shots with a position:
    `xg_coverage` = shots with xG / shots on target."""
    matches = await _played_matches(ctx, team.id, season_id)
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
    totals: dict[str, Any] = {
        "goals": 0,
        "goals_against": 0,
        "tagged_matches": 0,
        "shots": 0,
        "saves": 0,
        "turnovers": 0,
        "xg": 0.0,
        "xg_shots": 0,
    }
    pct = {"goals": 0, "shots": 0, "saves": 0, "goals_against": 0}  # matches with attempts
    for m in matches:
        s = await events_service.stats_for(ctx, m)
        own, opp = s["own"], s["opponent"]
        tagged = bool(s["quality"]["events"])
        goals = own["goals"] if tagged else m.score_own or 0
        against = opp["goals"] if tagged else m.score_opponent or 0
        rows.append(
            {
                "match_id": str(m.id),
                "kickoff_at": m.kickoff_at.isoformat(),
                "opponent": names.get(m.opponent_id, "") if m.opponent_id else "",
                "is_home": m.is_home,
                "score_own": m.score_own if m.score_own is not None else own["goals"],
                "score_opponent": m.score_opponent
                if m.score_opponent is not None
                else opp["goals"],
                "tagged": tagged,
                "goals": goals,
                "goals_against": against,
                "shots": own["shots"],
                "shooting_pct": own["shooting_pct"],
                "save_pct": own["save_pct"],
                "turnovers": own["turnovers"],
                "xg": own["xg"],
                "xg_coverage": own["xg_coverage"],
                "xg_against": opp["xg"],
                "seven_m": [own["seven_m_goals"], own["seven_m_shots"]],
            }
        )
        totals["goals"] += goals
        totals["goals_against"] += against
        totals["tagged_matches"] += tagged
        for k in ("shots", "saves", "turnovers", "xg_shots"):
            totals[k] += own[k]
        totals["xg"] = round(totals["xg"] + own["xg"], 2)
        if s["quality"]["attempts_known"]:
            for k in pct:
                pct[k] += own[k]
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
    if team.is_youth:
        # youth protection (addendum 01): no ranking of children, list by jersey number
        numbers = await _jersey_numbers(ctx, season_id)
        player_list = sorted(
            players.values(), key=lambda p: (numbers.get(p["player_id"], 100), p["player_id"])
        )
    else:
        player_list = sorted(players.values(), key=lambda p: -p["goals"])
    return {
        "ranked": not team.is_youth,
        "season_id": str(season_id),
        "matches": rows,
        "totals": {
            **totals,
            "matches": len(rows),
            "shooting_pct": round(pct["goals"] / pct["shots"], 4) if pct["shots"] else None,
            "save_pct": round(pct["saves"] / (pct["saves"] + pct["goals_against"]), 4)
            if pct["saves"] + pct["goals_against"]
            else None,
            "xg_coverage": round(totals["xg_shots"] / totals["shots"], 4)
            if totals["shots"]
            else None,
        },
        "players": player_list,
    }


async def opponent_profile(ctx: Ctx, opponent_id: uuid.UUID) -> dict[str, Any]:
    """Scouting: what the opponent did in all our tagged matches against them (visible teams)."""
    opponent = await ctx.db.get(Opponent, opponent_id)
    if opponent is None or opponent.organization_id != ctx.require_actor().organization_id:
        raise ProblemError(404, "not-found", "Opponent not found")
    await billing.require_feature(ctx, "season", opponent.organization_id)
    visible = visible_team_ids(ctx.require_actor())
    q = select(Match).where(Match.opponent_id == opponent.id).order_by(Match.kickoff_at)
    if visible is not None:
        q = q.where(Match.team_id.in_(visible))
    matches = list((await ctx.db.scalars(q)).all())
    record = {"won": 0, "drawn": 0, "lost": 0}
    agg: dict[str, Any] = {
        "goals": 0,
        "shots": 0,
        "seven_m_goals": 0,
        "seven_m_shots": 0,
        "fast_break_goals": 0,
        "turnovers": 0,
        "xg": 0.0,
        "xg_shots": 0,
    }
    zones: dict[str, dict[str, int]] = {}
    goal_zones: dict[str, dict[str, int]] = {}
    scorers: dict[int, dict[str, int]] = {}
    formations: dict[str, int] = {}
    rows = []
    tagged = 0
    for m in matches:
        if m.score_own is not None and m.score_opponent is not None:
            key = (
                "won"
                if m.score_own > m.score_opponent
                else "drawn"
                if m.score_own == m.score_opponent
                else "lost"
            )
            record[key] += 1
        s = await events_service.match_stats(ctx, m.id)
        rows.append(
            {
                "match_id": str(m.id),
                "kickoff_at": m.kickoff_at.isoformat(),
                "is_home": m.is_home,
                "score_own": m.score_own,
                "score_opponent": m.score_opponent,
                "events": s["quality"]["events"],
            }
        )
        if not s["quality"]["events"]:
            continue
        tagged += 1
        opp = s["opponent"]
        for k in (
            "goals",
            "shots",
            "seven_m_goals",
            "seven_m_shots",
            "fast_break_goals",
            "turnovers",
            "xg_shots",
        ):
            agg[k] += opp[k]
        agg["xg"] = round(agg["xg"] + opp["xg"], 2)
        for src, dst in ((opp["zones"], zones), (opp["goal_zones"], goal_zones)):
            for z, v in src.items():
                d = dst.setdefault(z, {"shots": 0, "goals": 0})
                d["shots"] += v["shots"]
                d["goals"] += v["goals"]
        for p in s["players"].values():
            if p["side"] == "opponent" and p.get("number") is not None:
                d = scorers.setdefault(int(p["number"]), {"goals": 0, "shots": 0, "matches": 0})
                d["goals"] += p["goals"]
                d["shots"] += p["shots"]
                d["matches"] += 1
        main = await timeline_video(ctx, m.id)
        for seg in ((main.analysis or {}).get("formations") or []) if main else []:
            if seg.get("team") == "away":
                f = str(seg["formation"])
                formations[f] = formations.get(f, 0) + int(seg["end_ms"]) - int(seg["start_ms"])
    agg["shooting_pct"] = round(agg["goals"] / agg["shots"], 4) if agg["shots"] else None
    agg["xg_coverage"] = round(agg["xg_shots"] / agg["shots"], 4) if agg["shots"] else None
    top = sorted(scorers.items(), key=lambda kv: (-kv[1]["goals"], kv[0]))[:8]
    return {
        "opponent": {"id": str(opponent.id), "name": opponent.name},
        "record": record,
        "matches": rows,
        "tagged_matches": tagged,
        "totals": agg,
        "zones": zones,
        "goal_zones": goal_zones,
        "scorers": [{"number": n, **v} for n, v in top],
        "formations_ms": formations,
    }


async def match_pdf(ctx: Ctx, match_id: uuid.UUID, lang: str) -> tuple[bytes, str]:
    """Printable match report (PDF) in the requested language."""
    match = await get_match(ctx, match_id)
    await billing.require_feature(ctx, "pdf_reports", match.organization_id)
    org = await ctx.db.get(Organization, match.organization_id)
    team = await ctx.db.get(Team, match.team_id)
    opponent = await opponent_of(ctx, match)
    assert org is not None and team is not None
    stats = await events_service.stats_for(ctx, match)
    items: list[dict[str, Any]] = []
    if stats["quality"]["events"] and billing.has_feature(ctx.settings, org, "insights"):
        items = (await insights(ctx, match.id))["insights"]
    rows = (
        await ctx.db.execute(
            select(
                RosterEntry.player_id,
                Player.first_name,
                Player.last_name,
            )
            .join(Player, Player.id == RosterEntry.player_id)
            .where(RosterEntry.season_id == match.season_id)
        )
    ).all()
    names = {str(pid): f"{first} {last}" for pid, first, last in rows}
    own, opp = team.name, opponent.name if opponent else ""
    home, away = (own, opp) if match.is_home else (opp, own)
    score = ht = None
    if match.score_own is not None and match.score_opponent is not None:
        a, b = (match.score_own, match.score_opponent)
        score = f"{a}:{b}" if match.is_home else f"{b}:{a}"
    if match.halftime_own is not None and match.halftime_opponent is not None:
        a, b = (match.halftime_own, match.halftime_opponent)
        ht = f"{a}:{b}" if match.is_home else f"{b}:{a}"
    subtitle = " · ".join(
        x
        for x in (match.kickoff_at.strftime("%d.%m.%Y %H:%M"), match.competition, match.venue)
        if x
    )
    pdf = report_pdf.render(
        lang,
        {"name": org.name, "primary_color": org.primary_color},
        {
            "home": home,
            "away": away,
            "own_name": own,
            "opp_name": opp,
            "period_s": match.period_s,
            "periods": match.periods,
            "score": score,
            "halftime": ht,
            "subtitle": subtitle,
        },
        stats,
        items,
        names,
    )
    filename = f"matchreport-{match.kickoff_at:%Y-%m-%d}-{opp}".lower().replace(" ", "-")
    return pdf, "".join(c for c in filename if c.isalnum() or c in "-_") + ".pdf"
