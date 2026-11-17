"""Training tips from the analysis (K21): what to train next, from the team's last matches.

The match insights of the most recent matches with events are put together: a weakness that has a
training topic (`focus.follow_for`) becomes a tip with its numbers, the matches it came up in, the
scenes of the latest of them and drills from the library for its topic. Weaknesses that come back
in several matches come first. With no analysed match there is nothing to say, and the answer says
so honestly (`matches_analysed` is 0).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select

from handball_api.core.errors import ProblemError
from handball_api.models import Event, Match, Opponent
from handball_api.services import insights as insights_service
from handball_api.services.context import Ctx
from handball_api.services.drills import library
from handball_api.services.focus import follow_for
from handball_api.services.matches import counted
from handball_api.services.orgs import get_team
from handball_api.services.policies import Action

RECENT = 5  # matches with events looked at
MAX_TIPS = 3
DRILLS_PER_TIP = 3
SCENES_PER_TIP = 6
# individual findings (one player) are for a talk, not for a team training
SKIP = {"player_inefficient"}


def _rule(key: str) -> str:
    return key.removeprefix("insights.")


def drills_for(topics: list[str], n: int = DRILLS_PER_TIP) -> list[str]:
    """Library drills for the topics: drills made for a topic (first focus) before the others."""
    hits = [d for d in library() if any(f in topics for f in d["focus"])]
    first = [d for d in hits if d["focus"][0] in topics]
    rest = [d for d in hits if d["focus"][0] not in topics]
    # basic drills first within each group: a tip should be easy to start with
    ordered = sorted(first, key=lambda d: d["level"] != "basic") + sorted(
        rest, key=lambda d: d["level"] != "basic"
    )
    return [d["id"] for d in ordered[:n]]


def rank(per_match: list[tuple[str, list[dict[str, Any]]]]) -> list[dict[str, Any]]:
    """Weaknesses with a training topic, grouped over the matches (newest first in `per_match`).

    A weakness found in more matches ranks higher, then one from the latest match, then the
    stronger one (insight score). Each tip carries the insight of its most recent match.
    """
    groups: dict[str, dict[str, Any]] = {}
    for pos, (match_id, items) in enumerate(per_match):
        for item in items:
            if item.get("kind") != "weakness" or _rule(item.get("key", "")) in SKIP:
                continue
            follow = follow_for(item["key"], item.get("params") or {})
            if follow is None:
                continue
            gid = str(item.get("id") or item["key"])
            if gid not in groups:
                groups[gid] = {
                    "id": gid,
                    "key": item["key"],
                    "params": item.get("params") or {},
                    "evidence": item.get("evidence") or {},
                    "sample": item.get("sample"),
                    "match_id": match_id,
                    "topics": follow[3],
                    "metric": follow[0],
                    "matches": 0,
                    "latest": pos == 0,
                    "scores": [],
                }
            groups[gid]["matches"] += 1
            groups[gid]["scores"].append(float(item.get("score") or 0))
    tips = list(groups.values())
    tips.sort(key=lambda t: (-t["matches"], not t["latest"], -max(t["scores"])))
    for t in tips:
        t["score"] = round(sum(t["scores"]) / len(t["scores"]), 3)
        del t["scores"]
        t["drills"] = drills_for(t["topics"])
    return tips[:MAX_TIPS]


async def _recent_matches(ctx: Ctx, team_id: uuid.UUID) -> list[Match]:
    has_events = select(Event.match_id).distinct()
    return list(
        (
            await ctx.db.scalars(
                select(Match)
                .where(
                    Match.team_id == team_id,
                    Match.kind == "match",
                    counted(),  # the example match is not the team's (R1)
                    Match.id.in_(has_events),
                )
                .order_by(Match.kickoff_at.desc())
                .limit(RECENT)
            )
        ).all()
    )


async def tips(ctx: Ctx, team_id: uuid.UUID) -> dict[str, Any]:
    team = await get_team(ctx, team_id, Action.MATCH_READ)
    matches = await _recent_matches(ctx, team.id)
    out: dict[str, Any] = {
        "matches_analysed": len(matches),
        "plan_required": False,
        "matches": [],
        "tips": [],
    }
    if not matches:
        return out
    per_match: list[tuple[str, list[dict[str, Any]]]] = []
    try:
        for m in matches:
            per_match.append((str(m.id), (await insights_service.insights(ctx, m.id))["insights"]))
    except ProblemError as exc:
        if exc.status != 402:
            raise
        out["plan_required"] = True
        return out
    names = {
        o.id: o.name
        for o in (
            await ctx.db.scalars(
                select(Opponent).where(
                    Opponent.id.in_({m.opponent_id for m in matches if m.opponent_id})
                )
            )
        ).all()
    }
    out["matches"] = [
        {
            "match_id": m.id,
            "kickoff_at": m.kickoff_at,
            "opponent": names.get(m.opponent_id) if m.opponent_id else None,
        }
        for m in matches
    ]
    ranked = rank(per_match)
    for t in ranked:
        scenes = await insights_service._scenes(
            ctx, uuid.UUID(t["match_id"]), t["evidence"], limit=SCENES_PER_TIP
        )
        t["scenes"] = [s for s in scenes if s["t_ms"] is not None]
        t["of"] = len(matches)
        del t["latest"]
    out["tips"] = ranked
    return out
