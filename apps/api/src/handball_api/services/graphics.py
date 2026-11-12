"""Data of the Anlauf graphics (docs/design/ux-reset/ANLAUF.md, section 10).

One read model per match for the screens: the goal sequence of the report (Verlauf, Rail), each
goal as the scorer's run and the shot spot (Bundle, Zones, scene tiles), whether the court of the
video is confirmed, the phases from the report (power play, short-handed) and the estimated fast
breaks, and the questions for Prüfen. Per scene: the positions for the tactics camera.

Only what is measured is returned. Runs come from the tracking (positions 8 to 10 per second,
the 2 to 4 s before the shot of the track that scores); without a confirmed court there are no
positions. The ball is not detected here: `ball` stays empty until the ball and its holder come
from the analysis (docs/OPEN_QUESTIONS.md, Q-UX-15).

Demo matches (`is_demo`, seeded) have no real tracking (their video is synthetic): their runs
and positions are drawn from the marked events and a fixed seed, and every one of them says
`source: "demo"`.
"""

from __future__ import annotations

import math
import random
import uuid
from typing import Any

import numpy as np
from sqlalchemy import select

from handball_api.core.errors import ProblemError
from handball_api.models import CameraCalibration, Event, GoalCandidate, Match, Track, VideoAsset
from handball_api.services.context import Ctx
from handball_api.services.matches import get_match, timeline_video
from handball_api.services.shot_positions import _rows

LENGTH, WIDTH = 40.0, 20.0
RUN_MS = 3000  # the run before the shot: 2 to 4 s
SCENE_MS = 6000  # a scene on the tactics camera
SAMPLE_MS = 110  # about 9 positions per second
ESTIMATED_SOURCES = {"heuristic", "scoreboard_ocr"}
TEAM_OF_TRACK = {"home": "own", "home_gk": "own", "away": "opp", "away_gk": "opp", "referee": "ref"}

