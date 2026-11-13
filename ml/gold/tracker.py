"""Ball tracker v2: one ball path per clip from the detectors' candidates (research, ml/).

Every frame has a few candidates: the ball net's peaks (every frame) and OWLv2's boxes (every 2nd
frame); candidates of both within MERGE px become one with both scores. The path is the cheapest
chain through the candidates (dynamic programming over frames):
- a chosen candidate earns its detector reward (net score, OWLv2 score, a bonus when both agree);
- a frame without a point costs `miss`; a new segment costs `start`;
- a step costs the squared distance to the position predicted from the previous step's velocity
  (constant velocity), scaled by a tolerance that grows with the speed (bounces, catches and
  deflections change the velocity); steps faster than `vmax` are impossible;
- a predecessor may lie up to `gap` frames back (short occlusions keep the velocity);
- spots that stay put for most of the clip (lamps, a spare ball at the bench) earn no reward.
Gaps inside a segment are filled linearly when `fill` is set.

    from tracker import track_clip   # pre clip (prelabel kernel output) -> per frame [x, y] | None
"""

import math
from dataclasses import dataclass, field


@dataclass
class Params:
    # chosen by random search with 2-fold cross-validation over the gold clips (tune_tracker.py)
    miss: float = 0.35
    start: float = 3.0
    w_net: float = 2.0
    w_owl: float = 6.0
    both: float = 0.4
    net_min: float = 0.1
    owl_min: float = 0.05
    sigma0: float = 6.0  # px of tolerance at rest (per frame, 1280 px wide picture)
    sigma_v: float = 0.6  # extra tolerance per px/frame of speed
    sigma_new: float = 30.0  # tolerance of the first step of a segment (no velocity yet)
    vmax: float = 70.0  # px per frame at 30 fps, 1280 px wide
    gap: int = 2
    merge: float = 8.0
    static_frac: float = 0.5
    static_px: float = 5.0
    static_keep: float = 0.6  # share of the reward a static spot keeps (a ball held still is static too)
    fill: bool = True
    extra: dict = field(default_factory=dict)


@dataclass
class Cand:
    x: float
    y: float
    net: float = 0.0
    owl: float = 0.0
    r: float = 0.0


def candidates(c: dict, p: Params) -> list[list[Cand]]:
    frames: list[list[Cand]] = []
    for r in c["pre"]:
        cs = [Cand(x, y, net=s) for x, y, s in r["net"] if s >= p.net_min]
        for o in r.get("owl", []):
            if o[4] < p.owl_min:
                continue
            near = min(cs, key=lambda q: math.hypot(q.x - o[0], q.y - o[1]), default=None)
            if near and math.hypot(near.x - o[0], near.y - o[1]) <= p.merge:
                near.owl = max(near.owl, o[4])
            else:
                cs.append(Cand(o[0], o[1], owl=o[4]))
        frames.append(cs)
    # static spots: a position that holds a candidate of a detector in most frames that detector
    # ran on (OWLv2 runs on every 2nd frame only)
    cell = p.static_px
    holds: dict[str, dict[tuple[int, int], set[int]]] = {"net": {}, "owl": {}}
    ran = {"net": len(frames), "owl": sum("owl" in r for r in c["pre"])}
    for k, cs in enumerate(frames):
        for q in cs:
            gx, gy = int(q.x // cell), int(q.y // cell)
            for src in ("net", "owl"):
                if getattr(q, src):
                    for dx in (-1, 0, 1):
                        for dy in (-1, 0, 1):
                            holds[src].setdefault((gx + dx, gy + dy), set()).add(k)
    for cs in frames:
        for q in cs:
            g = (int(q.x // cell), int(q.y // cell))
            static = any(
                len(holds[src].get(g, ())) > p.static_frac * max(1, ran[src]) for src in holds
            )
            q.r = (p.static_keep if static else 1.0) * (
                p.w_net * q.net + p.w_owl * q.owl + (p.both if q.net and q.owl else 0.0)
            )
    return frames


def track_clip(c: dict, p: Params | None = None) -> list:
    p = p or Params()
    frames = candidates(c, p)
    n = len(frames)
    scale = c["w"] / 1280 * 30 / c.get("fps_read", c.get("fps", 30))  # px per frame at this clip
    vmax = p.vmax * scale
    INF = float("inf")
    # best[k][j] = (cost, back, vx, vy); back = (k', i) or ("F", k-1) for a segment start
    best: list[list[tuple]] = []
    F = [0.0] * n  # cheapest solution of frames 0..k (frame k may be empty)
    Fb: list = [None] * n  # (k, j) when frame k ends on candidate j, else None (miss)
    for k in range(n):
        row = []
        prevF = F[k - 1] if k else 0.0
        for q in frames[k]:
            cost = prevF + p.start - q.r
            back: tuple = ("F", k - 1)
            vel = (0.0, 0.0)
            for kp in range(max(0, k - p.gap), k):
                dt = k - kp
                skip = p.miss * (dt - 1)
                for i, (c0, _b, vx, vy) in enumerate(best[kp]):
                    if c0 == INF:
                        continue
                    a = frames[kp][i]
                    dx, dy = q.x - a.x, q.y - a.y
                    if math.hypot(dx, dy) > vmax * dt:
                        continue
                    if _b[0] == "F":  # no velocity yet
                        s = p.sigma_new * scale * dt
                        m = (dx * dx + dy * dy) / (2 * s * s)
                    else:
                        ex, ey = dx - vx * dt, dy - vy * dt
                        s = (p.sigma0 * scale + p.sigma_v * math.hypot(vx, vy)) * dt
                        m = (ex * ex + ey * ey) / (2 * s * s)
                    tot = c0 + skip + m - q.r
                    if tot < cost:
                        cost, back, vel = tot, (kp, i), (dx / dt, dy / dt)
            row.append((cost, back, vel[0], vel[1]))
        best.append(row)
        F[k] = prevF + p.miss
        Fb[k] = None
        for j, (c0, *_rest) in enumerate(row):
            if c0 < F[k]:
                F[k], Fb[k] = c0, (k, j)
    out: list = [None] * n
    k = n - 1
    while k >= 0:
        if Fb[k] is None:
            k -= 1
            continue
        kk, j = Fb[k]
        while True:
            q = frames[kk][j]
            out[kk] = [q.x, q.y]
            back = best[kk][j][1]
            if back[0] == "F":
                k = back[1]
                break
            kp, i = back
            if p.fill and kk - kp > 1:
                a = frames[kp][i]
                for t in range(kp + 1, kk):
                    u = (t - kp) / (kk - kp)
                    out[t] = [a.x + u * (q.x - a.x), a.y + u * (q.y - a.y)]
            kk, j = kp, i
    return out
