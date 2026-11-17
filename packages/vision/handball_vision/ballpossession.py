"""Who has the ball, from the ball path and the player boxes (BRIEF 7.2 stage 7, player level).

The ball path (`balltrack`) is in frame pixels; a player holds the ball when it is inside the
player's box (widened a little, and raised for a ball held overhead). The court position of a ball
in the air cannot be taken from the floor homography, but the holder's feet can: possession
places the ball on the court.

From the holder per frame:
- **possessions**: one player holding for at least `min_hold_s` (bouncing and short occlusions
  are bridged by `max_gap_s`);
- **passes**: the ball goes from one player to a team-mate within `max_flight_s`;
- **turnovers**: it goes to an opponent (interception, steal, or a lost ball picked up).

Passes and turnovers are only reported between possessions that are both certain; a ball that
disappears for longer is a "lost" end, not a pass.
"""

from __future__ import annotations

import bisect
import itertools
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

Box = tuple[int, float, float, float, float]  # track id, x1, y1, x2, y2 (frame pixels)
# play intervals covering less than this share of the video are not trusted for gating the ball
# (a hall board read 39 times in 10 minutes gave 6 s of play: every ball would be dropped)
MIN_PLAY_SHARE = 0.2


@dataclass(frozen=True)
class Possession:
    track_id: int
    team: str | None
    first: int  # frame
    last: int


@dataclass(frozen=True)
class Transfer:
    kind: str  # "pass" or "turnover"
    from_track: int
    to_track: int
    from_team: str | None
    to_team: str | None
    released: int  # frame the ball left the passer
    received: int  # frame the receiver had it


def holder(ball: tuple[float, float], boxes: Sequence[Box], margin: float = 0.15) -> int | None:
    """The track holding a ball at `ball`: the box containing it (widened by `margin` of its width
    on each side, raised by 20 % of its height for arms overhead). Several boxes: the one whose
    upper-body centre is nearest (the ball is held in hands, not at the feet)."""
    bx, by = ball
    best, best_d = None, float("inf")
    for tid, x1, y1, x2, y2 in boxes:
        w, h = x2 - x1, y2 - y1
        if not (x1 - margin * w <= bx <= x2 + margin * w and y1 - 0.2 * h <= by <= y2):
            continue
        cx, cy = (x1 + x2) / 2, y1 + 0.35 * h
        d = ((bx - cx) / max(w, 1.0)) ** 2 + ((by - cy) / max(h, 1.0)) ** 2
        if d < best_d:
            best, best_d = tid, d
    return best


def holders(
    ball: Mapping[int, tuple[float, float]], boxes: Mapping[int, Sequence[Box]]
) -> dict[int, int | None]:
    """Holder per frame with a ball position and boxes (None: ball free or in flight)."""
    return {f: holder(xy, boxes[f]) for f, xy in sorted(ball.items()) if f in boxes}


def possessions(
    by_frame: Mapping[int, int | None],
    teams: Mapping[int, str],
    fps: float,
    min_hold_s: float = 0.3,
    max_gap_s: float = 0.5,
) -> list[Possession]:
    """Runs of the same holder, short gaps bridged, too short runs dropped."""
    runs: list[list[int]] = []  # [track, first, last]
    gap = round(max_gap_s * fps)
    for f in sorted(by_frame):
        tid = by_frame[f]
        if tid is None:
            continue
        if runs and runs[-1][0] == tid and f - runs[-1][2] <= gap:
            runs[-1][2] = f
        else:
            runs.append([tid, f, f])
    need = min_hold_s * fps
    out = [Possession(t, teams.get(t), a, b) for t, a, b in runs if b - a + 1 >= need]
    # a short foreign run between two of the same holder (a crossing player) disappears above;
    # merge what is now adjacent
    merged: list[Possession] = []
    for p in out:
        if merged and merged[-1].track_id == p.track_id and p.first - merged[-1].last <= 3 * gap:
            merged[-1] = Possession(p.track_id, p.team, merged[-1].first, p.last)
        else:
            merged.append(p)
    return merged


