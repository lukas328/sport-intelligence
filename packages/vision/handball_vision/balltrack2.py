"""Ball tracker v2: one ball path from the 3-frame ball net's candidates (ADR 025 follow-up,
docs/plans/produkt-analyse-integration.md step 2).

Product port of the research tracker `ml/gold/tracker.py` with its learned candidate rescoring
(`ml/gold/tracker_rescore.py`, weights learned without OWLv2: the product cannot run OWLv2). Gold v1
(42 clips, 12 px, nets hr1 + hrp1): 80.0 % of all balls [74.7, 84.9], 83.3 % of the fast ones
[75.2, 90.1] (`ml/ball/LINEAGE.md` section 5). The research file stays the reference;
`tests/test_balltrack2.py` and `ml/integration/parity_tracker.py` check that both give the same path.

Every frame has a few candidates (net peaks, frame pixels). The path is the cheapest chain through
them (dynamic programming over frames):
- a chosen candidate earns `rescore` times its ball probability (logistic regression on net score,
  top-1 of its frame, static spot, moving support, slow persistence);
- a frame without a point costs `miss`; a new segment costs `start`;
- a step costs the squared distance to the position predicted from the previous step's velocity,
  scaled by a tolerance that grows with the speed; steps faster than `vmax` are impossible;
- a predecessor may lie up to `gap` frames back, a fast one (speed at least `v_fast`) up to
  `gap_fast` frames;
- repeated frames (25 fps stored as 50 or 30): a candidate within `dup_px` of its moving
  predecessor one frame back keeps the predecessor's velocity, at most `dup_max` times in a row;
- spots that hold a candidate in most frames of the window (lamps, a spare ball) are static; note
  that the no-OWLv2 rescoring gives this flag weight 0 (as in research), so a still spot loses
  only through missing motion support and its slow persistence.
- with the candidates' positions on the camera's canvas (`world`, an operated camera), a spot that
  holds a candidate in more than `world_static_frac` of the window's frames there (within
  `world_static_px`) earns only `world_static_keep` of its reward: objects at the bench (spare
  balls, bottles) move through the picture with the camera but stand still on the canvas. Dev shot
  clips (41, product CPU setting, the owner's 546 judged tracker points): points on a known wrong
  object 89 -> 74, of them at the bench 22 -> 9; points on a known ball 111 -> 115
  (`ml/integration/ball_world_static.py`; values chosen there among five, so a little optimistic).
Gaps inside a segment are filled linearly.

Confidence ("don't know"): each output point gets the geometric mean of its ball probability (for a
filled frame the lower of its two ends) and the mean probability of its segment.

The research tracker ran on 8 s clips; `track_windows` runs it on overlapping windows of that length
over a whole video and keeps each window's centre, so the static-spot rule and the costs see the
same span as on gold.

LICENCE NOTE (test phase): the candidates come from nets trained with DeepSport data
(non-commercial); see `handball_vision.ballnet`.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

# learned without OWLv2 on the training clips (ml/gold/data/tracker_rescore_noowl.json:
# 27 627 candidates, 4 703 on a ball); order: bias, net, top1, owl, both, static, move, slow
RESCORE_W = (-3.8596, 3.4757, 1.6149, 0.0, 0.0, 0.0, 2.4326, -1.6922)

Point = tuple[float, float]


@dataclass(frozen=True)
class Params:
    # chosen by random search with 2-fold cross-validation over the gold clips (research)
    miss: float = 0.35
    start: float = 3.0
    w_net: float = 2.0
    net_min: float = 0.1
    sigma0: float = 6.0  # px of tolerance at rest (per frame, 1280 px wide picture)
    sigma_v: float = 0.6  # extra tolerance per px/frame of speed
    sigma_new: float = 30.0  # tolerance of the first step of a segment (no velocity yet)
    vmax: float = 70.0  # px per frame at 30 fps, 1280 px wide
    gap: int = 2
    static_frac: float = 0.5
    static_px: float = 5.0
    static_keep: float = 0.6
    fill: bool = True
    dup_px: float = 5.0
    dup_max: int = 1
    gap_fast: int = 4
    v_fast: float = 8.0
    rescore: float = 3.0  # reward = rescore * ball probability (0 = hand-set reward w_net * score)
    # still on the camera's canvas (only with `world`): cell size per 1280 px, share of the window
    # the cell must hold a candidate in, share of the reward such a spot keeps
    world_static_px: float = 11.0
    world_static_frac: float = 0.3
    world_static_keep: float = 0.0


@dataclass
class Cand:
    x: float
    y: float
    net: float
    r: float = 0.0
    static: bool = False
    world_static: bool = False


def merge_candidates(
    lists: Sequence[Sequence[tuple[float, float, float]]], radius: float = 8.0, top: int = 5
) -> list[tuple[float, float, float]]:
    """Ensemble of several nets' peaks for one frame: peaks within `radius` px merge (position of
    the first, scores summed), the score is divided by the number of nets, best `top` kept."""
    merged: list[list[float]] = []
    for lst in lists:
        for x, y, s in lst:
            for o in merged:
                if math.hypot(o[0] - x, o[1] - y) <= radius:
                    o[2] += s
                    break
            else:
                merged.append([x, y, s])
    n = max(1, len(lists))
    out = sorted(((x, y, s / n) for x, y, s in merged), key=lambda v: -v[2])
    return out[:top]


def candidates(
    peaks: Sequence[Sequence[tuple[float, float, float]]], p: Params
) -> list[list[Cand]]:
    frames = [[Cand(x, y, net=s) for x, y, s in row if s >= p.net_min] for row in peaks]
    cell = p.static_px
    holds: dict[tuple[int, int], set[int]] = {}
    for k, cs in enumerate(frames):
        for q in cs:
            gx, gy = int(q.x // cell), int(q.y // cell)
            if q.net:
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        holds.setdefault((gx + dx, gy + dy), set()).add(k)
    ran = max(1, len(frames))
    for cs in frames:
        for q in cs:
            g = (int(q.x // cell), int(q.y // cell))
            q.static = len(holds.get(g, ())) > p.static_frac * ran
            q.r = (p.static_keep if q.static else 1.0) * p.w_net * q.net
    return frames


def mark_world_static(
    frames: list[list[Cand]],
    world: Sequence[Sequence[Point | None]],
    peaks: Sequence[Sequence[tuple[float, float, float]]],
    width: float,
    p: Params,
) -> None:
    """Flag candidates whose canvas position (`world[k][i]` for `peaks[k][i]`, None where the camera
    is unknown) is held by a candidate in more than `world_static_frac` of the frames."""
    cell = p.world_static_px * width / 1280
    pos = [
        [w for w, (_x, _y, s) in zip(wr, row, strict=True) if s >= p.net_min]
        for wr, row in zip(world, peaks, strict=True)
    ]
    holds: dict[tuple[int, int], set[int]] = {}
    for k, ws in enumerate(pos):
        for w in ws:
            if w is None:
                continue
            gx, gy = int(w[0] // cell), int(w[1] // cell)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    holds.setdefault((gx + dx, gy + dy), set()).add(k)
    ran = max(1, len(frames))
    for cs, ws in zip(frames, pos, strict=True):
        for q, w in zip(cs, ws, strict=True):
            g = (int(w[0] // cell), int(w[1] // cell)) if w is not None else None
            q.world_static = g is not None and len(holds.get(g, ())) > p.world_static_frac * ran


def features(frames: list[list[Cand]], scale: float) -> list[list[list[float]]]:
    """Rescoring features per candidate (research `tracker_rescore.features`, OWLv2 columns 0)."""
    out = []
    n = len(frames)
    vmin = 3.0 * scale
    for k, cs in enumerate(frames):
        top = max((q.net for q in cs), default=0.0)
        row = []
        for q in cs:
            move = 0.0
            for d in (1, 2):
                if k - d < 0 or k + d >= n:
                    continue
                for a in frames[k - d]:
                    for b in frames[k + d]:
                        mx, my = (a.x + b.x) / 2, (a.y + b.y) / 2
                        if (
                            math.hypot(mx - q.x, my - q.y) <= 6 * scale
                            and math.hypot(b.x - a.x, b.y - a.y) >= 2 * d * vmin
                        ):
                            move = max(move, min(1.0, a.net * b.net))
            slow = 0
            for d in range(-10, 11):
                if d == 0 or not 0 <= k + d < n:
                    continue
                if any(
                    math.hypot(a.x - q.x, a.y - q.y) <= 2 * scale * abs(d) + 4
                    for a in frames[k + d]
                ):
                    slow += 1
            row.append(
                [
                    1.0,
                    q.net,
                    float(q.net > 0 and q.net >= top),
                    0.0,
                    0.0,
                    float(q.static),
                    move,
                    slow / 20,
                ]
            )
        out.append(row)
    return out


def _rescore(frames: list[list[Cand]], scale: float, p: Params) -> None:
    for cs, fs in zip(frames, features(frames, scale), strict=True):
        for q, f in zip(cs, fs, strict=True):
            z = sum(a * b for a, b in zip(RESCORE_W, f, strict=True))
            q.r = p.rescore / (1 + math.exp(-z))


def track(
    peaks: Sequence[Sequence[tuple[float, float, float]]],
    fps: float,
    width: float = 1280.0,
    p: Params | None = None,
    world: Sequence[Sequence[Point | None]] | None = None,
) -> tuple[list[Point | None], list[float]]:
    """Per frame (x, y) or None, and a confidence in 0..1 per frame (0 where None).

    `peaks[k]`: the candidates (x, y, score) of frame k in frame pixels of a `width` px wide
    picture; consecutive entries are consecutive frames at `fps`. `world[k][i]`: optional canvas
    position of `peaks[k][i]` (same scale as the frame), for spots that stand still there."""
    p = p or Params()
    frames = candidates(peaks, p)
    n = len(frames)
    scale = width / 1280 * 30 / fps  # px per frame at this video
    if p.rescore > 0:
        _rescore(frames, scale, p)
    if world is not None:
        mark_world_static(frames, world, peaks, width, p)
        for cs in frames:
            for q in cs:
                if q.world_static:
                    q.r *= p.world_static_keep
    norm = p.rescore if p.rescore > 0 else p.w_net
    vmax = p.vmax * scale
    dup = p.dup_px * width / 1280
    inf = float("inf")
    # best[k][j] = (cost, back, vx, vy, reps); back = (k', i) or (-1, k-1) for a segment start
    best: list[list[tuple[float, tuple[int, int], float, float, int]]] = []
    big_f = [0.0] * n  # cheapest solution of frames 0..k (frame k may be empty)
    big_fb: list[tuple[int, int] | None] = [None] * n
    for k in range(n):
        row = []
        prev_f = big_f[k - 1] if k else 0.0
        for q in frames[k]:
            cost = prev_f + p.start - q.r
            back: tuple[int, int] = (-1, k - 1)
            vel = (0.0, 0.0)
            reps = 0
            for kp in range(max(0, k - max(p.gap, p.gap_fast)), k):
                dt = k - kp
                skip = p.miss * (dt - 1)
                for i, (c0, b0, vx, vy, rp) in enumerate(best[kp]):
                    if c0 == inf:
                        continue
                    new_seg = b0[0] == -1
                    if dt > p.gap and (new_seg or math.hypot(vx, vy) < p.v_fast * scale):
                        continue
                    a = frames[kp][i]
                    dx, dy = q.x - a.x, q.y - a.y
                    if math.hypot(dx, dy) > vmax * dt:
                        continue
                    if (
                        dt == 1
                        and rp < p.dup_max
                        and not new_seg
                        and math.hypot(dx, dy) <= dup
                        and math.hypot(vx, vy) > dup
                    ):
                        s = p.sigma0 * scale
                        tot = c0 + (dx * dx + dy * dy) / (2 * s * s) - q.r
                        if tot < cost:
                            cost, back, vel, reps = tot, (kp, i), (vx, vy), rp + 1
                        continue
                    if new_seg:
                        s = p.sigma_new * scale * dt
                        m = (dx * dx + dy * dy) / (2 * s * s)
                    else:
                        ex, ey = dx - vx * dt, dy - vy * dt
                        s = (p.sigma0 * scale + p.sigma_v * math.hypot(vx, vy)) * dt
                        m = (ex * ex + ey * ey) / (2 * s * s)
                    tot = c0 + skip + m - q.r
                    if tot < cost:
                        cost, back, vel, reps = tot, (kp, i), (dx / dt, dy / dt), 0
            row.append((cost, back, vel[0], vel[1], reps))
        best.append(row)
        big_f[k] = prev_f + p.miss
        big_fb[k] = None
        for j, (c0, *_rest) in enumerate(row):
            if c0 < big_f[k]:
                big_f[k], big_fb[k] = c0, (k, j)
    out: list[Point | None] = [None] * n
    pt = [0.0] * n
    conf = [0.0] * n
    k = n - 1
    while k >= 0:
        fb = big_fb[k]
        if fb is None:
            k -= 1
            continue
        kk, j = fb
        seg = []
        while True:
            q = frames[kk][j]
            prob = min(1.0, max(0.0, q.r / norm))
            out[kk], pt[kk] = (q.x, q.y), prob
            seg.append(kk)
            back = best[kk][j][1]
            if back[0] == -1:
                k = back[1]
                break
            kp, i = back
            if p.fill and kk - kp > 1:
                a = frames[kp][i]
                pa = min(1.0, max(0.0, a.r / norm))
                for t in range(kp + 1, kk):
                    u = (t - kp) / (kk - kp)
                    out[t] = (a.x + u * (q.x - a.x), a.y + u * (q.y - a.y))
                    pt[t] = min(prob, pa)
                    seg.append(t)
            kk, j = kp, i
        mean = sum(pt[t] for t in seg) / len(seg)
        for t in seg:
            conf[t] = math.sqrt(pt[t] * mean)
    return out, conf


def track_windows(
    peaks: Sequence[Sequence[tuple[float, float, float]]],
    fps: float,
    width: float = 1280.0,
    window_s: float = 8.0,
    overlap_s: float = 2.0,
    p: Params | None = None,
    world: Sequence[Sequence[Point | None]] | None = None,
) -> tuple[list[Point | None], list[float]]:
    """`track` over overlapping windows of `window_s` (the gold clip length); each frame takes the
    result of the window whose centre is nearest."""
    n = len(peaks)
    win = max(1, round(window_s * fps))
    if n <= win:
        return track(peaks, fps, width, p, world)
    hop = max(1, win - round(overlap_s * fps))
    out: list[Point | None] = [None] * n
    conf = [0.0] * n
    near = [math.inf] * n  # distance of the frame to the centre of its chosen window
    for s in [*range(0, n - win, hop), n - win]:
        o, c = track(
            peaks[s : s + win], fps, width, p, None if world is None else world[s : s + win]
        )
        centre = (win - 1) / 2
        for t in range(win):
            d = abs(t - centre)
            if d < near[s + t]:
                near[s + t] = d
                out[s + t], conf[s + t] = o[t], c[t]
    return out, conf
