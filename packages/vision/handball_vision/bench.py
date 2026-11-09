"""People outside play: substitutes on the bench, coaches, officials at the table (ADR 028 addendum).

A learned detector sees everyone near the court; `detection.filter_on_court` keeps feet within
1.5 m of the lines, which still includes the bench row along a sideline (seated people's feet are
about a metre beyond the line) and spectators sitting right at the court edge. They pollute team
colours, number votes, possession and the physical metrics.

The rule works on court positions (calibration) and on stretches of a track, not whole tracks:
the tracker often hands a bench person's track to a player who passes the bench, or the other way
round (a substitute walks onto the court).

1. **Off court**: the median foot point over a window of `window_s` lies beyond a *sideline* by
   a margin. The margin grows with the distance from the camera: at least `margin_m`, or
   `margin_px` image pixels across the line at that spot (on the far side a few pixels of
   calibration error are most of a metre, and wings stand on that line). Points beyond the goal
   lines never count: goalkeepers and the goal-line referee stand there.
2. **Still**: in that window the track stays within `still_m` of its median (90th percentile).
   Referees and players along a sideline keep moving.
3. **Bench stretch**: a run of such points lasting at least `min_run_s` (gaps in the
   observations do not break it while the person stays at the same spot). It takes in the
   neighbouring looks within `still_m` of its median (standing up moves the foot point just
   inside the margin).

The bench stretches are cut out of the track. The pieces in between become tracks of their own
(the person before and after a bench stretch is often not the same), unless they are leftovers
of the bench: fewer than `min_piece_points` looks, or a median off court without moving like a
referee. A track with nothing left is bench as a whole.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, replace
from typing import Any

import numpy as np
from numpy.typing import NDArray

from handball_vision.calibration import Calibration
from handball_vision.tracking import TrackPoint

F64 = NDArray[np.float64]
COURT_L, COURT_W = 40.0, 20.0


@dataclass(frozen=True)
class BenchRule:
    margin_m: float = 0.15
    margin_px: float = 25.0
    window_s: float = 8.0
    still_m: float = 2.0
    min_run_s: float = 6.0
    max_gap_s: float = 2.0
    min_piece_points: int = 5


@dataclass(frozen=True)
class BenchStretch:
    """A bench stretch: `track_id` is the (stitched) track it was cut from."""

    track_id: int
    first_frame: int
    last_frame: int
    x: float
    y: float
    whole_track: bool

    def to_dict(self, fps: float) -> dict[str, Any]:
        return {
            "track_id": self.track_id,
            "first_ms": round(self.first_frame * 1000 / fps),
            "last_ms": round(self.last_frame * 1000 / fps),
            "x": round(self.x, 1),
            "y": round(self.y, 1),
            "whole_track": self.whole_track,
        }


@dataclass
class BenchSplit:
    points: list[TrackPoint]
    stretches: list[BenchStretch]
    removed: set[int]  # tracks that were bench as a whole
    pieces: dict[int, tuple[int, int, int]]  # new track -> (old track, first frame, last frame)
    cut: dict[int, list[tuple[int, int]]]  # old track -> bench frame ranges cut out of it

    def owner(self, track_id: int, frame: int) -> int | None:
        """The track a look (colour, number, role) of `track_id` at `frame` now belongs to;
        None when it fell on a bench stretch."""
        if track_id in self.removed:
            return None
        for a, b in self.cut.get(track_id, []):
            if a <= frame <= b:
                return None
        for new, (_, a, b) in self._pieces_of(track_id):
            if a <= frame <= b:
                return new
        return track_id

    def _pieces_of(self, track_id: int) -> list[tuple[int, tuple[int, int, int]]]:
        return [(n, v) for n, v in self.pieces.items() if v[0] == track_id]


DEFAULT_RULE = BenchRule()


def sideline_margins(
    calib: Calibration | None, xs: F64, rule: BenchRule = DEFAULT_RULE
) -> tuple[F64, F64]:
    """Margins (metres) beyond the near (y = 0) and far (y = 20) sideline at court positions `xs`:
    `margin_px` across the line converted to metres there, at least `margin_m`."""
    floor = np.full(len(xs), rule.margin_m)
    if calib is None or rule.margin_px <= 0:
        return floor, floor.copy()
    out = []
    for y in (0.0, COURT_W):
        xc = np.clip(xs, 0.0, COURT_L)
        a = calib.to_image(np.column_stack([xc, np.full(len(xs), y - 0.5)]))
        b = calib.to_image(np.column_stack([xc, np.full(len(xs), y + 0.5)]))
        with np.errstate(all="ignore"):
            px_per_m = np.linalg.norm(b - a, axis=1)
            m = np.where(np.isfinite(px_per_m) & (px_per_m > 0), rule.margin_px / px_per_m, 0.0)
        out.append(np.maximum(floor, m))
    return out[0], out[1]


def bench_frames(
    frames: NDArray[np.int64],
    xy: F64,
    fps: float,
    margins: tuple[F64, F64],
    rule: BenchRule = DEFAULT_RULE,
) -> list[tuple[int, int]]:
    """Bench stretches (first, last frame) of one track from its observed foot points (sorted by
    frame). `margins` are the near and far sideline margins per point (`sideline_margins`)."""
    n = len(frames)
    if n == 0:
        return []
    near, far = margins
    t = frames.astype(np.float64) / fps
    half = rule.window_s / 2
    lo = np.searchsorted(t, t - half, side="left")
    hi = np.searchsorted(t, t + half, side="right")
    bench = np.zeros(n, bool)
    for i in range(n):
        w = xy[lo[i] : hi[i]]
        med = np.median(w, axis=0)
        if -near[i] <= med[1] <= COURT_W + far[i]:
            continue
        spread = np.linalg.norm(w - med, axis=1)
        bench[i] = float(np.percentile(spread, 90)) <= rule.still_m
    # runs of consecutive bench points; a gap in the observations (camera elsewhere, occlusion)
    # does not break a run when the person is still at the same spot afterwards
    runs: list[tuple[int, int]] = []
    start: int | None = None
    for i in range(n + 1):
        joins = (
            i < n
            and bench[i]
            and start is not None
            and (
                t[i] - t[i - 1] <= rule.max_gap_s
                or float(np.linalg.norm(xy[i] - xy[i - 1])) <= rule.still_m
            )
        )
        if joins:
            continue
        if start is not None and t[i - 1] - t[start] >= rule.min_run_s:
            runs.append((start, i - 1))
        start = i if i < n and bench[i] else None
    # a run takes in the neighbouring looks at the same spot (standing up moves the foot point
    # just inside the margin; the person is the same)
    grown: list[tuple[int, int]] = []
    for a, b in runs:
        med = np.median(xy[a : b + 1], axis=0)
        while a > 0 and float(np.linalg.norm(xy[a - 1] - med)) <= rule.still_m:
            a -= 1
        while b < n - 1 and float(np.linalg.norm(xy[b + 1] - med)) <= rule.still_m:
            b += 1
        if grown and a <= grown[-1][1] + 1:
            grown[-1] = (grown[-1][0], b)
        else:
            grown.append((a, b))
    return [(int(frames[a]), int(frames[b])) for a, b in grown]


def split_bench(
    points: Iterable[TrackPoint],
    fps: float,
    calib: Calibration | None,
    rule: BenchRule = DEFAULT_RULE,
) -> BenchSplit:
    """Take the bench stretches out of the tracks (see the module docstring)."""
    by: dict[int, list[TrackPoint]] = defaultdict(list)
    for p in points:
        by[p.track_id].append(p)
    next_id = max(by, default=0) + 1
    kept: list[TrackPoint] = []
    stretches: list[BenchStretch] = []
    removed: set[int] = set()
    pieces: dict[int, tuple[int, int, int]] = {}
    cut: dict[int, list[tuple[int, int]]] = {}
    for tid in sorted(by):
        ps = sorted(by[tid], key=lambda p: p.frame)
        seen = [p for p in ps if p.observed]
        if not seen:
            kept += ps
            continue
        frames = np.array([p.frame for p in seen], np.int64)
        xy = np.array([(p.x, p.y) for p in seen], np.float64)
        runs = bench_frames(frames, xy, fps, sideline_margins(calib, xy[:, 0], rule), rule)
        if not runs:
            kept += ps
            continue

        def inside(f: int, runs: list[tuple[int, int]] = runs) -> bool:
            return any(a <= f <= b for a, b in runs)

        # pieces between the bench stretches; short leftovers beside the bench go with it
        groups: list[list[TrackPoint]] = []
        for p in ps:
            if inside(p.frame):
                continue
            if groups and not any(groups[-1][-1].frame < a <= p.frame for a, _ in runs):
                groups[-1].append(p)
            else:
                groups.append([p])
        groups = [g for g in groups if _piece_survives(g, calib, rule)]
        if not groups:
            removed.add(tid)
            stretches.append(_stretch(tid, ps[0].frame, ps[-1].frame, xy, True))
            continue
        cut[tid] = list(runs)
        for a, b in runs:
            sel = (frames >= a) & (frames <= b)
            stretches.append(_stretch(tid, a, b, xy[sel], False))
        kept_frames = {p.frame for g in groups for p in g}
        dropped = [p.frame for p in ps if not inside(p.frame) and p.frame not in kept_frames]
        if dropped:
            cut[tid] += _ranges(dropped, ps)
        kept += groups[0]  # the first piece keeps the track id
        for g in groups[1:]:
            pieces[next_id] = (tid, g[0].frame, g[-1].frame)
            kept += [replace(p, track_id=next_id) for p in g]
            next_id += 1
    kept.sort(key=lambda p: (p.frame, p.track_id))
    return BenchSplit(kept, stretches, removed, pieces, cut)


def _piece_survives(g: list[TrackPoint], calib: Calibration | None, rule: BenchRule) -> bool:
    """A piece of a track cut by bench stretches stays a track of its own unless it is a leftover
    of the bench: too few looks, or its median off court and not moving like a referee."""
    seen = [p for p in g if p.observed]
    if len(seen) < rule.min_piece_points:
        return False
    xy = np.array([(p.x, p.y) for p in seen], np.float64)
    med = np.median(xy, axis=0)
    near, far = sideline_margins(calib, med[:1], rule)
    if float(np.linalg.norm(xy.std(axis=0))) >= 1.5 * rule.still_m:
        return True  # moves like a player or a referee
    return bool(-near[0] <= med[1] <= COURT_W + far[0])


def _ranges(frames: list[int], ps: list[TrackPoint]) -> list[tuple[int, int]]:
    """Frame ranges covering `frames`, split where a point of `ps` outside them lies between."""
    want = set(frames)
    out: list[tuple[int, int]] = []
    open_run = False
    for p in ps:
        if p.frame not in want:
            open_run = False
        elif open_run:
            out[-1] = (out[-1][0], p.frame)
        else:
            out.append((p.frame, p.frame))
            open_run = True
    return out


def _stretch(tid: int, a: int, b: int, xy: F64, whole: bool) -> BenchStretch:
    med = np.median(xy, axis=0) if len(xy) else np.zeros(2)
    return BenchStretch(tid, a, b, float(med[0]), float(med[1]), whole)
