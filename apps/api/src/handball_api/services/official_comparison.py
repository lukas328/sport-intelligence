"""Official goals of an imported report compared with what the video found.

`comparison` lists the official goals next to what the video found (the import's video data, or an
automatic goal within the same 20 s) and the video goals without an official one; goals before
or after the main video (a clip of part of the game) are "outside", not missing. The coach
confirms or dismisses each row (`review`, kept in attributes.review, kept by a re-import).

The matching primitives (`Seen`, `nearest`, MATCH_WINDOW_S) are shared with the import
(services/official_report.py), which pairs official goals with video goals the same way.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select

from handball_api.core.clock import format_clock
from handball_api.core.errors import ProblemError
from handball_api.models import Event
from handball_api.services import audit, roster
from handball_api.services.auto_events import CANDIDATE, OFFICIAL, OVERLAY
from handball_api.services.context import Ctx
from handball_api.services.events import shown_attributes
from handball_api.services.matches import duration_ms, get_match, timeline_video
from handball_api.services.policies import Action

SOURCE = OFFICIAL
# goals seen on video: an official goal takes over their video time (a confirmed goal candidate
# has no scorer; the report has)
AUTO_GOALS = ("heuristic", "model", OVERLAY, CANDIDATE)
REVIEW = ("confirmed", "dismissed")
MATCH_WINDOW_S = 20.0  # the overlay changes a few seconds after the goal; minutes are rounded


@dataclass
class Seen:
    """A goal already known from video: an automatic event, or the video data an earlier import
    took over from one."""

    side: str
    clock_s: float
    t_ms: int | None
    x: float | None
    y: float | None
    source: str
    confidence: float
    event: Event | None = None
    outcome: str = "goal"
    candidate_id: str | None = None  # the video candidate it was confirmed on


def nearest(cands: list[Any], side: str, clock: float, outcome: str = "goal") -> Any | None:
    best = [
        c
        for c in cands
        if c.side == side
        and getattr(c, "outcome", "goal") == outcome
        and abs(c.clock_s - clock) <= MATCH_WINDOW_S
    ]
    return min(best, key=lambda c: abs(c.clock_s - clock)) if best else None


def _review(e: Event) -> str | None:
    r = (e.attributes or {}).get("review")
    return r if r in REVIEW else None


def _video_goal(e: Event) -> dict[str, Any]:
    attrs = e.attributes or {}
    return {
        "event_id": e.id,
        "side": e.side,
        "period": e.period,
        "clock_s": e.clock_s,
        "official_time": format_clock(e.clock_s),
        "t_ms": e.t_ms,
        "source": e.source,
        "confidence": round(e.confidence, 3),
        "number": e.number,
        "player_id": e.player_id,
        "name": attrs.get("scorer_name"),
        "score": attrs.get("score"),
        "review": _review(e),
    }


async def comparison(ctx: Ctx, match_id: uuid.UUID) -> dict[str, Any]:
    """Each official goal with what the video found: the video data the import took over (or the
    analysis noted), else an automatic goal of the same side within MATCH_WINDOW_S of match
    clock, as the import pairs them; then the automatic goals without an official counterpart.
    An official goal the video did not find whose time (from the match clock) lies before or after
    the main video is "outside": a clip of a few minutes is not missing the rest of the game."""
    match = await get_match(ctx, match_id)
    length_ms = duration_ms(await timeline_video(ctx, match.id, ready=True))
    goals = (
        await ctx.db.scalars(
            select(Event)
            .where(Event.match_id == match.id, Event.type == "shot", Event.outcome == "goal")
            .order_by(Event.period, Event.clock_s.nulls_last(), Event.t_ms.nulls_last())
        )
    ).all()
    official = [g for g in goals if g.source == SOURCE]
    auto = [g for g in goals if g.source in AUTO_GOALS]
    visible = await roster.visible_players(ctx, match.team_id, match.season_id)
    cands = [
        Seen(g.side, float(g.clock_s), g.t_ms, g.x, g.y, g.source, g.confidence, g)
        for g in auto
        if g.clock_s is not None
    ]
    used: set[int] = set()
    rows: list[dict[str, Any]] = []
    for o in official:
        stored = (o.attributes or {}).get("video")
        video: dict[str, Any] | None = None
        if isinstance(stored, dict):
            video = {
                "source": str(stored.get("source", OVERLAY)),
                "t_ms": stored.get("t_ms"),
                "clock_s": stored.get("clock_s"),
                "confidence": stored.get("confidence"),
                "event_id": None,
            }
        elif o.clock_s is not None:
            hit = nearest([c for c in cands if id(c) not in used], o.side, float(o.clock_s))
            if hit is not None and hit.event is not None:
                used.add(id(hit))
                video = {
                    "source": hit.source,
                    "t_ms": hit.t_ms,
                    "clock_s": hit.clock_s,
                    "confidence": round(hit.confidence, 3),
                    "event_id": hit.event.id,
                }
        video_t = video.get("t_ms") if video else None
        t_ms = int(video_t) if video_t is not None else o.t_ms
        status = "found" if video else "missing"
        if (
            status == "missing"
            and t_ms is not None
            and length_ms is not None
            and not 0 <= t_ms <= length_ms
        ):
            status = "outside"
        attrs = shown_attributes(o, visible)
        rows.append(
            {
                "event_id": o.id,
                "side": o.side,
                "period": o.period,
                "clock_s": o.clock_s,
                "official_time": attrs.get("official_time") or format_clock(o.clock_s),
                # where the video shows it: the video reading, else the time from the clock
                "t_ms": t_ms,
                "estimated": video_t is None,
                "number": o.number,
                "player_id": o.player_id,
                "name": attrs.get("name"),
                "score": attrs.get("score"),
                "penalty": o.shot_type == "penalty",
                "status": status,
                "video": video,
                "review": _review(o),
            }
        )
    paired = {id(c.event) for c in cands if id(c) in used}
    extra = [_video_goal(g) for g in auto if id(g) not in paired]
    found = sum(1 for r in rows if r["status"] == "found")
    outside = sum(1 for r in rows if r["status"] == "outside")
    report = (match.report_extra or {}).get("official_report") or {}
    return {
        "imported": bool(report) or bool(official),
        "provider": report.get("provider"),
        "source_url": report.get("url"),
        "home": report.get("home"),
        "away": report.get("away"),
        "window_s": MATCH_WINDOW_S,
        "counts": {
            "official": len(rows),
            "found": found,
            "missing": len(rows) - found - outside,
            "outside": outside,
            "extra": len(extra),
            "open": sum(1 for r in rows if r["status"] == "missing" and r["review"] is None)
            + sum(1 for r in extra if r["review"] is None),
        },
        "goals": rows,
        "extra": extra,
    }


async def review(ctx: Ctx, match_id: uuid.UUID, event_id: uuid.UUID, status: str | None) -> None:
    """The coach checked a row of the comparison: an official goal (its video time is right, or
    not) or a video goal without an official one (a real goal, or a misreading)."""
    match = await get_match(ctx, match_id, Action.EVENT_WRITE)
    ev = await ctx.db.get(Event, event_id)
    if (
        ev is None
        or ev.match_id != match.id
        or ev.type != "shot"
        or ev.outcome != "goal"
        or ev.source not in (SOURCE, *AUTO_GOALS)
    ):
        raise ProblemError(404, "not-found", "Goal not found in the comparison")
    attrs = {k: v for k, v in (ev.attributes or {}).items() if k != "review"}
    if status is not None:
        attrs["review"] = status
    ev.attributes = attrs
    await audit.record(
        ctx,
        "match.official_goal_reviewed",
        target_type="match",
        target_id=match.id,
        data={"event_id": str(ev.id), "source": ev.source, "review": status},
    )
