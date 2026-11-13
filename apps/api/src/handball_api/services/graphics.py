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
from handball_api.models import (
    CameraCalibration,
    Event,
    GoalCandidate,
    Match,
    ProcessingJob,
    Track,
    VideoAsset,
)
from handball_api.services.context import Ctx
from handball_api.services.events import clock_from_video
from handball_api.services.matches import (
    REPORT_SOURCES,
    duration_ms,
    get_match,
    timeline_video,
)
from handball_api.services.shot_positions import _rows

LENGTH, WIDTH = 40.0, 20.0
RUN_MS = 3000  # the run before the shot: 2 to 4 s
# a scene on the tactics camera: before the goal, not the way back after it (third real-video
# test G3): the candidate time lies 4 to 7 s after the goal, a confirmed goal has its own time
SCENE_MS = 10000
SCENE_AFTER_MS = 2000  # the scene ends this long after the goal time
COURT_MARGIN = 1.0  # metres around the court still drawn; beyond: spectators, the bench
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


def _shown_field(
    demo: bool, asset: VideoAsset | None, tracking: bool, confirmed: bool | None
) -> bool | None:
    """Whether positions may be drawn. A demo match shows invented positions, but not while the
    court of its video is still asked in Prüfen (UX test B12: «zeigen wir keine Positionen» must
    hold); a real match only with a confirmed court."""
    if not demo:
        return confirmed
    return not (asset is not None and tracking and confirmed is False)


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
                "number": None,  # only the scorer's number is known (UX test B39)
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
                "number": None,
                "xy": drift(x, y, 0.3, (ball_y - y) * 0.12),
            }
        )
    tracks.append(
        {
            "team": defence,
            "number": None,
            "xy": drift(0.9, 10.0, 0.2, (ball_y - 10) * 0.15),
        }
    )
    tracks.append({"team": "ref", "number": None, "xy": drift(12.0, 1.6, -2.4, -0.1, 3)})
    return tracks


