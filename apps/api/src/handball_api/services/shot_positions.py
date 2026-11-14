"""Positions for goals that were marked by hand (BRIEF 7.2 stage 10, without the ball).

Courtside marks, the match sheet or tagging give the time of a goal and often the scorer's shirt
number, but not where the shot came from. The tracking knows where every player was: the shot
position is where the scorer (track with that shirt number) or else the attacker nearest to the
attacked goal came closest to it in the 10 s before the goal. Same rule as the overlay goals
(handball_vision.shots); the result is marked as estimated (`position_source`).

Where the shot came from (fourth real-video test H7): Prüfen asks «Von wo?» with one tap after a
confirmed goal (`set_spot`). The coach's answer is the zone of the three things (la, rl, rm, rr,
ra, kr, m7, gs) and, from a tap on the small court, a point in court metres; it is stored as the
event's shot_zone, shot_type (Siebenmeter: penalty, Gegenstoss: fast_break, as graphics.zone_of
reads them) and x/y, with `zone_source` "coach". Without an answer the estimate from the tracks
(`fill_one`) is the fallback: x/y and the zone from that point, `zone_source` "estimated".
"Weiss nicht" keeps the estimate and is not asked again (`zone_source` "unknown" without one).

Gegenstoss replaces the place in the question: for the three things a fast break is its own
pattern (zone gs, read from shot_type before shot_zone), and a second tap would double the
question. The goal keeps an estimated place from the tracks where there is one.
"""

from __future__ import annotations

import math
import uuid
from typing import Any

import numpy as np
from sqlalchemy import select

from handball_api.core.storage import ObjectNotFoundError
from handball_api.models import CameraCalibration, Event, Match, Track, VideoAsset
from handball_api.services.context import Ctx
from handball_api.services.timeline import Files
from handball_court.zones import shot_zone, spec

WINDOW_MS = 10_000
LENGTH, WIDTH = 40.0, 20.0

# the zones of the three things (left/right from the attacker's view: facing the goal, left is +y,
# on the half court with the goal at the top it is the left of the picture)
SPOT_ZONES = ("la", "rl", "rm", "rr", "ra", "kr", "m7", "gs")
# the event's shot zone (handball_court.zones) for a zone the coach tapped
EVENT_ZONE = {
    "la": "wing_left",
    "rl": "back_left",
    "rm": "back_centre",
    "rr": "back_right",
    "ra": "wing_right",
    "kr": "circle_centre",
    "m7": "penalty",
    "gs": "fast_break",
}
# shot zones of the events as zones of the graphics (graphics.ZONE)
GRAPHIC_ZONE = {
    "wing_left": "la",
    "back_left": "rl",
    "half_left": "rl",
    "back_centre": "rm",
    "half_centre": "rm",
    "back_right": "rr",
    "half_right": "rr",
    "wing_right": "ra",
    "circle_left": "kr",
    "circle_centre": "kr",
    "circle_right": "kr",
}
SEVEN_M = (33.0, 10.0)  # the 7 m mark in front of the attacked goal
COACH = "coach"
ESTIMATED = "estimated"
UNKNOWN = "unknown"


def event_zone_at(x: float, y: float) -> str:
    """The event's shot zone at a point (attacked goal at x = 40); a long throw counts as the back
    court of its side, so every point has a zone of the graphics."""
    z = shot_zone(x, y)
    if z != "long_range":
        return z
    dy = y - WIDTH / 2
    if abs(dy) < spec()["centre_half_width_m"]["back"]:
        return "back_centre"
    return "back_left" if dy > 0 else "back_right"


def zone_at(x: float, y: float) -> str:
    """The zone of the graphics at a point (attacked goal at x = 40)."""
    return GRAPHIC_ZONE.get(event_zone_at(x, y), "rm")


def zone_of(e: Event) -> str | None:
    """The zone of the three things: a penalty and a fast break by their kind, else the shot zone,
    else the zone at the shot spot (an overlay goal or an estimate carries only x/y, H7)."""
    if e.shot_type == "penalty":
        return "m7"
    if e.shot_type == "fast_break":
        return "gs"
    z = GRAPHIC_ZONE.get(e.shot_zone or "")
    if z is None and e.shot_zone is None and e.x is not None and e.y is not None:
        z = zone_at(e.x, e.y)
    return z


