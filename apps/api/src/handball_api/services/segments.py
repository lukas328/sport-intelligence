"""Several files per match and several matches per video (addendum 01, 4.8).

Files of one match are ordered by the camera clock in their metadata (fallback: upload order) and
the gap between the end of one file and the start of the next is shown. Match boundaries found in a
tournament video are offered as suggestions to split.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import delete, select

from handball_api.core.errors import ProblemError
from handball_api.models import Match, MatchSegment, VideoAsset
from handball_api.models.enums import VideoRole, VideoStatus
from handball_api.services.context import Ctx
from handball_api.services.matches import get_match, parts_of
from handball_api.services.policies import Action


def parse_recorded(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


async def rebuild(ctx: Ctx, match: Match) -> list[MatchSegment]:
    """Order of the main-camera files (the parts of the match timeline): by the camera clock,
    else by upload. A file being processed again keeps its place; failed files leave. Once a person
    swapped the order it is kept, and a file added later comes after the others."""
    old = {
        s.video_id: s
        for s in (
            await ctx.db.scalars(select(MatchSegment).where(MatchSegment.match_id == match.id))
        ).all()
    }
    videos = [
        v
        for v in (
            await ctx.db.scalars(
                select(VideoAsset).where(
                    VideoAsset.match_id == match.id,
                    VideoAsset.role == VideoRole.MAIN,
                    VideoAsset.status != VideoStatus.FAILED,
                )
            )
        ).all()
        if v.status == VideoStatus.READY or v.id in old
    ]
    ids = {v.id for v in videos}
    if old and set(old) == ids and all(s.confirmed for s in old.values()):
        return sorted(old.values(), key=lambda s: s.position)
    confirmed = any(s.confirmed for s in old.values())

    def natural(v: VideoAsset) -> tuple[bool, datetime, str]:
        return (v.recorded_at is None, v.recorded_at or v.created_at, v.filename)

    if confirmed:
        kept = sorted((v for v in videos if v.id in old), key=lambda v: old[v.id].position)
        videos = kept + sorted((v for v in videos if v.id not in old), key=natural)
    else:
        videos.sort(key=natural)
    await ctx.db.execute(delete(MatchSegment).where(MatchSegment.match_id == match.id))
    out = []
    prev: VideoAsset | None = None
    for i, v in enumerate(videos):
        gap = None
        if prev is not None and prev.recorded_at and v.recorded_at and prev.duration_s:
            gap = int(
                (v.recorded_at - prev.recorded_at).total_seconds() * 1000 - prev.duration_s * 1000
            )
        was = old.get(v.id)
        seg = MatchSegment(
            organization_id=match.organization_id,
            match_id=match.id,
            video_id=v.id,
            position=i,
            start_ms=0,
            end_ms=int((v.duration_s or 0) * 1000) or None,
            gap_before_ms=gap,
            source=was.source
            if was is not None and was.confirmed
            else ("metadata" if v.recorded_at else "upload_order"),
            confirmed=bool(was is not None and was.confirmed) or (confirmed and was is None),
        )
        ctx.db.add(seg)
        out.append(seg)
        prev = v
    await ctx.db.flush()
    return out


async def parts(ctx: Ctx, match_id: uuid.UUID) -> list[dict[str, Any]]:
    match = await get_match(ctx, match_id)
    offsets = {p.video_id: p.offset_ms for p in await parts_of(ctx, match.id)}
    rows = (
        await ctx.db.execute(
            select(MatchSegment, VideoAsset)
            .join(VideoAsset, VideoAsset.id == MatchSegment.video_id)
            .where(MatchSegment.match_id == match.id)
            .order_by(MatchSegment.position)
        )
    ).all()
    return [
        {
            "video_id": v.id,
            "filename": v.filename,
            "position": s.position,
            "start_ms": offsets.get(v.id),
            "duration_s": v.duration_s,
            "recorded_at": v.recorded_at,
            "gap_before_ms": s.gap_before_ms,
            "source": s.source,
            "confirmed": s.confirmed,
        }
        for s, v in rows
    ]


async def reorder(
    ctx: Ctx, match_id: uuid.UUID, video_ids: list[uuid.UUID]
) -> list[dict[str, Any]]:
    from handball_api.services import timeline  # imports this module (rebuild)

    match = await get_match(ctx, match_id, Action.VIDEO_UPLOAD)
    before = await parts_of(ctx, match.id)
    segs = {
        s.video_id: s
        for s in (
            await ctx.db.scalars(select(MatchSegment).where(MatchSegment.match_id == match.id))
        ).all()
    }
    if sorted(segs) != sorted(video_ids):
        raise ProblemError(422, "invalid-order", "Give every file exactly once")
    for i, vid in enumerate(video_ids):
        segs[vid].position = i
        segs[vid].confirmed = True
        segs[vid].source = "user_correction"
        segs[vid].gap_before_ms = None if i == 0 else segs[vid].gap_before_ms
    await ctx.db.flush()
    # everything of the match moves with its part (confirmed answers included)
    await timeline.apply_moves(ctx, match, timeline.moves(before, await parts_of(ctx, match.id)))
    await ctx.db.refresh(match)
    k = match.kickoff_ms or {}
    if "1" in k and "2" in k and int(k["1"]) > int(k["2"]):
        match.kickoff_ms = {"1": int(k["2"]), "2": int(k["1"])}
    await ctx.db.flush()
    return await parts(ctx, match_id)


async def boundaries(ctx: Ctx, match_id: uuid.UUID) -> list[dict[str, Any]]:
    """Suggested match boundaries from the analysis of the main video (tournaments)."""
    match = await get_match(ctx, match_id)
    out = []
    for v in (
        await ctx.db.scalars(
            select(VideoAsset).where(
                VideoAsset.match_id == match.id, VideoAsset.role == VideoRole.MAIN
            )
        )
    ).all():
        for b in ((v.analysis or {}).get("auto_events") or {}).get("boundaries") or []:
            out.append({"video_id": v.id, **b})
    return out
