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
- repeated frames: many videos repeat frames (25 fps stored as 50, 24/25 fps as 30 or 60), so a
  flying ball stands still for one frame and then jumps two steps. A candidate within `dup_px` of
  its predecessor one frame back is taken as such a repeat: it keeps the predecessor's velocity
  instead of zeroing it, at most `dup_max` times in a row (a ball held still is then an ordinary
  still step with velocity zero);
- a fast ball (predecessor speed at least `v_fast`, px per frame at 30 fps) may skip up to
  `gap_fast` frames: the nets often see a flying ball only every second or third frame, while a
  slow wrong object (a scrolling banner, a lamp moving with the pan) is seen in every frame;
- with `rescore` set, a candidate's reward is `rescore` times its ball probability from a logistic
  regression (tracker_rescore.py, weights in data/tracker_rescore.json) on net score, top-1, OWLv2
  score, agreement, static spot, moving support (a moving pair one or two frames before and after
  with this point in the middle) and slow persistence (candidates nearby in most of +-10 frames);
  trained on the training clips with candidates of a net that never saw their labels;
  a clip without any OWLv2 output (the shippable case: the product cannot run OWLv2) uses weights
  learned without OWLv2 (data/tracker_rescore_noowl.json, `tracker_rescore.py --noowl`);
- spots that stay put for most of the clip (lamps, a spare ball at the bench) earn no reward.
Gaps inside a segment are filled linearly when `fill` is set.

Confidence ("don't know"): `track_clip_conf` also returns a confidence per output point, the
geometric mean of the point's ball probability (rescoring; for a filled frame the lower of its two
ends) and the mean probability of its whole segment (a path on a wrong object is usually weak along
its length, a single weak point inside a good flight is not). With `conf_min` > 0, `track_clip`
leaves points below it out (None). Default 0: output unchanged.

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
    dup_px: float = 5.0  # a repeated frame: the candidate within this many px of the previous one
    dup_max: int = 1  # repeats in a row that keep the velocity (0 = off)
    gap_fast: int = 4  # longer gaps for a fast ball: predecessor speed at least v_fast (px/frame at 30 fps)
    v_fast: float = 8.0
    rescore: float = 3.0  # > 0: reward = rescore * ball probability of tracker_rescore.py (0 = hand-set reward)
    rescore_w: str = "auto"  # "auto": no-OWLv2 weights for a clip without OWLv2 output; "owl" / "noowl" to force
    conf_min: float = 0.0  # > 0: leave out points whose confidence is below (track_clip_conf)
    extra: dict = field(default_factory=dict)


@dataclass
class Cand:
    x: float
    y: float
    net: float = 0.0
    owl: float = 0.0
    r: float = 0.0
    static: bool = False


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
            q.static = static
            q.r = (p.static_keep if static else 1.0) * (
                p.w_net * q.net + p.w_owl * q.owl + (p.both if q.net and q.owl else 0.0)
            )
    return frames


_W: dict = {}


def _weights(kind: str) -> list:
    import json
    from pathlib import Path

    if kind not in _W:
        name = "tracker_rescore_noowl.json" if kind == "noowl" else "tracker_rescore.json"
        _W[kind] = json.loads((Path(__file__).resolve().parent / "data" / name).read_text())["w"]
    return _W[kind]


def _rescore(frames, scale, p, has_owl: bool) -> None:
    from tracker_rescore import features

    kind = p.rescore_w if p.rescore_w != "auto" else ("owl" if has_owl else "noowl")
    w = p.extra.get("rescore_w", _weights(kind))
    F = features(frames, [[q.static for q in cs] for cs in frames], scale)
    for cs, fs in zip(frames, F):
        for q, f in zip(cs, fs):
            z = sum(a * b for a, b in zip(w, f))
            q.r = p.rescore / (1 + math.exp(-z))