def zone_source(e: Event) -> str | None:
    """Who said where the shot came from: coach, estimated, unknown (coach did not know) or
    None (nobody yet)."""
    v = (e.attributes or {}).get("zone_source")
    return str(v) if v in (COACH, ESTIMATED, UNKNOWN) else None


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
    files = await Files.of(ctx, match.id)
    tracks_of: dict[uuid.UUID, list[Track]] = {}
    filled = 0
    for g in goals:
        filled += await fill_one(ctx, g, files, tracks_of)
    if filled:
        await ctx.db.flush()
    return filled


async def _attack(
    ctx: Ctx, g: Event, files: Files, tracks_of: dict[uuid.UUID, list[Track]]
) -> tuple[list[Any], float, dict[int, int | None]] | None:
    """The attacking side's positions in the 10 s before goal `g` (its part of the match), the
    goal they attack (x = 0 or 40, from where they are) and the shirt number per track."""
    if g.t_ms is None:
        return None
    hit = files.at(g.t_ms)
    if hit is None or not (hit[0].analysis or {}).get("chunks"):
        return None
    asset, local = hit
    if asset.id not in tracks_of:
        tracks_of[asset.id] = list(
            (await ctx.db.scalars(select(Track).where(Track.video_asset_id == asset.id))).all()
        )
    team_of = {t.track_no: str(t.team or "") for t in tracks_of[asset.id]}
    number_of = {t.track_no: t.number for t in tracks_of[asset.id]}
    label = "home" if g.side == "own" else "away"  # the own kit is "home" in the analysis
    rows = await _rows(ctx, asset, local - WINDOW_MS, local)
    attackers = [r for r in rows if team_of.get(int(r[1])) == label]
    if not attackers:
        return None
    gx = LENGTH if float(np.mean([r[2] for r in attackers])) > LENGTH / 2 else 0.0
    return attackers, gx, number_of


def goal_by_sides(asset: VideoAsset, local_ms: int, own: bool) -> float | None:
    """The goal a team attacks at `local_ms` of this file (x = 0 or 40), from the ends the
    analysis found for the half (the goalkeepers). Where the attackers stood in the seconds before
    says the wrong end for a fast break: they were defending at the other goal (seventh real-video
    test). None when the analysis found no ends."""
    sides = ((asset.analysis or {}).get("auto_events") or {}).get("sides") or []
    known = [s for s in sides if isinstance(s, dict) and s.get("home_defends") in ("left", "right")]
    if not known:
        return None
    cur = known[0]
    for s in known:
        if int(s.get("from_ms") or 0) <= local_ms:
            cur = s
    # the own kit is "home" in the analysis; the home team attacks right while it defends left
    return LENGTH if own == (cur["home_defends"] == "left") else 0.0


def side_in_image(homography: list[list[float]], goal_x: float) -> str | None:
    """Where the goal at `goal_x` (0 or 40) stands in the camera's picture, "left" or "right",
    from the court-to-image homography (any panning keeps the order of the two ends)."""

    def image_x(x: float) -> float | None:
        h = homography
        w = h[2][0] * x + h[2][1] * (WIDTH / 2) + h[2][2]
        if w <= 1e-9:
            return None
        return (h[0][0] * x + h[0][1] * (WIDTH / 2) + h[0][2]) / w

    a, b = image_x(0.0), image_x(LENGTH)
    if a is None or b is None or a == b:
        return None
    left_end = 0.0 if a < b else LENGTH
    return "left" if goal_x == left_end else "right"


async def goal_view(ctx: Ctx, g: Event) -> str | None:
    """Where the goal a shot went at stands in the video, "left" or "right", for drawing «Von wo?»
    as the camera sees the court (real-clip test of «Von wo?»): needs a court a person confirmed
    on that part of the match and the ends the analysis found for the half (or, without them,
    tracks of the attackers); None otherwise (the court is drawn with the goal at the top)."""
    files = await Files.of(ctx, g.match_id)
    hit = files.at(g.t_ms) if g.t_ms is not None else None
    if hit is None:
        return None
    cal = await ctx.db.scalar(
        select(CameraCalibration)
        .where(CameraCalibration.video_asset_id == hit[0].id)
        .order_by(CameraCalibration.created_at.desc())
        .limit(1)
    )
    if cal is None or cal.source != "user_correction":
        return None
    goal_x = goal_by_sides(hit[0], hit[1], g.side == "own")
    if goal_x is None:
        found = await _attack(ctx, g, files, {})
        goal_x = found[1] if found is not None else None
    return side_in_image(cal.homography, goal_x) if goal_x is not None else None