# shot zones of the events (left/right from the attacker's view) as zones of the graphics
ZONE = {
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


def zone_of(e: Event) -> str | None:
    if e.shot_type == "penalty":
        return "m7"
    if e.shot_type == "fast_break":
        return "gs"
    return ZONE.get(e.shot_zone or "")


def to_half(x: float, y: float) -> tuple[float, float]:
    """Court metres with the attacked goal at x = 40 (the events' convention) to the half court
    of the graphics: goal at the top, u across from the attacker's left, v from the goal line."""
    return (round(WIDTH - y, 2), round(LENGTH - x, 2))


def minute_of(e: Event) -> float | None:
    return round(e.clock_s / 60, 2) if e.clock_s is not None else None


def _team(side: str) -> str:
    return "own" if side == "own" else "opp"


async def _field_confirmed(ctx: Ctx, asset: VideoAsset | None) -> bool | None:
    """None without a video; True once a person confirmed the court (or set it by hand)."""
    if asset is None:
        return None
    cal = await ctx.db.scalar(
        select(CameraCalibration)
        .where(CameraCalibration.video_asset_id == asset.id)
        .order_by(CameraCalibration.created_at.desc())
        .limit(1)
    )
    return cal is not None and cal.source == "user_correction"


def _has_tracking(asset: VideoAsset | None) -> bool:
    return asset is not None and isinstance((asset.analysis or {}).get("chunks"), int)


# ---- demo: positions for seeded matches without tracking ---------------------------------------

# where a goal of a zone is shot from (half court, goal at the top), as in the design's demo data
DEMO_ZONE = {
    "la": ((0.7, 2.8), (0.8, 3.0)),
    "ra": ((17.2, 19.3), (0.8, 3.0)),
    "rl": ((3.8, 7.6), (8.6, 11.2)),
    "rm": ((8.4, 11.6), (8.8, 11.8)),
    "rr": ((12.4, 16.2), (8.6, 11.2)),
    "kr": ((8.0, 12.0), (6.0, 7.0)),
    "m7": ((10.0, 10.0), (7.0, 7.0)),
    "gs": ((6.5, 13.5), (4.5, 7.5)),
}


def _rng(e: Event) -> random.Random:
    return random.Random(int(e.id.hex[:12], 16))  # noqa: S311 (demo positions, not secrets)


def demo_run(e: Event) -> tuple[list[tuple[float, float]], tuple[float, float]]:
    """A run and a shot spot for a seeded goal (half court), from its zone; fixed per event."""
    r = _rng(e)
    z = zone_of(e) or "rm"
    (u0, u1), (v0, v1) = DEMO_ZONE[z]
    u, v = u0 + r.random() * (u1 - u0), v0 + r.random() * (v1 - v0)
    if z in ("la", "ra"):
        s = -1 if z == "la" else 1
        pts = [
            (u + s * (0.2 + r.random() * 0.6), v + 6 + r.random() * 4),
            (u + s * (0.6 + r.random()), v + 3 + r.random() * 1.5),
            (u - s * r.random() * 0.6, v + 1.2),
            (u, v),
        ]
    elif z == "gs":
        a = 3 + r.random() * 14
        pts = [
            (a, 19.6),
            (a + (u - a) * 0.35 + (r.random() - 0.5) * 2, 14 + r.random() * 2),
            (u + (r.random() - 0.5) * 1.5, v + 3.5),
            (u, v),
        ]
    elif z == "kr":
        s = -1 if r.random() < 0.5 else 1
        pts = [
            (u + s * (2.5 + r.random() * 2), v + 0.4 + r.random() * 0.6),
            (u + s * (1.2 + r.random()), v + 0.2 + r.random() * 0.5),
            (u + s * 0.4, v + 0.1),
            (u, v),
        ]
    elif z == "m7":
        pts = [(u, v + 2.2), (u, v + 1.1), (u, v)]
    else:
        dx = (r.random() - 0.5) * 7
        pts = [
            (u + dx, v + 4.5 + r.random() * 3),
            (u + dx * 0.55, v + 2.6 + r.random()),
            (u + dx * 0.15, v + 0.9),
            (u, v),
        ]
    clamp = [(round(min(19.7, max(0.3, p)), 2), round(min(19.8, max(0.3, q)), 2)) for p, q in pts]
    return clamp, clamp[-1]


def _half_to_court(u: float, v: float) -> tuple[float, float]:
    """Half court back to court metres, the attacked goal at x = 0 (left half, as the camera)."""
    return (round(v, 2), round(u, 2))


def demo_scene(e: Event) -> list[dict[str, Any]]:
    """Positions of a seeded scene on the left half (goal at x = 0): the scorer runs his demo run,
    five team mates and seven defenders hold a 6:0 shape and move a little, one referee."""
    r = _rng(e)
    run, _ = demo_run(e)
    scorer = [_half_to_court(u, v) for u, v in run]
    attack = "own" if e.side == "own" else "opp"
    defence = "opp" if attack == "own" else "own"

    def drift(x: float, y: float, dx: float, dy: float, n: int = 4) -> list[tuple[float, float]]:
        return [(round(x + dx * i / (n - 1), 2), round(y + dy * i / (n - 1), 2)) for i in range(n)]

    tracks: list[dict[str, Any]] = [{"team": attack, "number": e.number, "xy": scorer}]
    # attackers: backs and wings, the circle runner between the defenders
    for x, y in [(10.5, 4.5), (11.5, 10.0), (10.5, 15.5), (1.5, 1.2), (1.5, 18.8), (6.4, 10.0)][:5]:
        dx, dy = (r.random() - 0.5) * 1.6, (r.random() - 0.5) * 1.6
        tracks.append(
            {
                "team": attack,
                "number": r.choice([None, r.randint(2, 30)]),
                "xy": drift(x, y, dx, dy),
            }
        )
    # defence 6:0 on the 6 m line, shifting towards the ball side, and the keeper
    ball_y = scorer[-1][1]
    for y in [2.5, 5.5, 8.5, 11.5, 14.5, 17.5]:
        x = 6.3 + 0.25 * math.cos((y - 10) / 10 * math.pi)
        tracks.append(
            {
                "team": defence,
                "number": r.choice([None, r.randint(2, 30)]),
                "xy": drift(x, y, 0.3, (ball_y - y) * 0.12),
            }
        )
    tracks.append(
        {
            "team": defence,
            "number": 1 if r.random() < 0.5 else None,
            "xy": drift(0.9, 10.0, 0.2, (ball_y - 10) * 0.15),
        }
    )
    tracks.append({"team": "ref", "number": None, "xy": drift(12.0, 1.6, -2.4, -0.1, 3)})
    return tracks


# ---- the match --------------------------------------------------------------------------------


async def _goals(ctx: Ctx, match: Match) -> list[Event]:
    return list(
        (
            await ctx.db.scalars(
                select(Event)
                .where(Event.match_id == match.id, Event.type == "shot", Event.outcome == "goal")
                .order_by(Event.clock_s.nulls_last(), Event.t_ms.nulls_last())
            )
        ).all()
    )


async def _tracking_run(
    ctx: Ctx, asset: VideoAsset, tracks: list[Track], e: Event
) -> list[tuple[float, float]]:
    """The scorer's track in the 3 s before the goal (the track with the scorer's number on the
    attacking side), in half-court coordinates; empty when the tracking has no such track."""
    if e.t_ms is None or e.number is None:
        return []
    label = "home" if e.side == "own" else "away"
    nos = {
        t.track_no for t in tracks if t.number == e.number and str(t.team or "").startswith(label)
    }
    if not nos:
        return []
    rows = await _rows(ctx, asset, e.t_ms - RUN_MS, e.t_ms)
    mine = rows[np.isin(rows[:, 1].astype(int), list(nos))] if len(rows) else rows
    if len(mine) < 3:
        return []
    mine = mine[np.argsort(mine[:, 0])]
    gx = LENGTH if float(np.mean(mine[:, 2])) > LENGTH / 2 else 0.0
    pts: list[tuple[float, float]] = []
    last = -1e9
    for t, _, x, y in mine:
        if t - last < SAMPLE_MS:
            continue
        last = float(t)
        cx, cy = (float(x), float(y)) if gx == LENGTH else (LENGTH - float(x), WIDTH - float(y))
        pts.append(to_half(cx, cy))
    return pts


async def match_graphics(ctx: Ctx, match_id: uuid.UUID) -> dict[str, Any]:
    match = await get_match(ctx, match_id)
    asset = await timeline_video(ctx, match.id)
    tracking = _has_tracking(asset)
    tracks = (
        list((await ctx.db.scalars(select(Track).where(Track.video_asset_id == asset.id))).all())
        if tracking and asset is not None
        else []
    )
    confirmed_field = await _field_confirmed(ctx, asset)
    demo = match.is_demo  # seeded: the synthetic video says nothing about the match
    goals = await _goals(ctx, match)

    report = [
        {"minute": minute_of(e), "team": _team(e.side)} for e in goals if e.clock_s is not None
    ]

    runs: list[dict[str, Any]] = []
    for e in goals:
        attrs = e.attributes or {}
        estimated_spot = bool(attrs.get("position_source")) or e.source in ESTIMATED_SOURCES
        run: list[tuple[float, float]] = []
        shot = to_half(e.x, e.y) if e.x is not None and e.y is not None else None
        source = "marked" if shot else None
        if demo:
            run, shot = demo_run(e)
            source = "demo"
        elif tracking and asset is not None and confirmed_field:
            run = await _tracking_run(ctx, asset, tracks, e)
            if run:
                source = "tracking"
                shot = shot or run[-1]
        if shot is None:
            continue
        runs.append(
            {
                "event_id": e.id,
                "team": _team(e.side),
                "minute": minute_of(e),
                "number": e.number,
                "zone": zone_of(e),
                "run": run,
                "shot": shot,
                # where on the goal is only marked by hand (goal_zone); never drawn as a flight
                "aim": None,
                "confirmed": not estimated_spot,
                "source": source,
                "has_video": e.t_ms is not None,
                "t_ms": e.t_ms,
            }
        )

    return {
        "has_video": asset is not None,
        "field_confirmed": True if demo else confirmed_field,
        "report_goals": report,
        "goals": runs,
        "phases": await _phases(ctx, match, goals),
        # the court first: until it is confirmed the analysis draws no positions (demo matches
        # show invented ones, the real court of their video is still asked)
        "checks": (
            [_field_check(asset)]
            if asset is not None and tracking and confirmed_field is False
            else []
        )
        + await _checks(ctx, match),
        "source": "demo" if demo else "analysis",
    }


async def _phases(ctx: Ctx, match: Match, goals: list[Event]) -> list[dict[str, Any]]:
    """Power play and short-handed play from the 2-minute penalties of the report; fast breaks
    as marked (estimated when they come from the video)."""
    pens = (
        await ctx.db.scalars(
            select(Event).where(
                Event.match_id == match.id,
                Event.type == "suspension_2min",
                Event.clock_s.is_not(None),
            )
        )
    ).all()
    out: list[dict[str, Any]] = []
    for kind, side in (("power_play", "opponent"), ("short_handed", "own")):
        windows = sorted(
            (float(p.clock_s or 0), float(p.clock_s or 0) + 120) for p in pens if p.side == side
        )
        if not windows:
            continue
        us = them = 0
        for g in goals:
            if g.clock_s is not None and any(a <= g.clock_s < b for a, b in windows):
                us, them = (us + 1, them) if g.side == "own" else (us, them + 1)
        out.append(
            {
                "kind": kind,
                "count": len(windows),
                "windows": [[round(a / 60, 2), round(b / 60, 2)] for a, b in windows],
                "goals_us": us,
                "goals_them": them,
                "estimated": False,
            }
        )
    fb = [g for g in goals if g.shot_type == "fast_break"]
    if fb:
        out.append(
            {
                "kind": "fast_break",
                "count": len(fb),
                "windows": [],
                "goals_us": sum(1 for g in fb if g.side == "own"),
                "goals_them": sum(1 for g in fb if g.side != "own"),
                "estimated": any(g.source in ESTIMATED_SOURCES for g in fb),
            }
        )
    return out


def _field_check(asset: VideoAsset) -> dict[str, Any]:
    return {
        "id": asset.id,
        "kind": "field",
        "frame_ref": 0,
        "box": None,
        "seconds_in_view": None,
        "suggested_side": None,
        "candidates": [],
    }


async def _checks(ctx: Ctx, match: Match) -> list[dict[str, Any]]:
    """Questions for Prüfen: the open goal and shot candidates of the video. A question about a
    person needs a box in the picture, which the analysis does not deliver yet: not asked."""
    rows = (
        await ctx.db.scalars(
            select(GoalCandidate)
            .where(GoalCandidate.match_id == match.id, GoalCandidate.status == "open")
            .order_by(GoalCandidate.kind, GoalCandidate.rank, GoalCandidate.goal_ms)
        )
    ).all()
    return [
        {
            "id": c.id,
            "kind": c.kind,
            "frame_ref": c.goal_ms,
            "box": None,
            "seconds_in_view": None,
            "suggested_side": c.suggested_side,
            "candidates": [],
        }
        for c in rows
    ]


# ---- one scene ------------------------------------------------------------------------------


async def scene_camera(ctx: Ctx, match_id: uuid.UUID, event_id: uuid.UUID) -> dict[str, Any]:
    """Positions of the 6 s before a goal for the tactics camera, in court metres (goal of the
    attack at x = 0, the left half). Only with a confirmed court; the ball stays empty."""
    match = await get_match(ctx, match_id)
    e = await ctx.db.get(Event, event_id)
    if e is None or e.match_id != match.id:
        raise ProblemError(404, "not-found", "No such event")
    asset = await timeline_video(ctx, match.id)
    tracking = _has_tracking(asset)
    demo = match.is_demo  # seeded: the synthetic video says nothing about the match
    field = True if demo else await _field_confirmed(ctx, asset)
    clock = e.clock_s
    base: dict[str, Any] = {
        "event_id": e.id,
        "clock_s": max(0.0, clock - SCENE_MS / 1000) if clock is not None else None,
        "duration_s": SCENE_MS / 1000,
        "field_confirmed": field,
        "tracks": [],
        "ball": [],
        "scorer": {"team": _team(e.side), "number": e.number} if e.number is not None else None,
        "shot": None,
        "confirmed": not (
            bool((e.attributes or {}).get("position_source")) or e.source in ESTIMATED_SOURCES
        ),
        "source": "demo" if demo else "analysis",
    }
    if demo:
        tracks = demo_scene(e)
        base["tracks"] = tracks
        base["shot"] = list(tracks[0]["xy"][-1])
        return base
    if not field or not tracking or asset is None or e.t_ms is None:
        return base
    rows = await _rows(ctx, asset, e.t_ms - SCENE_MS, e.t_ms)
    if not len(rows):
        return base
    meta = {
        t.track_no: t
        for t in (await ctx.db.scalars(select(Track).where(Track.video_asset_id == asset.id))).all()
    }
    attack = "home" if e.side == "own" else "away"
    att = [
        r for r in rows if str(getattr(meta.get(int(r[1])), "team", "") or "").startswith(attack)
    ]
    flip = bool(att) and float(np.mean([r[2] for r in att])) > LENGTH / 2  # attack to the left half
    out: dict[int, list[tuple[float, float]]] = {}
    last: dict[int, float] = {}
    for t, no, x, y in rows[np.argsort(rows[:, 0])]:
        n = int(no)
        if t - last.get(n, -1e9) < SAMPLE_MS:
            continue
        last[n] = float(t)
        px, py = (LENGTH - float(x), WIDTH - float(y)) if flip else (float(x), float(y))
        out.setdefault(n, []).append((round(px, 2), round(py, 2)))
    for n, xy in out.items():
        tr = meta.get(n)
        team = TEAM_OF_TRACK.get(str(getattr(tr, "team", "") or ""))
        if team is None or len(xy) < 2:
            continue
        base["tracks"].append(
            {
                "team": team,
                "number": getattr(tr, "number", None) if team != "ref" else None,
                "xy": xy,
            }
        )
    scorer = next(
        (
            t
            for t in base["tracks"]
            if e.number is not None and t["team"] == _team(e.side) and t["number"] == e.number
        ),
        None,
    )
    if scorer:
        base["shot"] = list(scorer["xy"][-1])
    return base