def track_clip(c: dict, p: Params | None = None) -> list:
    p = p or Params()
    out, conf = track_clip_conf(c, p)
    if p.conf_min > 0:
        out = [q if q is not None and cf >= p.conf_min else None for q, cf in zip(out, conf)]
    return out


def track_clip_conf(c: dict, p: Params | None = None) -> tuple[list, list]:
    """Per frame [x, y] or None, and a confidence in 0..1 per frame (0 where None)."""
    p = p or Params()
    frames = candidates(c, p)
    n = len(frames)
    scale = c["w"] / 1280 * 30 / c.get("fps_read", c.get("fps", 30))  # px per frame at this clip
    if p.rescore > 0:
        _rescore(frames, scale, p, any(r.get("owl") for r in c["pre"]))
    norm = p.rescore if p.rescore > 0 else max(p.w_net, p.w_owl) + p.both
    vmax = p.vmax * scale
    gfast = p.gap_fast
    INF = float("inf")
    # best[k][j] = (cost, back, vx, vy, reps); back = (k', i) or ("F", k-1) for a segment start;
    # reps = repeated frames in a row that ended here
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
            reps = 0
            for kp in range(max(0, k - max(p.gap, gfast)), k):
                dt = k - kp
                skip = p.miss * (dt - 1)
                for i, (c0, _b, vx, vy, rp) in enumerate(best[kp]):
                    if c0 == INF:
                        continue
                    if dt > p.gap and (_b[0] == "F" or math.hypot(vx, vy) < p.v_fast * scale):
                        continue
                    a = frames[kp][i]
                    dx, dy = q.x - a.x, q.y - a.y
                    if math.hypot(dx, dy) > vmax * dt:
                        continue
                    if (dt == 1 and rp < p.dup_max and _b[0] != "F" and math.hypot(dx, dy) <= p.dup_px * c["w"] / 1280
                            and math.hypot(vx, vy) > p.dup_px * c["w"] / 1280):
                        # a repeated frame of a moving ball: keep its velocity
                        s = p.sigma0 * scale
                        tot = c0 + (dx * dx + dy * dy) / (2 * s * s) - q.r
                        if tot < cost:
                            cost, back, vel, reps = tot, (kp, i), (vx, vy), rp + 1
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
                        cost, back, vel, reps = tot, (kp, i), (dx / dt, dy / dt), 0
            row.append((cost, back, vel[0], vel[1], reps))
        best.append(row)
        F[k] = prevF + p.miss
        Fb[k] = None
        for j, (c0, *_rest) in enumerate(row):
            if c0 < F[k]:
                F[k], Fb[k] = c0, (k, j)
    out: list = [None] * n
    pt = [0.0] * n  # ball probability of the point (filled frames: the lower end)
    conf = [0.0] * n
    k = n - 1
    while k >= 0:
        if Fb[k] is None:
            k -= 1
            continue
        kk, j = Fb[k]
        seg = []  # frames of this segment and the probabilities of its chosen candidates
        while True:
            q = frames[kk][j]
            prob = min(1.0, max(0.0, q.r / norm))
            out[kk], pt[kk] = [q.x, q.y], prob
            seg.append(kk)
            back = best[kk][j][1]
            if back[0] == "F":
                k = back[1]
                break
            kp, i = back
            if p.fill and kk - kp > 1:
                a = frames[kp][i]
                pa = min(1.0, max(0.0, a.r / norm))
                for t in range(kp + 1, kk):
                    u = (t - kp) / (kk - kp)
                    out[t], pt[t] = [a.x + u * (q.x - a.x), a.y + u * (q.y - a.y)], min(prob, pa)
                    seg.append(t)
            kk, j = kp, i
        detected = [pt[t] for t in seg]
        mean = sum(detected) / len(detected)
        mode = p.extra.get("conf_mode", "geo")
        for t in seg:
            conf[t] = {"point": pt[t], "segment": mean}.get(mode, math.sqrt(pt[t] * mean))
    return out, conf