def transfers(pos: Sequence[Possession], fps: float, max_flight_s: float = 2.5) -> list[Transfer]:
    """Passes and turnovers between consecutive possessions of different players."""
    out = []
    for a, b in itertools.pairwise(pos):
        if a.track_id == b.track_id or (b.first - a.last) / fps > max_flight_s:
            continue
        same = a.team is not None and a.team.removesuffix("_gk") == (b.team or "").removesuffix(
            "_gk"
        )
        out.append(
            Transfer(
                "pass" if same else "turnover",
                a.track_id,
                b.track_id,
                a.team,
                b.team,
                a.last,
                b.first,
            )
        )
    return out


def summary(pos: Sequence[Possession], moves: Sequence[Transfer], fps: float) -> dict[str, object]:
    """Ball time per team and player, passes and turnovers per team."""
    team_s: dict[str, float] = {}
    player_s: dict[int, float] = {}
    for p in pos:
        dur = (p.last - p.first + 1) / fps
        if p.team:
            key = p.team.removesuffix("_gk")
            team_s[key] = team_s.get(key, 0.0) + dur
        player_s[p.track_id] = player_s.get(p.track_id, 0.0) + dur
    passes: dict[str, int] = {}
    turnovers: dict[str, int] = {}
    for m in moves:
        key = (m.from_team or "unknown").removesuffix("_gk")
        bucket = passes if m.kind == "pass" else turnovers
        bucket[key] = bucket.get(key, 0) + 1
    return {
        "ball_time_s": {k: round(v, 1) for k, v in team_s.items()},
        "player_ball_time_s": {k: round(v, 1) for k, v in player_s.items()},
        "passes": passes,
        "turnovers": turnovers,
        "possessions": len(pos),
    }


def _apply(h: Any, x: float, y: float) -> tuple[float, float]:
    v = h @ np.array([x, y, 1.0])
    return float(v[0] / v[2]), float(v[1] / v[2])


