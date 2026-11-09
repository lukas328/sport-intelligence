"""Ball path over time from per-frame ball peaks (BRIEF 7.2 stage 5).

A single frame cannot tell a ball from a lamp, a shoe or a ball-sized spot on the wall; a few
frames in a row can. The ball is one object and cannot jump: between two frames it moves at most
`max_speed` (about 30 m/s for a hard shot). So:

1. **Tracklets:** peaks in consecutive frames are linked when the step is physically possible
   (gate around the constant-velocity prediction). Short gaps (missed frames) are bridged.
2. **Static spots:** a place (in camera-compensated canvas pixels, so a panning camera does not
   matter) where peaks show up in a large share of the seconds is part of the hall, not the ball.
   A tracklet that does not move over seconds is dropped as well.
3. **Best chain:** at most one tracklet at a time; consecutive tracklets must be reachable in the
   gap between them (after a long gap anything is). The chain with the largest evidence wins
   (weighted interval scheduling, `O(n log n)`).

Peak evidence is `logit(score) - logit(min_score)`: peaks above `min_score` count for, below
against. Coordinates are whatever the caller passes (canvas pixels for a moving camera, court
metres when calibrated); `max_speed` and the radii are in the same unit per second.
"""

from __future__ import annotations

import bisect
import itertools
import math
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Peak:
    frame: int
    x: float
    y: float
    score: float


@dataclass
class Tracklet:
    peaks: list[Peak] = field(default_factory=list)
    vx: float = 0.0
    vy: float = 0.0
    value: float = 0.0

    @property
    def first(self) -> int:
        return self.peaks[0].frame

    @property
    def last(self) -> int:
        return self.peaks[-1].frame


@dataclass(frozen=True)
class BallPoint:
    frame: int
    x: float
    y: float
    score: float  # 0 for interpolated points
    tracklet: int


def _logit(p: float) -> float:
    p = min(max(p, 1e-4), 1 - 1e-4)
    return math.log(p / (1 - p))