def unique_numbers(tracks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """A read number is shown once per team and moment: the longest track keeps it, the others
    lose it (two own players with a 15 on one camera, UX test B39)."""
    keep: dict[tuple[str, int], int] = {}
    for i, t in enumerate(tracks):
        n = t.get("number")
        if n is None:
            continue
        k = (str(t.get("team")), int(n))
        if k not in keep or len(t.get("xy") or []) > len(tracks[keep[k]].get("xy") or []):
            keep[k] = i
    shown = set(keep.values())
    return [
        t if t.get("number") is None or i in shown else {**t, "number": None}
        for i, t in enumerate(tracks)
    ]


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
    field = _shown_field(demo, asset, tracking, confirmed_field)
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
        if demo and field:
            run, shot = demo_run(e)
            source = "demo"
        elif demo:
            pass  # court not confirmed: no invented run, only a spot marked by hand
        elif tracking and asset is not None and confirmed_field:
            run = await _tracking_run(ctx, asset, tracks, e)
            if run:
                source = "tracking"
                shot = shot or run[-1]
        # a confirmed goal without a spot is still a goal: score, course, list, scene (real-video
        # test E01); only the drawings need the spot and leave it out
        runs.append(
            {
                "event_id": e.id,
                "team": _team(e.side),
                "minute": minute_of(e),
                "number": e.number,
                "player_id": e.player_id,
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

    job = await _analysis_job(ctx, asset)
    return {
        "has_video": asset is not None,
        "analysis": _job_state(job),
        # when the analysis was done: the start puts a fresh one in its head (second round)
        "analysis_at": job.finished_at if job is not None and _job_state(job) == "ready" else None,
        # a match report brought goals (handball.ch, a paper report): «Spielbericht» only then
        # (real-video test F6; the course also carries the video's goals)
        "has_report": any(e.source in REPORT_SOURCES for e in goals),
        "span": _span(match, asset),
        "field_confirmed": field,
        "report_goals": report,
        "goals": runs,
        "phases": await _phases(ctx, match, goals),
        # the court first: until it is confirmed the analysis draws no positions (demo matches
        # show invented ones, the real court of their video is still asked)
        "checks": await _open_checks(ctx, match, asset, tracking, confirmed_field),
        "more_checks": await more_checks(ctx, match),
        "source": "demo" if demo else "analysis",
    }


async def _analysis_job(ctx: Ctx, asset: VideoAsset | None) -> ProcessingJob | None:
    if asset is None:
        return None
    return await ctx.db.scalar(
        select(ProcessingJob)
        .where(ProcessingJob.video_asset_id == asset.id, ProcessingJob.kind == "analysis")
        .order_by(ProcessingJob.created_at.desc())
        .limit(1)
    )


def _job_state(job: ProcessingJob | None) -> str:
    if job is None:
        return "none"
    return {
        "queued": "running",
        "running": "running",
        "succeeded": "ready",
        "failed": "failed",
    }.get(str(job.status.value if hasattr(job.status, "value") else job.status), "none")


async def analysis_status(ctx: Ctx, asset: VideoAsset | None) -> str:
    """none, running, ready or failed: the latest analysis job of the video. «Analyse fertig» is
    said only once it is ready (real-video test E06)."""
    return _job_state(await _analysis_job(ctx, asset))


def _span(match: Match, asset: VideoAsset | None) -> list[float] | None:
    """The match minutes the video covers, once the throw-off is set: the course is drawn over
    that stretch, not over a whole match (real-video test E10). Null without throw-off."""
    if asset is None or match.is_demo:
        return None
    length = duration_ms(asset)
    first = min((int(v) for v in (match.kickoff_ms or {}).values()), default=None)
    if length is None or first is None:
        return None
    start = clock_from_video(match, max(0, 0 if first <= 0 else first))
    end = clock_from_video(match, length)
    if start is None or end is None:
        return None
    total = match.period_s * match.periods / 60
    return [round(max(0.0, start[1] / 60), 2), round(min(total, end[1] / 60), 2)]


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


def kickoff_missing(match: Match, length_ms: int | None) -> list[int]:
    """The halves whose throw-off Prüfen asks: the first while it is not set, the second once the
    video runs a break past the first half (the same rule as web lib/match-workflow.ts)."""
    k = match.kickoff_ms or {}
    first = k.get("1")
    if first is None:
        return [1]
    second = length_ms is not None and length_ms > int(first) + match.period_s * 1000 + 5 * 60_000
    return [2] if second and k.get("2") is None else []


def _kickoff_check(match: Match, asset: VideoAsset | None = None) -> list[dict[str, Any]]:
    """The throw-off, asked in Prüfen while it is not set (UX test B10): it ties the match clock
    to the video. `frame_ref` is the half."""
    return [
        {
            "id": uuid.uuid5(match.id, f"kickoff:{period}"),
            "kind": "kickoff",
            "frame_ref": period,
            "box": None,
            "seconds_in_view": None,
            "suggested_side": None,
            "candidates": [],
        }
        for period in kickoff_missing(match, duration_ms(asset) if asset is not None else None)
    ]


async def _open_checks(
    ctx: Ctx, match: Match, asset: VideoAsset | None, tracking: bool, confirmed_field: bool | None
) -> list[dict[str, Any]]:
    """Every open question of Prüfen, in the order they are asked: the court, the throw-off,
    then the goal and shot candidates."""
    return (
        (
            [_field_check(asset)]
            if asset is not None and tracking and confirmed_field is False
            else []
        )
        + (_kickoff_check(match, asset) if asset is not None and not match.is_demo else [])
        + await _checks(ctx, match)
    )


async def open_checks(ctx: Ctx, match: Match) -> list[dict[str, Any]]:
    """The open questions of a match: the one count the mail, the start and Prüfen share (UX
    test A02)."""
    asset = await timeline_video(ctx, match.id)
    tracking = _has_tracking(asset)
    return await _open_checks(ctx, match, asset, tracking, await _field_confirmed(ctx, asset))


SAME_MOMENT_MS = 5000  # two candidates this close, for the same side, are one goal


def _windows(rows: list[GoalCandidate]) -> list[list[GoalCandidate]]:
    """Candidates of one goal: their goal times lie within SAME_MOMENT_MS and they suggest the
    same side (real-video test E12, F4). Overlapping clips alone are not enough: two goals 12 s
    apart (goal, throw-off, fast break) are normal. Each group is measured against its first
    candidate, so no chain of neighbours merges several goals."""
    groups: list[list[GoalCandidate]] = []
    for c in sorted(rows, key=lambda c: c.goal_ms):
        home = next(
            (
                g
                for g in groups
                if abs(c.goal_ms - g[0].goal_ms) < SAME_MOMENT_MS
                and c.suggested_side == g[0].suggested_side
            ),
            None,
        )
        if home is None:
            groups.append([c])
        else:
            home.append(c)
    return groups


async def _goal_questions(
    ctx: Ctx, match: Match
) -> tuple[list[GoalCandidate], list[GoalCandidate]]:
    """The goal candidates to ask: one per moment, none where a goal of that moment is already
    confirmed. First those of the default rate (the strongest, what three things need), the
    others as «Wenn du magst» (E07). Shot candidates are not asked in Prüfen and not counted."""
    from handball_api.services.goal_candidates import DEFAULT_RATE

    rows = (
        await ctx.db.scalars(
            select(GoalCandidate).where(
                GoalCandidate.match_id == match.id,
                GoalCandidate.kind == "goal",
                GoalCandidate.status.in_(("open", "confirmed")),
            )
        )
    ).all()
    asked: list[GoalCandidate] = []
    for group in _windows(list(rows)):
        if any(c.status == "confirmed" for c in group):
            continue
        asked.append(min(group, key=lambda c: (c.rate, -c.score, c.rank)))
    first = [c for c in asked if c.rate <= DEFAULT_RATE["goal"]]
    more = [c for c in asked if c.rate > DEFAULT_RATE["goal"]]
    order = lambda c: c.goal_ms  # noqa: E731
    return sorted(first, key=order), sorted(more, key=order)


def _check_of(c: GoalCandidate) -> dict[str, Any]:
    return {
        "id": c.id,
        "kind": c.kind,
        "frame_ref": c.goal_ms,
        "box": None,
        "seconds_in_view": None,
        "suggested_side": c.suggested_side,
        "candidates": [],
    }


async def _checks(ctx: Ctx, match: Match) -> list[dict[str, Any]]:
    """Questions for Prüfen: the goal candidates worth asking first. A question about a person
    needs a box in the picture, which the analysis does not deliver yet: not asked here."""
    first, _ = await _goal_questions(ctx, match)
    return [_check_of(c) for c in first]


async def more_checks(ctx: Ctx, match: Match) -> list[dict[str, Any]]:
    """The goal candidates of a lower rank: offered as «Wenn du magst: n weitere», not counted."""
    _, more = await _goal_questions(ctx, match)
    return [_check_of(c) for c in more]


# ---- one scene ------------------------------------------------------------------------------


async def scene_camera(ctx: Ctx, match_id: uuid.UUID, event_id: uuid.UUID) -> dict[str, Any]:
    """Positions of the 6 s before a goal for the tactics camera, in court metres (goal of the
    attack at x = 0, the left half). Only with a confirmed court; the ball stays empty."""
    match = await get_match(ctx, match_id)
    e = await ctx.db.get(Event, event_id)
    if e is None or e.match_id != match.id:
        raise ProblemError(404, "not-found", "No such event")
    return await camera_of(ctx, match, e)


def scene_tracks(
    rows: np.ndarray, teams: dict[int, tuple[str, int | None]], start: float, ours: bool
) -> tuple[list[dict[str, Any]], bool]:
    """The tracks of one scene from the position rows (t, track, x, y): only positions on the
    court, about 9 per second, with their time in the scene; and whether the attack goes to
    the goal at x = 40. Not mirrored: the court shows the goal on the side the video shows it
    (third real-video test G3)."""
    attack = "home" if ours else "away"
    att = [r for r in rows if teams.get(int(r[1]), ("", None))[0].startswith(attack)]
    right = bool(att) and float(np.mean([r[2] for r in att])) > LENGTH / 2
    out: dict[int, list[tuple[float, float]]] = {}
    times: dict[int, list[float]] = {}
    last: dict[int, float] = {}
    for t, no, x, y in rows[np.argsort(rows[:, 0])]:
        n = int(no)
        px, py = float(x), float(y)
        # only what stands on the court: spectators and the bench in front are not players
        if not on_court(px, py):
            continue
        if t - last.get(n, -1e9) < SAMPLE_MS:
            continue
        last[n] = float(t)
        out.setdefault(n, []).append((round(px, 2), round(py, 2)))
        # when in the scene (0 to 1): a track is drawn only while it exists (real-video test F5)
        times.setdefault(n, []).append(round(min(1.0, max(0.0, (float(t) - start) / SCENE_MS)), 4))
    tracks: list[dict[str, Any]] = []
    for n, xy in out.items():
        kind, number = teams.get(n, ("", None))
        team = TEAM_OF_TRACK.get(kind)
        if team is None or len(xy) < 2:
            continue
        tracks.append(
            {"team": team, "number": number if team != "ref" else None, "xy": xy, "ts": times[n]}
        )
    return tracks, right


def on_court(x: float, y: float) -> bool:
    """A position on the court or just beside it (COURT_MARGIN)."""
    m = COURT_MARGIN
    return -m <= x <= LENGTH + m and -m <= y <= WIDTH + m


async def camera_of(ctx: Ctx, match: Match, e: Event) -> dict[str, Any]:
    """The tactics camera of one goal, without the access check: for the caller that checked
    access itself (the match page above, a share link for the shared scenes)."""
    asset = await timeline_video(ctx, match.id)
    tracking = _has_tracking(asset)
    demo = match.is_demo  # seeded: the synthetic video says nothing about the match
    field = _shown_field(demo, asset, tracking, await _field_confirmed(ctx, asset))
    clock = e.clock_s
    base: dict[str, Any] = {
        "event_id": e.id,
        "clock_s": max(0.0, clock - (SCENE_MS - SCENE_AFTER_MS) / 1000)
        if clock is not None
        else None,
        # without the throw-off the scene still has its place in the video (E02)
        "video_s": max(0.0, (e.t_ms - SCENE_MS + SCENE_AFTER_MS) / 1000)
        if e.t_ms is not None
        else None,
        # the attack goes to the goal at x = 40: drawn on that side, as the video shows it (G3)
        "right": False,
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
    if demo and field:
        tracks = unique_numbers(demo_scene(e))
        base["tracks"] = tracks
        base["shot"] = list(tracks[0]["xy"][-1])
        return base
    if demo or not field or not tracking or asset is None or e.t_ms is None:
        return base
    start = e.t_ms - SCENE_MS + SCENE_AFTER_MS
    rows = await _rows(ctx, asset, start, start + SCENE_MS)
    if not len(rows):
        return base
    meta = {
        t.track_no: t
        for t in (await ctx.db.scalars(select(Track).where(Track.video_asset_id == asset.id))).all()
    }
    teams = {
        no: (str(getattr(t, "team", "") or ""), getattr(t, "number", None))
        for no, t in meta.items()
    }
    base["tracks"], base["right"] = scene_tracks(rows, teams, start, e.side == "own")
    base["tracks"] = unique_numbers(base["tracks"])
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
