"""Positions for goals that were marked by hand (BRIEF 7.2 stage 10, without the ball).

Courtside marks, the match sheet or tagging give the time of a goal and often the scorer's shirt
number, but not where the shot came from. The tracking knows where every player was: the shot
position is where the scorer (track with that shirt number) or else the attacker nearest to the
attacked goal came closest to it in the 10 s before the goal. Same rule as the overlay goals
(handball_vision.shots); the result is marked as estimated (`position_source`).
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from sqlalchemy import select

from handball_api.core.storage import ObjectNotFoundError
from handball_api.models import Event, Match, Track, VideoAsset
from handball_api.services.context import Ctx
from handball_api.services.matches import timeline_video

WINDOW_MS = 10_000
LENGTH, WIDTH = 40.0, 20.0


def _goal_distance(x: float, y: float, gx: float) -> float:
    return math.hypot(x - gx, y - min(max(y, 8.5), 11.5))


async def _rows(ctx: Ctx, asset: VideoAsset, t0: int, t1: int) -> np.ndarray:
    from handball_api.services.videos import media_prefix

    meta = asset.analysis or {}
    chunk_ms, chunks = meta.get("chunk_ms"), meta.get("chunks")
    if not isinstance(chunk_ms, int) or not isinstance(chunks, int) or chunk_ms <= 0:
        return np.zeros((0, 4), np.float32)
    parts = []
    for n in range(max(0, t0 // chunk_ms), min(chunks - 1, t1 // chunk_ms) + 1):
        try:
            data, _ = await ctx.storage.get(
                ctx.settings.s3_bucket_artifacts,
                f"{media_prefix(asset)}analysis/chunk_{n:05d}.bin",
            )
        except ObjectNotFoundError:
            continue
        parts.append(np.frombuffer(data, dtype="<f4").reshape(-1, 4))
    rows = np.concatenate(parts) if parts else np.zeros((0, 4), np.float32)
    return rows[(rows[:, 0] >= t0) & (rows[:, 0] <= t1)]


async def fill(ctx: Ctx, match: Match) -> int:
    """Shot positions for the match's goals with a video time and no position yet."""
    goals = (
        await ctx.db.scalars(
            select(Event).where(
                Event.match_id == match.id,
                Event.type == "shot",
                Event.outcome == "goal",
                Event.t_ms.is_not(None),
                Event.x.is_(None),
            )
        )
    ).all()
    if not goals:
        return 0
    asset = await timeline_video(ctx, match.id)
    if asset is None or not (asset.analysis or {}).get("chunks"):
        return 0
    tracks = (await ctx.db.scalars(select(Track).where(Track.video_asset_id == asset.id))).all()
    team_of = {t.track_no: str(t.team or "") for t in tracks}
    number_of = {t.track_no: t.number for t in tracks}
    filled = 0
    for g in goals:
        assert g.t_ms is not None
        label = "home" if g.side == "own" else "away"  # the own kit is "home" in the analysis
        rows = await _rows(ctx, asset, g.t_ms - WINDOW_MS, g.t_ms)
        attackers = [r for r in rows if team_of.get(int(r[1])) == label]
        if not attackers:
            continue
        gx = LENGTH if float(np.mean([r[2] for r in attackers])) > LENGTH / 2 else 0.0
        mine = [
            r for r in attackers if g.number is not None and number_of.get(int(r[1])) == g.number
        ]
        pool, method = (mine, "tracking_number") if mine else (attackers, "tracking_nearest")
        best = min(pool, key=lambda r: _goal_distance(float(r[2]), float(r[3]), gx))
        x, y = float(best[2]), float(best[3])
        if gx == 0.0:
            x, y = LENGTH - x, WIDTH - y
        g.x, g.y = round(x, 2), round(y, 2)
        attrs: dict[str, Any] = dict(g.attributes or {})
        attrs["position_source"] = method
        g.attributes = attrs
        filled += 1
    if filled:
        await ctx.db.flush()
    return filled