def static_cells(
    peaks: list[Peak], fps: float, cell: float, min_share: float = 0.15, min_seconds: int = 8
) -> set[tuple[int, int]]:
    """Grid cells (size `cell`) holding peaks in at least `min_share` of the seconds with peaks
    (and at least `min_seconds` of them): fixed things in the hall."""
    seconds: dict[tuple[int, int], set[int]] = defaultdict(set)
    all_seconds: set[int] = set()
    for p in peaks:
        s = int(p.frame / fps)
        all_seconds.add(s)
        seconds[(int(p.x // cell), int(p.y // cell))].add(s)
    if not all_seconds:
        return set()
    need = max(min_seconds, min_share * len(all_seconds))
    # a spot on a cell border spreads over two cells: count the 2x2 neighbourhood
    out = set()
    for c in seconds:
        near: set[int] = set()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                near |= seconds.get((c[0] + dx, c[1] + dy), set())
        if len(seconds[c]) >= need / 2 and len(near) >= need:
            out.add(c)
    return out


def link(
    peaks: list[Peak],
    fps: float,
    max_speed: float,
    radius: float,
    max_gap: int = 3,
) -> list[Tracklet]:
    """Tracklets from peaks: each peak joins the open tracklet whose constant-velocity prediction
    is nearest (within `radius` + half the maximal step, and a step no longer than `max_speed`
    allows), stronger peaks first; a tracklet closes after `max_gap` frames without a peak."""
    by_frame: dict[int, list[Peak]] = defaultdict(list)
    for p in peaks:
        by_frame[p.frame].append(p)
    done: list[Tracklet] = []
    open_: list[Tracklet] = []
    for f in sorted(by_frame):
        still: list[Tracklet] = []
        for t in open_:
            (done if f - t.last > max_gap else still).append(t)
        open_ = still
        taken: set[int] = set()
        for p in sorted(by_frame[f], key=lambda q: -q.score):
            best, best_d = None, math.inf
            for k, t in enumerate(open_):
                if k in taken:
                    continue
                last = t.peaks[-1]
                dt = (f - last.frame) / fps
                step = math.hypot(p.x - last.x, p.y - last.y)
                if step > radius + max_speed * dt:
                    continue
                d = math.hypot(p.x - (last.x + t.vx * dt), p.y - (last.y + t.vy * dt))
                if d <= radius + 0.5 * max_speed * dt and d < best_d:
                    best, best_d = k, d
            if best is None:
                open_.append(Tracklet([p]))
                taken.add(len(open_) - 1)
                continue
            t = open_[best]
            last = t.peaks[-1]
            dt = (f - last.frame) / fps
            vx, vy = (p.x - last.x) / dt, (p.y - last.y) / dt
            a = 0.5 if len(t.peaks) > 1 else 1.0  # smoothed velocity
            t.vx, t.vy = (1 - a) * t.vx + a * vx, (1 - a) * t.vy + a * vy
            t.peaks.append(p)
            taken.add(best)
    return done + open_


def track(
    peaks: list[Peak],
    fps: float,
    max_speed: float,
    radius: float,
    min_score: float = 0.3,
    max_gap: int = 3,
    min_length: int = 3,
    static_cell: float | None = None,
    static_after_s: float = 1.5,
    free_after_s: float = 2.0,
) -> tuple[list[BallPoint], dict[str, int]]:
    """The ball path: chosen tracklets' peaks plus linear interpolation over their short gaps."""
    cell = static_cell if static_cell is not None else 2 * radius
    static = static_cells(peaks, fps, cell)
    kept = [p for p in peaks if (int(p.x // cell), int(p.y // cell)) not in static]
    tracklets = link(kept, fps, max_speed, radius, max_gap)
    bias = _logit(min_score)
    good: list[Tracklet] = []
    n_static = n_short = 0
    for t in tracklets:
        if len(t.peaks) < min_length:
            n_short += 1
            continue
        if (t.last - t.first) / fps >= static_after_s:
            xs = sorted(p.x for p in t.peaks)
            ys = sorted(p.y for p in t.peaks)
            spread = max(xs[-1] - xs[0], ys[-1] - ys[0])
            if spread < radius:
                n_static += 1
                continue
        t.value = sum(_logit(p.score) - bias for p in t.peaks)
        if t.value > 0:
            good.append(t)
    good.sort(key=lambda t: t.last)
    ends = [t.last for t in good]
    best = [0.0] * len(good)
    prev: list[int | None] = [None] * len(good)
    prefix: list[tuple[float, int | None]] = []  # running max of best[] by end frame
    free_gap = int(free_after_s * fps)
    for j, t in enumerate(good):
        candidate, came = 0.0, None
        # anything that ended long enough before is reachable: running maximum
        k = bisect.bisect_left(ends, t.first - free_gap) - 1
        if k >= 0 and prefix[k][0] > candidate:
            candidate, came = prefix[k]
        # recent ones must be reachable at ball speed
        i = bisect.bisect_left(ends, t.first) - 1
        while i > k:
            a = good[i]
            gap_s = (t.first - a.last) / fps
            pa, pb = a.peaks[-1], t.peaks[0]
            reach = math.hypot(pb.x - pa.x, pb.y - pa.y) <= radius + max_speed * gap_s
            if reach and best[i] > candidate:
                candidate, came = best[i], i
            i -= 1
        best[j] = t.value + candidate
        prev[j] = came
        top = prefix[-1] if prefix else (0.0, None)
        prefix.append((best[j], j) if best[j] > top[0] else top)
    chain: list[int] = []
    at: int | None = max(range(len(good)), key=lambda q: best[q]) if good else None
    while at is not None:
        chain.append(at)
        at = prev[at]
    out: list[BallPoint] = []
    for n, j in enumerate(reversed(chain)):
        ps = good[j].peaks
        for p0, p1 in itertools.pairwise(ps):
            out.append(BallPoint(p0.frame, p0.x, p0.y, p0.score, n))
            for f in range(p0.frame + 1, p1.frame):
                w = (f - p0.frame) / (p1.frame - p0.frame)
                out.append(BallPoint(f, p0.x + w * (p1.x - p0.x), p0.y + w * (p1.y - p0.y), 0.0, n))
        out.append(BallPoint(ps[-1].frame, ps[-1].x, ps[-1].y, ps[-1].score, n))
    stats = {
        "peaks": len(peaks),
        "static_cells": len(static),
        "tracklets": len(tracklets),
        "short": n_short,
        "static_tracklets": n_static,
        "chosen": len(chain),
        "frames_with_ball": sum(1 for p in out if p.score > 0),
    }
    return out, stats