def from_observations(
    obs: Any,
    result: Any,
    min_score: float = 0.35,
    play: Sequence[tuple[int, int]] | None = None,
    min_conf: float = 0.0,
) -> dict[str, Any] | None:
    """Ball path, holders, possessions and transfers for an analysed video.

    `obs` is a `handball_vision.observe.Observations` (ball boxes per observed frame, camera
    motion), `result` its `AnalysisResult` (tracks keep the index of their box in the frame's
    observation). Ball peaks go to the camera-compensated canvas for the temporal path, and back
    to frame pixels for the holder test. None without ball observations.

    `play`: the stretches (start_ms, end_ms) in which the match clock runs
    (`scoreboard.play_intervals`). Balls outside them are ignored: in breaks, timeouts and before
    and after the game warm-up balls, ball racks and loose balls are not the game ball. None or
    empty (no clock read): every ball counts. `ball_gated_by_clock` says which it was. Intervals
    covering less than `MIN_PLAY_SHARE` of the video are ignored too (`clock_too_sparse`).

    With ball net candidates in the observations (`obs.ball_cands`, `HB_BALL_MODEL`) the path comes
    from tracker v2 (`balltrack2`, frame pixels, points below `min_conf` left out); otherwise from
    the YOLOX "sports ball" boxes and `balltrack` (`min_score`). `ball_model` says which. With the
    ball net the result also carries `path_rows` (`path_rows()`, a numpy array: the caller stores
    it and removes it before the result goes into JSON)."""
    gate = sorted(play) if play else None
    sparse = False
    span_ms = 1000 * obs.total / obs.fps if getattr(obs, "total", 0) and obs.fps else 0.0
    if gate and span_ms and sum(b - a for a, b in gate) < MIN_PLAY_SHARE * span_ms:
        # the clock was read too rarely to tell play from breaks (a hall board mostly out of
        # view): every ball counts, as without a clock
        gate, sparse = None, True
    gated = {
        "ball_gated_by_clock": gate is not None,
        "in_play_s": round(sum(b - a for a, b in gate) / 1000, 1) if gate else None,
        **({"clock_too_sparse": True} if sparse else {}),
    }
    cands: Mapping[int, Sequence[tuple[float, float, float]]] = (
        getattr(obs, "ball_cands", None) or {}
    )
    found = _path_v2(obs, cands, gate, min_conf) if cands else _path_v1(obs, gate, min_score)
    if found is None:
        return None
    path, stats, model, conf = found
    if not path and not stats:  # balls only while the clock stood
        return {
            **gated,
            "ball_model": model,
            "path_stats": {},
            "summary": summary([], [], obs.fps),
            "possessions": [],
            "transfers": [],
        }
    people = {fo.index: fo.people for fo in obs.frames}
    boxes: dict[int, list[Box]] = defaultdict(list)
    for p in result.points:
        if p.det_index is None or p.frame not in people:
            continue
        d = people[p.frame][p.det_index]
        boxes[p.frame].append((p.track_id, d.x1, d.y1, d.x2, d.y2))
    ball = {f: xy for f, xy in path.items() if f in boxes}
    ms = 1000 / obs.fps
    teams = {tid: str(v["label"]) for tid, v in result.teams.items()}
    pos = possessions(holders(ball, boxes), teams, obs.fps)
    moves = transfers(pos, obs.fps)
    rows = {"path_rows": path_rows(path, conf, obs.fps)} if model == "ballnet" else {}
    return {
        **gated,
        **rows,
        "ball_model": model,
        "path_stats": stats,
        "summary": summary(pos, moves, obs.fps),
        "possessions": [
            {
                "track_id": p.track_id,
                "team": p.team,
                "start_ms": round(p.first * ms),
                "end_ms": round(p.last * ms),
            }
            for p in pos
        ],
        "transfers": [
            {
                "kind": m.kind,
                "from": m.from_track,
                "to": m.to_track,
                "released_ms": round(m.released * ms),
                "received_ms": round(m.received * ms),
            }
            for m in moves
        ],
    }


# path (frame -> frame px), path stats, model name, confidence per path frame (ball net only)
PathResult = tuple[dict[int, tuple[float, float]], dict[str, Any], str, dict[int, float]]


def _in_play(gate: list[tuple[int, int]] | None, starts: list[int], t_ms: float) -> bool:
    if gate is None:
        return True
    k = bisect.bisect_right(starts, t_ms) - 1
    return k >= 0 and t_ms <= gate[k][1]


def _path_v1(obs: Any, gate: list[tuple[int, int]] | None, min_score: float) -> PathResult | None:
    """YOLOX ball boxes -> camera-compensated canvas peaks -> `balltrack` -> frame pixels."""
    from handball_vision import balltrack

    motion = obs.motion
    fw = motion.frame_size[0]
    starts = [a for a, _ in gate or []]
    ms = 1000 / obs.fps
    peaks: list[balltrack.Peak] = []
    seen = False
    for fo in obs.frames:
        if not fo.balls:
            continue
        seen = True
        if not _in_play(gate, starts, fo.index * ms):
            continue
        h = motion.frame_to_canvas(fo.index)
        if h is None:
            continue
        for d in fo.balls:
            x, y = _apply(h, (d.x1 + d.x2) / 2, (d.y1 + d.y2) / 2)
            peaks.append(balltrack.Peak(fo.index, x, y, float(d.score)))
    if not seen or (not peaks and gate is None):
        return None
    if not peaks:
        return {}, {}, "yolox", {}
    step = obs.frames[1].index - obs.frames[0].index if len(obs.frames) > 1 else 1
    path, stats = balltrack.track(
        peaks,
        obs.fps,
        max_speed=0.9 * fw,  # about 30 m/s on a broadcast view of the court
        radius=fw / 160,
        min_score=min_score,
        max_gap=3 * step,
    )
    out: dict[int, tuple[float, float]] = {}
    for bpnt in path:
        h = motion.canvas_to_frame(bpnt.frame)
        if h is not None:
            out[bpnt.frame] = _apply(h, bpnt.x, bpnt.y)
    return out, dict(stats), "yolox", {}


