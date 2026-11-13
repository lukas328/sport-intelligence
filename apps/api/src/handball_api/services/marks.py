"""Courtside marks with device time (addendum 01, 5.3).

A phone (web or app) stores 4 to 8 freely labelled buttons per team. Marks are saved offline with
the phone's clock and uploaded later (idempotent per client id). After the video is analysed they
are synced automatically: the camera's recording start is the prior, goal taps against goals in the
video refine it (`handball_metrics.sync`). Marks then appear as the "Coach" track and as a list;
without live marks nothing is missing (P1).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from handball_api.core.errors import ProblemError
from handball_api.models import Event, LiveTag, LiveTagSession, Match, Team, VideoAsset
from handball_api.schemas.marks import MarkIn, MarkKey
from handball_api.services import audit
from handball_api.services.context import Ctx
from handball_api.services.matches import get_match, timeline_video
from handball_api.services.orgs import get_team
from handball_api.services.policies import Action
from handball_metrics.sync import estimate_offset

GOAL_KEYS = ("goal_own", "goal_opp")
HALFTIME = "halftime"
# the default set: the two goal keys make the automatic sync possible
DEFAULT_KEYS: list[dict[str, Any]] = [
    {"key": "goal_own", "label": None, "color": "#15803d"},
    {"key": "goal_opp", "label": None, "color": "#b91c1c"},
    {"key": "good", "label": None, "color": "#0b6bcb"},
    {"key": "mistake", "label": None, "color": "#ca8a04"},
    {"key": "defence", "label": None, "color": "#7c3aed"},
    {"key": "review", "label": None, "color": "#475569"},
]


async def keys(ctx: Ctx, team_id: uuid.UUID) -> list[dict[str, Any]]:
    team = await get_team(ctx, team_id, Action.TEAM_READ)
    return list(team.settings.get("live_keys") or DEFAULT_KEYS)


async def set_keys(ctx: Ctx, team_id: uuid.UUID, items: list[MarkKey]) -> list[dict[str, Any]]:
    team = await get_team(ctx, team_id, Action.CLIP_WRITE)
    seen = [k.key for k in items]
    if len(set(seen)) != len(seen) or HALFTIME in seen:
        raise ProblemError(422, "validation", "Keys must be unique and not 'halftime'")
    team.settings = {**team.settings, "live_keys": [k.model_dump() for k in items]}
    return list(team.settings["live_keys"])


async def start(ctx: Ctx, match_id: uuid.UUID, device: str | None) -> LiveTagSession:
    match = await get_match(ctx, match_id, Action.CLIP_WRITE)
    s = LiveTagSession(
        organization_id=match.organization_id,
        match_id=match.id,
        user_id=ctx.user_id,
        device=(device or "")[:120] or None,
        started_at=datetime.now(UTC),
    )
    ctx.db.add(s)
    await ctx.db.flush()
    return s


async def _session(ctx: Ctx, session_id: uuid.UUID) -> tuple[LiveTagSession, Match]:
    s = await ctx.db.get(LiveTagSession, session_id)
    if s is None:
        raise ProblemError(404, "not-found", "Mark session not found")
    match = await get_match(ctx, s.match_id, Action.CLIP_WRITE)
    return s, match


async def add(ctx: Ctx, session_id: uuid.UUID, items: list[MarkIn]) -> dict[str, Any]:
    s, match = await _session(ctx, session_id)
    # one writer per match at a time: two uploads of the same queue (a tap and the «online» event,
    # or a second session opened by a race) must not both store a mark (UX test N02)
    await ctx.db.execute(select(Match.id).where(Match.id == match.id).with_for_update())
    sessions = select(LiveTagSession.id).where(LiveTagSession.match_id == match.id)
    known = {
        t.client_id: t.id
        for t in (
            await ctx.db.scalars(
                select(LiveTag).where(
                    LiveTag.session_id.in_(sessions),
                    LiveTag.client_id.in_([i.client_id for i in items]),
                )
            )
        ).all()
    }
    stored = []
    for i in items:
        if i.client_id in known:
            stored.append({"client_id": i.client_id, "id": known[i.client_id]})
            continue
        tag = LiveTag(
            organization_id=s.organization_id,
            session_id=s.id,
            client_id=i.client_id,
            device_time=i.device_time,
            key=i.key,
            note=i.note,
        )
        ctx.db.add(tag)
        await ctx.db.flush()
        known[i.client_id] = tag.id
        stored.append({"client_id": i.client_id, "id": tag.id})
    if s.offset_ms is None and await _main_video(ctx, match.id):
        await sync_match(ctx, match.id, authorised=True)
    return {"stored": stored}


async def _main_video(ctx: Ctx, match_id: uuid.UUID) -> VideoAsset | None:
    return await timeline_video(ctx, match_id)


def _ms(dt: datetime) -> int:
    return round(dt.timestamp() * 1000)


async def sync_match(
    ctx: Ctx, match_id: uuid.UUID, authorised: bool = False
) -> list[dict[str, Any]]:
    """(Re)computes the offset of every mark session of the match that was not set by hand."""
    if not authorised:
        await get_match(ctx, match_id, Action.CLIP_WRITE)
    video = await _main_video(ctx, match_id)
    goals = [
        int(t)
        for t in (
            await ctx.db.scalars(
                select(Event.t_ms).where(
                    Event.match_id == match_id,
                    Event.type == "shot",
                    Event.outcome == "goal",
                    Event.t_ms.is_not(None),
                )
            )
        ).all()
        if t is not None
    ]
    prior = -_ms(video.recorded_at) if video and video.recorded_at else None
    out = []
    sessions = (
        await ctx.db.scalars(select(LiveTagSession).where(LiveTagSession.match_id == match_id))
    ).all()
    for s in sessions:
        if s.sync_source == "manual":
            out.append(_sync_out(s, 0))
            continue
        taps = [
            _ms(t)
            for t in (
                await ctx.db.scalars(
                    select(LiveTag.device_time).where(
                        LiveTag.session_id == s.id, LiveTag.key.in_(GOAL_KEYS)
                    )
                )
            ).all()
        ]
        r = estimate_offset(taps, goals, prior)
        s.offset_ms, s.sync_confidence, s.sync_source = r.offset_ms, r.confidence, r.source
        s.video_id = video.id if video and r.offset_ms is not None else None
        out.append(_sync_out(s, r.matched))
    return out


def _sync_out(s: LiveTagSession, matched: int) -> dict[str, Any]:
    return {
        "session_id": s.id,
        "offset_ms": s.offset_ms,
        "confidence": s.sync_confidence,
        "source": s.sync_source,
        "matched": matched,
    }


async def set_offset(ctx: Ctx, session_id: uuid.UUID, offset_ms: int) -> LiveTagSession:
    """Manual correction (e.g. after checking one mark in the video); later syncs keep it."""
    s, match = await _session(ctx, session_id)
    video = await _main_video(ctx, match.id)
    s.offset_ms, s.sync_confidence, s.sync_source = offset_ms, 1.0, "manual"
    s.video_id = video.id if video else None
    await audit.record(ctx, "marks.offset_set", target_type="live_tag_session", target_id=s.id)
    return s


async def marks(ctx: Ctx, match_id: uuid.UUID) -> dict[str, Any]:
    match = await get_match(ctx, match_id, Action.CLIP_WRITE)
    team = await ctx.db.get(Team, match.team_id)
    sessions = {
        s.id: s
        for s in (
            await ctx.db.scalars(select(LiveTagSession).where(LiveTagSession.match_id == match.id))
        ).all()
    }
    tags = (
        await ctx.db.scalars(
            select(LiveTag)
            .where(LiveTag.session_id.in_(list(sessions)))
            .order_by(LiveTag.device_time)
        )
    ).all()
    halftime: dict[uuid.UUID, datetime] = {}
    for t in tags:
        if t.key == HALFTIME and t.session_id not in halftime:
            halftime[t.session_id] = t.device_time
    labels = {
        k["key"]: k.get("label")
        for k in (team.settings.get("live_keys") if team else None) or DEFAULT_KEYS
    }
    items = []
    for t in tags:
        if t.key == HALFTIME:
            continue
        s = sessions[t.session_id]
        ht = halftime.get(t.session_id)
        items.append(
            {
                "id": t.id,
                "client_id": t.client_id,
                "session_id": t.session_id,
                "key": t.key,
                "label": labels.get(t.key),
                "note": t.note,
                "device_time": t.device_time,
                "half": 1 if ht is None or t.device_time < ht else 2,
                "t_ms": _ms(t.device_time) + s.offset_ms if s.offset_ms is not None else None,
            }
        )
    return {
        "sessions": [
            {
                "id": s.id,
                "device": s.device,
                "started_at": s.started_at,
                "offset_ms": s.offset_ms,
                "confidence": s.sync_confidence,
                "source": s.sync_source,
            }
            for s in sessions.values()
        ],
        "marks": items,
    }
