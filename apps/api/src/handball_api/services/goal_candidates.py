"""Goal candidates from the video analysis (handball_vision.goalcandidates): moments that are
probably goals, which the coach confirms or rejects with one click.

- `store` (analysis result of the match's main video): the open candidates of the video are
  replaced; reviewed ones stay (a rejected candidate is a hard negative for training, a confirmed
  one is a goal), and a new candidate this close to a reviewed one is the same moment and is not
  added again. Each candidate gets a suggested side: the side whose attack (automatic possession)
  ended just before it.
- `listing`: the candidates with the goal they are already covered by, following the dedupe rules
  of the automatic events (auto_events): an overlay or official goal within OVERLAY_DEDUPE_MS
  (the overlay changes a few seconds after the goal; official times come from the clock), any
  other goal (tagged, corrected, a confirmed candidate) within NMS_MS (the candidates' own
  spacing). Computed when read, so a report imported later still merges them.
- `review`: confirm (a goal event of the chosen side, source "goal_candidate", at the estimated
  goal time; an automatic throw-off goal of that side close to it is superseded), reject, or undo.
  Every review goes to the audit log.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select

from handball_api.core.errors import ProblemError
from handball_api.models import Event, GoalCandidate, Match, Possession, VideoAsset
from handball_api.schemas.events import EventIn
from handball_api.services import audit
from handball_api.services import events as event_service
from handball_api.services.auto_events import (
    CANDIDATE,
    OFFICIAL,
    OVERLAY,
    OVERLAY_DEDUPE_MS,
    SOURCE,
)
from handball_api.services.context import Ctx
from handball_api.services.events import clock_from_video
from handball_api.services.matches import get_match
from handball_api.services.policies import Action

GOAL_SOURCE = CANDIDATE  # goal events confirmed from a candidate
NMS_MS = 8000  # candidates are at least this far apart
SIDE_BEFORE_MS = 12_000  # an attack that ended this long before the goal scored it
RATES = (1, 2, 4)
DEFAULT_RATE = 2
REVIEWED = ("confirmed", "rejected")
SIDES = ("own", "opponent")


def _int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


async def store(
    ctx: Ctx, match: Match, asset: VideoAsset, found: dict[str, Any] | None, pipeline: str | None
) -> dict[str, int]:
    """Candidates of a new analysis of the match's main video (`found` is the worker's
    `goal_candidates`; None when the video was too short or nobody was seen)."""
    await ctx.db.execute(
        delete(GoalCandidate).where(
            GoalCandidate.video_asset_id == asset.id, GoalCandidate.status == "open"
        )
    )
    reviewed = [
        c.t_ms
        for c in (
            await ctx.db.scalars(
                select(GoalCandidate).where(GoalCandidate.video_asset_id == asset.id)
            )
        ).all()
    ]
    rows = [r for r in (found or {}).get("candidates") or [] if isinstance(r, dict)]
    if not rows:
        return {"goal_candidates": 0}
    attacks = (
        await ctx.db.scalars(
            select(Possession).where(Possession.match_id == match.id, Possession.source == SOURCE)
        )
    ).all()
    template = str((found or {}).get("template") or "")[:20] or None
    created = 0
    for r in rows:
        t_ms = _int(r.get("t_ms"), -1)
        if t_ms < 0 or any(abs(t_ms - t) <= NMS_MS for t in reviewed):
            continue
        goal_ms = _int(r.get("goal_ms"), t_ms)
        rate = _int(r.get("rate"), max(RATES))
        ctx.db.add(
            GoalCandidate(
                organization_id=match.organization_id,
                match_id=match.id,
                video_asset_id=asset.id,
                t_ms=t_ms,
                goal_ms=goal_ms,
                start_ms=_int(r.get("start_ms"), max(0, t_ms - 10_000)),
                end_ms=_int(r.get("end_ms"), t_ms + 4000),
                score=float(r.get("score") or 0.0),
                rate=rate if rate in RATES else max(RATES),
                rank=_int(r.get("rank")),
                suggested_side=suggest_side(attacks, goal_ms),
                status="open",
                template_version=template,
                pipeline_version=pipeline,
            )
        )
        created += 1
    await ctx.db.flush()
    return {"goal_candidates": created}


def suggest_side(attacks: Any, goal_ms: int) -> str | None:
    """The side whose attack ended last before the goal (as overlay goals are aligned)."""
    near = [p for p in attacks if goal_ms - SIDE_BEFORE_MS <= p.end_ms <= goal_ms + 3000]
    return max(near, key=lambda p: p.end_ms).side if near else None


def _covered(c: GoalCandidate, goals: list[Event]) -> Event | None:
    """The goal a candidate is already covered by, nearest first."""
    best: Event | None = None
    for g in goals:
        if g.t_ms is None or (c.event_id is not None and g.id == c.event_id):
            continue
        window = OVERLAY_DEDUPE_MS if g.source in (OVERLAY, OFFICIAL) else NMS_MS
        d = abs(int(g.t_ms) - c.t_ms)
        if d <= window and (best is None or d < abs(int(best.t_ms or 0) - c.t_ms)):
            best = g
    return best


async def _goals(ctx: Ctx, match_id: uuid.UUID) -> list[Event]:
    return list(
        (
            await ctx.db.scalars(
                select(Event).where(
                    Event.match_id == match_id,
                    Event.type == "shot",
                    Event.outcome == "goal",
                    Event.t_ms.is_not(None),
                    Event.source != SOURCE,  # estimated from throw-offs: what candidates check
                )
            )
        ).all()
    )


def _row(c: GoalCandidate, match: Match, known: Event | None) -> dict[str, Any]:
    derived = clock_from_video(match, c.goal_ms)
    return {
        "id": c.id,
        "video_asset_id": c.video_asset_id,
        "t_ms": c.t_ms,
        "goal_ms": c.goal_ms,
        "start_ms": c.start_ms,
        "end_ms": c.end_ms,
        "score": round(c.score, 3),
        "rate": c.rate,
        "suggested_side": c.suggested_side,
        "status": c.status,
        "side": c.side,
        "event_id": c.event_id,
        "period": derived[0] if derived else None,
        "clock_s": derived[1] if derived else None,
        "known": None
        if known is None or c.status != "open"
        else {"event_id": known.id, "source": known.source, "side": known.side, "t_ms": known.t_ms},
    }


async def listing(ctx: Ctx, match_id: uuid.UUID) -> dict[str, Any]:
    match = await get_match(ctx, match_id)
    cands = (
        await ctx.db.scalars(
            select(GoalCandidate)
            .where(GoalCandidate.match_id == match.id)
            .order_by(GoalCandidate.t_ms)
        )
    ).all()
    goals = await _goals(ctx, match.id)
    rows = [_row(c, match, _covered(c, goals)) for c in cands]
    open_rows = [r for r in rows if r["status"] == "open" and r["known"] is None]
    versions = sorted({c.template_version for c in cands if c.template_version})
    return {
        "template": versions[-1] if versions else None,
        "rates": list(RATES),
        "default_rate": DEFAULT_RATE,
        "counts": {
            "total": len(rows),
            "open": len(open_rows),
            "open_by_rate": {str(r): sum(1 for x in open_rows if x["rate"] <= r) for r in RATES},
            "confirmed": sum(1 for r in rows if r["status"] == "confirmed"),
            "rejected": sum(1 for r in rows if r["status"] == "rejected"),
            "known": sum(1 for r in rows if r["known"] is not None),
        },
        "candidates": rows,
    }


async def _drop_goal(ctx: Ctx, c: GoalCandidate) -> uuid.UUID | None:
    """The goal event a confirmation created, removed (it is still this candidate's)."""
    if c.event_id is None:
        return None
    ev = await ctx.db.get(Event, c.event_id)
    gone = None
    if ev is not None and (ev.attributes or {}).get("goal_candidate") == str(c.id):
        await event_service.delete_event(ctx, ev.id)
        gone = ev.id
    c.event_id = None
    return gone


async def review(
    ctx: Ctx, match_id: uuid.UUID, candidate_id: uuid.UUID, status: str | None, side: str | None
) -> dict[str, Any]:
    """Confirm (`side` required: whose goal), reject or reopen (`status` None) a candidate."""
    match = await get_match(ctx, match_id, Action.EVENT_WRITE)
    c = await ctx.db.get(GoalCandidate, candidate_id)
    if c is None or c.match_id != match.id:
        raise ProblemError(404, "not-found", "Goal candidate not found")
    if status == "confirmed" and side not in SIDES:
        raise ProblemError(422, "invalid-side", "A confirmed goal needs the side that scored")
    if status == "confirmed" and c.status == "open":
        known = _covered(c, await _goals(ctx, match.id))
        if known is not None:
            raise ProblemError(409, "already-a-goal", "This moment is already a goal")
    before = (c.status, c.side)
    superseded: list[str] = []
    removed = None
    if status == "confirmed":
        ev = await ctx.db.get(Event, c.event_id) if c.event_id else None
        if ev is not None and (ev.attributes or {}).get("goal_candidate") == str(c.id):
            if ev.side != side:
                ev.side = str(side)
        else:
            ev = await event_service.create_event(
                ctx,
                match.id,
                EventIn(
                    type="shot",
                    side=side,
                    outcome="goal",
                    t_ms=c.goal_ms,
                    attributes={
                        "goal_candidate": str(c.id),
                        "clip": [c.start_ms, c.end_ms],
                    },
                ),
                source=GOAL_SOURCE,
            )
            c.event_id = ev.id
        # an automatic goal estimated from the throw-off is the same goal, now confirmed
        for g in await ctx.db.scalars(
            select(Event).where(
                Event.match_id == match.id,
                Event.source == SOURCE,
                Event.type == "shot",
                Event.outcome == "goal",
                Event.side == side,
                Event.t_ms.between(c.goal_ms - OVERLAY_DEDUPE_MS, c.goal_ms + OVERLAY_DEDUPE_MS),
            )
        ):
            superseded.append(str(g.id))
            await ctx.db.delete(g)
        c.status, c.side = "confirmed", side
    else:
        removed = await _drop_goal(ctx, c)
        c.status, c.side = ("rejected" if status == "rejected" else "open"), None
    c.reviewed_by_id = ctx.user_id if status is not None else None
    c.reviewed_at = datetime.now(UTC) if status is not None else None
    await ctx.db.flush()
    await audit.record(
        ctx,
        "match.goal_candidate_reviewed",
        target_type="match",
        target_id=match.id,
        data={
            "candidate_id": str(c.id),
            "video_asset_id": str(c.video_asset_id),
            "t_ms": c.t_ms,
            "template": c.template_version,
            "review": status,
            "side": c.side,
            "before": {"status": before[0], "side": before[1]},
            "event_id": str(c.event_id) if c.event_id else None,
            "removed_event_id": str(removed) if removed else None,
            "superseded": superseded,
        },
    )
    goals = await _goals(ctx, match.id)
    return _row(c, match, _covered(c, goals))