def ball_path_v2(
    obs: Any,
    cands: Mapping[int, Sequence[tuple[float, float, float]]],
    gate: list[tuple[int, int]] | None = None,
) -> tuple[int, list[tuple[float, float] | None], list[float]]:
    """Tracker v2 over the ball net candidates: (first frame, point per frame from there, confidence
    per frame), frame pixels. Frames outside play have no candidates.

    The net may have run on every `step`-th frame only (`HB_BALL_EVERY`): the tracker then runs on
    that thinned sequence at fps / step, and the frames in between are filled linearly between
    neighbouring points of a segment (gold v1: hrp1 on every 3rd frame 65.3 % instead of 76.1 %,
    ml/integration; the frames between without a point stay None)."""
    from handball_vision import balltrack2

    frames = sorted(cands)
    first, last = frames[0], frames[-1]
    step = _net_step(frames)
    starts = [a for a, _ in gate or []]
    ms = 1000 / obs.fps
    peaks = [
        list(cands.get(f, ())) if _in_play(gate, starts, f * ms) else []
        for f in range(first, last + 1, step)
    ]
    thin, thin_conf = balltrack2.track_windows(
        peaks, obs.fps / step, float(obs.motion.frame_size[0])
    )
    if step == 1:
        return first, thin, thin_conf
    n = last - first + 1
    out: list[tuple[float, float] | None] = [None] * n
    conf = [0.0] * n
    for i, (q, c) in enumerate(zip(thin, thin_conf, strict=True)):
        out[i * step], conf[i * step] = q, c
    for i in range(len(thin) - 1):
        a, b = thin[i], thin[i + 1]
        if a is None or b is None:
            continue
        low = min(thin_conf[i], thin_conf[i + 1])
        for j in range(1, step):
            u = j / step
            out[i * step + j] = (a[0] + u * (b[0] - a[0]), a[1] + u * (b[1] - a[1]))
            conf[i * step + j] = low
    return first, out, conf


def _net_step(frames: Sequence[int]) -> int:
    """The spacing of the frames the net ran on (the most common gap; 1 for every frame)."""
    gaps: dict[int, int] = defaultdict(int)
    for a, b in itertools.pairwise(frames):
        if b > a:
            gaps[b - a] += 1
    return max(gaps, key=lambda g: gaps[g]) if gaps else 1


def _path_v2(
    obs: Any,
    cands: Mapping[int, Sequence[tuple[float, float, float]]],
    gate: list[tuple[int, int]] | None,
    min_conf: float,
) -> PathResult:
    first, out, conf = ball_path_v2(obs, cands, gate)
    path: dict[int, tuple[float, float]] = {}
    sure: dict[int, float] = {}
    for k, (q, c) in enumerate(zip(out, conf, strict=True)):
        if q is not None and c >= min_conf:
            path[first + k], sure[first + k] = q, c
    stats = {"frames": len(out), "points": len(path)}
    if not path and gate is not None:
        return {}, {}, "ballnet", {}
    return path, stats, "ballnet", sure


def path_rows(
    path: Mapping[int, tuple[float, float]], conf: Mapping[int, float], fps: float
) -> Any:
    """The ball path for storage (`analysis/ball.bin`): float32 rows t_ms, x, y (frame pixels of
    the analysis proxy), confidence, one per frame with a point."""
    rows = [(f * 1000 / fps, path[f][0], path[f][1], conf.get(f, 0.0)) for f in sorted(path)]
    return np.array(rows, np.float32).reshape(-1, 4)
