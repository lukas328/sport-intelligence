"""Identities of tracks and the physical load (M5)."""

from __future__ import annotations

import uuid

from sqlalchemy import select

from handball_api.core.errors import ProblemError
from handball_api.models import Match, RosterEntry, Track
from handball_api.models.enums import VideoStatus
from handball_api.services import audit, timeline
from handball_api.services.context import Ctx
from handball_api.services.matches import get_match
from handball_api.services.policies import Action
from handball_api.services.video_base import get_asset


async def set_track_identity(
    ctx: Ctx, asset_id: uuid.UUID, track_no: int, player_id: uuid.UUID | None, number: int | None
) -> Track:
    asset = await get_asset(ctx, asset_id, Action.EVENT_WRITE)
    track = await ctx.db.scalar(
        select(Track).where(Track.video_asset_id == asset.id, Track.track_no == track_no)
    )
    if track is None:
        raise ProblemError(404, "not-found", "Track not found")
    if player_id is not None:
        match = await ctx.db.get(Match, asset.match_id)
        assert match is not None
        if match.observed:
            # an observed match goes by shirt numbers: our roster plays no part in it (L4)
            raise ProblemError(422, "validation", "An observed match has no players of the team")
        entry = await ctx.db.scalar(
            select(RosterEntry).where(
                RosterEntry.season_id == match.season_id, RosterEntry.player_id == player_id
            )
        )
        if entry is None:
            raise ProblemError(422, "validation", "The player is not in this season's roster")
        if number is None:
            number = entry.jersey_number
    track.player_id, track.number = player_id, number
    cleared = player_id is None and number is None
    track.identity_source = None if cleared else "user_correction"
    track.player_confidence = None if cleared else 1.0
    await audit.record(
        ctx,
        "track.identity_set",
        target_type="video",
        target_id=asset.id,
        data={"track": track_no, "player_id": str(player_id) if player_id else None},
    )
    return track


BANDS = ("walk", "jog", "run", "sprint")


def _merge_physical(items: list[dict[str, object]]) -> dict[str, object]:
    """Sum of track fragments of one player (same rules as handball_vision.physical.merge)."""

    def f(d: dict[str, object], k: str) -> float:
        v = d.get(k)
        return float(v) if isinstance(v, int | float) else 0.0

    total = sum(f(p, "duration_s") for p in items) or 1.0
    heat: list[list[float]] = []
    for p in items:
        grid = p.get("heatmap")
        if not isinstance(grid, list) or not grid:
            continue
        w = f(p, "duration_s") / total
        if not heat:
            heat = [[0.0] * len(row) for row in grid]
        for r, row in enumerate(grid):
            for c, v in enumerate(row):
                heat[r][c] += float(v) * w
    bands: dict[str, float] = dict.fromkeys(BANDS, 0.0)
    for p in items:
        b = p.get("band_distance_m")
        if isinstance(b, dict):
            for k in BANDS:
                bands[k] += float(b.get(k, 0.0))
    return {
        "distance_m": round(sum(f(p, "distance_m") for p in items), 1),
        "duration_s": round(sum(f(p, "duration_s") for p in items), 1),
        "max_speed_ms": round(max((f(p, "max_speed_ms") for p in items), default=0.0), 2),
        "sprints": int(sum(f(p, "sprints") for p in items)),
        "band_distance_m": {k: round(v, 1) for k, v in bands.items()},
        "heatmap": [[round(v, 4) for v in row] for row in heat],
    }


async def match_physical(ctx: Ctx, match_id: uuid.UUID) -> dict[str, object]:
    """Physical load per identified player and per unidentified track of the main video (over
    all parts of the match: a player's distance of both halves adds up)."""
    match = await get_match(ctx, match_id)
    pairs = [
        (a, o)
        for a, o in (await timeline.Files.of(ctx, match.id)).all()
        if a.status == VideoStatus.READY
    ]
    if not pairs:
        return {"video_id": None, "players": [], "tracks": [], "estimated": True}
    main = pairs[0][0]
    offsets = {a.id: o for a, o in pairs}
    tracks = (
        await ctx.db.scalars(
            select(Track)
            .where(Track.video_asset_id.in_(list(offsets)))
            .order_by(Track.video_asset_id, Track.track_no)
        )
    ).all()
    by_player: dict[uuid.UUID, list[Track]] = {}
    loose = []
    for t in tracks:
        if t.team == "referee" or not t.physical:
            continue
        if t.player_id is not None:
            by_player.setdefault(t.player_id, []).append(t)
        else:
            loose.append(t)
    players = [
        {
            "player_id": str(pid),
            "number": ts[0].number,
            "team": ts[0].team,
            "tracks": [t.track_no for t in ts],
            **_merge_physical([t.physical for t in ts if t.physical]),
        }
        for pid, ts in by_player.items()
    ]
    players.sort(key=lambda p: -float(p["distance_m"]))  # type: ignore[arg-type]
    return {
        "video_id": str(main.id),
        "players": players,
        "tracks": [
            {
                "track_no": t.track_no,
                "team": t.team,
                "number": t.number,
                "first_ms": t.first_ms + offsets.get(t.video_asset_id, 0),
                "last_ms": t.last_ms + offsets.get(t.video_asset_id, 0),
                **_merge_physical([t.physical] if t.physical else []),
            }
            for t in loose
        ],
        "estimated": True,
    }