async def fill_one(
    ctx: Ctx,
    g: Event,
    files: Files | None = None,
    tracks_of: dict[uuid.UUID, list[Track]] | None = None,
) -> bool:
    """The estimated shot position of one goal from the tracks of its part of the match, and the
    zone at that point when nobody gave one; False when the tracks say nothing."""
    if g.t_ms is None or g.x is not None:
        return False
    files = files or await Files.of(ctx, g.match_id)
    tracks_of = {} if tracks_of is None else tracks_of
    # the goal's part of the match and the time in that file (Q-VIDEO-PARTS): a goal in the second
    # half reads the second file's tracks; the attacked goal is found per goal, so the change of
    # ends at half time needs nothing of its own
    found = await _attack(ctx, g, files, tracks_of)
    if found is None:
        return False
    attackers, gx, number_of = found
    mine = [r for r in attackers if g.number is not None and number_of.get(int(r[1])) == g.number]
    pool, method = (mine, "tracking_number") if mine else (attackers, "tracking_nearest")
    best = min(pool, key=lambda r: _goal_distance(float(r[2]), float(r[3]), gx))
    x, y = float(best[2]), float(best[3])
    if gx == 0.0:
        x, y = LENGTH - x, WIDTH - y
    g.x, g.y = round(x, 2), round(y, 2)
    attrs: dict[str, Any] = dict(g.attributes or {})
    attrs["position_source"] = method
    # the zone at that point, so the three things find it (graphics.zone_of reads shot_zone);
    # a zone the coach gave, a penalty or a fast break stays as it is
    if g.shot_type not in ("penalty", "fast_break") and zone_source(g) != COACH:
        g.shot_zone = event_zone_at(g.x, g.y)
        if zone_source(g) is None:
            attrs["zone_source"] = ESTIMATED
    g.attributes = attrs
    return True


async def set_spot(
    ctx: Ctx, g: Event, zone: str, x: float | None = None, y: float | None = None
) -> None:
    """Where the shot of goal `g` came from, as the coach said it: a zone of the three things
    (or "unknown"), and the tapped point in court metres (attacked goal at x = 40) when there
    is one."""
    attrs: dict[str, Any] = dict(g.attributes or {})
    if zone == UNKNOWN:
        # the coach does not know: the estimate from the tracks stands (or is made now)
        if zone_source(g) == COACH:
            g.shot_zone = None
            if g.shot_type in ("penalty", "fast_break"):
                g.shot_type = None
            if attrs.get("position_source") == COACH:
                g.x = g.y = None
                attrs.pop("position_source", None)
        attrs["zone_source"] = UNKNOWN
        g.attributes = attrs
        if g.x is None:
            await fill_one(ctx, g)
        elif g.shot_zone is None and g.shot_type not in ("penalty", "fast_break"):
            g.shot_zone = event_zone_at(g.x, g.y) if g.y is not None else None
        return
    if zone not in SPOT_ZONES:
        raise ValueError(f"unknown zone {zone}")
    g.shot_zone = EVENT_ZONE[zone]
    if zone == "m7":
        g.shot_type = "penalty"
        x, y = SEVEN_M
    elif zone == "gs":
        g.shot_type = "fast_break"
    elif g.shot_type in ("penalty", "fast_break"):
        g.shot_type = None
    if x is not None and y is not None:
        g.x, g.y = round(x, 2), round(y, 2)
        attrs["position_source"] = COACH
    elif g.x is not None and g.y is not None and zone not in ("m7", "gs"):
        # an estimated point in another zone than the coach's is not drawn there
        if attrs.get("position_source") == COACH or zone_at(g.x, g.y) != zone:
            g.x = g.y = None
            attrs.pop("position_source", None)
    elif g.x is None and zone == "gs":
        await fill_one(ctx, g)  # a fast break keeps an estimated place where the tracks have one
        attrs = dict(g.attributes or {})
    attrs["zone_source"] = COACH
    g.attributes = attrs
