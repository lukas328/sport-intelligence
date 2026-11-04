"""Multi-object tracking on the court plane (BRIEF 7.2 stage 4).

ByteTrack-style association (own implementation, no external code): constant-velocity Kalman
filter per player in metres, Hungarian matching with a distance gate, first on confident
detections, then on low-score ones. Tracks are confirmed after `min_hits` and kept alive for
`max_age` frames without detections (occlusions), predicted meanwhile. Working in court
coordinates makes gates physical (max sprint speed) instead of pixel based.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import linear_sum_assignment

F64 = NDArray[np.float64]


@dataclass
class _Kalman:
    x: F64  # [px, py, vx, vy]
    p: F64

    @classmethod
    def start(cls, pos: F64) -> _Kalman:
        return cls(np.array([pos[0], pos[1], 0.0, 0.0]), np.diag([0.3, 0.3, 4.0, 4.0]))

    def predict(self, dt: float, q: float = 3.0) -> None:
        f = np.eye(4)
        f[0, 2] = f[1, 3] = dt
        g = np.array([[dt**2 / 2, 0], [0, dt**2 / 2], [dt, 0], [0, dt]])
        self.x = f @ self.x
        self.p = f @ self.p @ f.T + g @ g.T * q**2

    def update(self, z: F64, r: float) -> None:
        h = np.array([[1.0, 0, 0, 0], [0, 1.0, 0, 0]])
        s = h @ self.p @ h.T + np.eye(2) * r**2
        k = self.p @ h.T @ np.linalg.inv(s)
        self.x = self.x + k @ (z - h @ self.x)
        self.p = (np.eye(4) - k @ h) @ self.p


@dataclass
class Track:
    track_id: int
    kf: _Kalman
    feature: F64 | None = None  # running mean torso colour (Lab)
    label_votes: dict[str, int] = field(default_factory=dict)

    @property
    def label(self) -> str | None:
        if not self.label_votes:
            return None
        best = max(self.label_votes, key=self.label_votes.__getitem__)
        return best if self.label_votes[best] >= 3 else None

    hits: int = 1
    misses: int = 0
    hidden: int = 0  # steps spent outside the camera's view (panning cameras)
    confirmed: bool = False
    history: list[tuple[int, float, float, bool]] = field(
        default_factory=list
    )  # frame, x, y, observed

    @property
    def pos(self) -> F64:
        return self.kf.x[:2]


@dataclass(frozen=True)
class TrackPoint:
    track_id: int
    frame: int
    x: float
    y: float
    vx: float
    vy: float
    observed: bool
    det_index: int | None


class CourtTracker:
    def __init__(
        self,
        fps: float,
        gate_m: float = 2.0,
        high: float = 0.5,
        min_hits: int = 3,
        max_age_s: float = 2.0,
        meas_noise_m: float = 0.25,
        colour_weight: float = 0.0,
        colour_gate: float = 40.0,
        predict_output_s: float = 0.4,
        label_penalty_m: float = 0.6,
        max_hidden_s: float = 90.0,
    ) -> None:
        self.dt = 1 / fps
        self.gate = gate_m
        self.high = high
        self.min_hits = min_hits
        self.max_age = round(max_age_s * fps)
        self.max_hidden = round(max_hidden_s * fps)
        self.r = meas_noise_m
        self.cw = colour_weight
        self.label_penalty = label_penalty_m
        self.cgate = colour_gate
        self.predict_out = round(predict_output_s * fps)
        self.tracks: list[Track] = []
        self._next = 1
        self.frame = -1

    def _match(
        self,
        tracks: list[Track],
        pos: F64,
        gate: float,
        feats: F64 | None = None,
        labels: list[str | None] | None = None,
    ) -> tuple[list[tuple[int, int]], list[int], list[int]]:
        if not tracks or len(pos) == 0:
            return [], list(range(len(tracks))), list(range(len(pos)))
        tp = np.array([t.pos for t in tracks])
        cost = np.linalg.norm(tp[:, None] - pos[None], axis=2)
        if labels is not None:
            for i, t in enumerate(tracks):
                tl = t.label
                if tl is None:
                    continue
                # a confident team label never jumps to the other team's player
                penalty = np.array([1e6 if (lb is not None and lb != tl) else 0.0 for lb in labels])
                cost[i] = cost[i] + penalty
        if feats is not None and len(feats):
            for i, t in enumerate(tracks):
                if t.feature is None:
                    continue
                cd = np.linalg.norm(feats - t.feature, axis=1)
                cd = np.where(np.isnan(cd), 0.0, cd)
                cost[i] = np.where(cd > self.cgate, 1e6, cost[i] + self.cw * cd)
        # inflate the gate for tracks that have been predicted for a while
        gates = np.array(
            [
                gate + 0.5 * min(t.misses, 6) * self.dt * 7 + min(4.0, t.hidden * self.dt * 1.0)
                for t in tracks
            ]
        )
        cost = np.where(cost > gates[:, None], 1e6, cost)
        r, c = linear_sum_assignment(cost)
        pairs = [(i, j) for i, j in zip(r, c, strict=True) if cost[i, j] < 1e6]
        mt = {i for i, _ in pairs}
        md = {j for _, j in pairs}
        return (
            pairs,
            [i for i in range(len(tracks)) if i not in mt],
            [j for j in range(len(pos)) if j not in md],
        )

    def step(
        self,
        positions: F64,
        scores: NDArray[np.floating],
        features: F64 | None = None,
        labels: list[str | None] | None = None,
        visible: Callable[[F64], NDArray[np.bool_]] | None = None,
    ) -> list[TrackPoint]:
        """positions: (n, 2) court metres; scores: (n,); features: optional (n, 3) colours (NaN =
        unknown); `visible` (panning cameras) tells which court points the frame shows: a player
        outside the view is not missing, so his track waits (up to `max_hidden_s`) instead of
        ageing, and is matched again with a wider gate when he comes back into view."""
        self.frame += 1
        hidden_now: set[int] = set()
        if visible is not None and self.tracks:
            seen = visible(np.array([t.pos for t in self.tracks]))
            hidden_now = {i for i, v in enumerate(seen) if not v}
        for i, t in enumerate(self.tracks):
            if i in hidden_now:
                t.kf.x[2:] *= 0.8  # an unseen player is assumed to slow down, not run away
                t.kf.predict(self.dt, q=1.0)
            else:
                t.kf.predict(self.dt)
        positions = np.asarray(positions, dtype=np.float64).reshape(-1, 2)
        scores = np.asarray(scores, dtype=np.float64).reshape(-1)
        high = np.nonzero(scores >= self.high)[0]
        low = np.nonzero(scores < self.high)[0]
        assigned: dict[int, int] = {}

        feats = None if features is None else np.asarray(features, dtype=np.float64).reshape(-1, 3)
        lab = labels or [None] * len(positions)
        pairs, un_t, un_d = self._match(
            self.tracks,
            positions[high],
            self.gate,
            None if feats is None else feats[high],
            [lab[i] for i in high],
        )
        for ti, dj in pairs:
            assigned[ti] = int(high[dj])
        rest = [self.tracks[i] for i in un_t]
        pairs2, _, _ = self._match(
            rest,
            positions[low],
            self.gate * 0.6,
            None if feats is None else feats[low],
            [lab[i] for i in low],
        )
        for ri, dj in pairs2:
            assigned[un_t[ri]] = int(low[dj])

        for ti, t in enumerate(self.tracks):
            if ti in assigned:
                j = assigned[ti]
                t.kf.update(positions[j], self.r)
                lbl = lab[j]
                if lbl is not None:
                    t.label_votes[lbl] = t.label_votes.get(lbl, 0) + 1
                if feats is not None and not np.isnan(feats[j]).any():
                    t.feature = feats[j] if t.feature is None else 0.9 * t.feature + 0.1 * feats[j]
                t.hits += 1
                t.misses = 0
                if t.hits >= self.min_hits:
                    t.confirmed = True
            elif ti in hidden_now:
                t.hidden += 1
            else:
                t.misses += 1
        for ti in assigned:
            if ti < len(self.tracks):
                self.tracks[ti].hidden = 0
        # new tracks only from confident unmatched detections
        for dj in un_d:
            j = int(high[dj])
            f = None if feats is None or np.isnan(feats[j]).any() else feats[j]
            self.tracks.append(Track(self._next, _Kalman.start(positions[j]), feature=f))
            assigned[len(self.tracks) - 1] = j
            self._next += 1
        self.tracks = [
            t
            for t in self.tracks
            if t.misses <= (self.max_age if t.confirmed else 1)
            and t.hidden <= (self.max_hidden if t.confirmed else 0)
        ]

        out = []
        index_of = {id(self.tracks[i]): d for i, d in assigned.items() if i < len(self.tracks)}
        for t in self.tracks:
            if not t.confirmed or t.misses > self.predict_out or t.hidden > 0:
                continue
            x, y, vx, vy = (float(v) for v in t.kf.x)
            obs = t.misses == 0
            t.history.append((self.frame, x, y, obs))
            out.append(
                TrackPoint(
                    t.track_id, self.frame, x, y, vx, vy, obs, index_of.get(id(t)) if obs else None
                )
            )
        return out


def same_shirt(a: F64, b: F64, lab_gate: float = 35.0, hue_gate_deg: float = 28.0) -> bool:
    """Could two median torso colours (Lab) be the same shirt? Coloured shirts must agree in hue
    (video washes saturation out, hue survives); grey ones in lightness."""
    ca = np.array([a[1] - 128.0, a[2] - 128.0])
    cb = np.array([b[1] - 128.0, b[2] - 128.0])
    ma, mb = float(np.hypot(*ca)), float(np.hypot(*cb))
    if ma >= 7 and mb >= 7:
        cos = float(ca @ cb) / (ma * mb)
        if np.degrees(np.arccos(np.clip(cos, -1, 1))) > hue_gate_deg:
            return False
    elif (ma >= 12) != (mb >= 12):  # one clearly coloured, the other grey
        return False
    return float(np.linalg.norm(a - b)) <= lab_gate * 1.5


def stitch(
    points: list[TrackPoint],
    fps: float,
    max_gap_s: float = 4.0,
    speed_mps: float = 7.0,
    colours: dict[int, F64] | None = None,
    colour_gate: float = 35.0,
    rounds: int = 3,
) -> tuple[list[TrackPoint], dict[int, int]]:
    """Offline tracklet stitching: link a chain that ends to one that starts shortly after, if a
    player could have run the distance in between (and the shirt colour agrees). Each round is a
    global optimum via Hungarian matching of chain ends to chain starts. The analysis runs after
    the match, so using the future is allowed here."""
    by: dict[int, list[TrackPoint]] = {}
    for p in points:
        by.setdefault(p.track_id, []).append(p)
    chains: list[list[int]] = [[i] for i in sorted(by)]
    max_gap = round(max_gap_s * fps)

    def colour(chain: list[int]) -> F64 | None:
        cs = [colours[i] for i in chain if colours and i in colours]
        return np.median(np.stack(cs), axis=0) if cs else None

    for _ in range(rounds):
        n = len(chains)
        if n < 2:
            break
        ends = [by[c[-1]][-1] for c in chains]
        starts = [by[c[0]][0] for c in chains]
        cols = [colour(c) for c in chains]
        cost = np.full((n, n), 1e6)
        for a in range(n):
            for b in range(n):
                if a == b:
                    continue
                gap = starts[b].frame - ends[a].frame
                if gap <= 0 or gap > max_gap:
                    continue
                d = float(np.hypot(starts[b].x - ends[a].x, starts[b].y - ends[a].y))
                if d > 1.0 + speed_mps * gap / fps:
                    continue
                ca, cb = cols[a], cols[b]
                if ca is not None and cb is not None and not same_shirt(ca, cb, colour_gate):
                    continue
                cost[a, b] = d + 0.5 * gap / fps
        r, c = linear_sum_assignment(cost)
        links = {int(a): int(b) for a, b in zip(r, c, strict=True) if cost[a, b] < 1e6}
        if not links:
            break
        # follow links from chains that are nobody's successor; avoid cycles
        successors = set(links.values())
        merged: list[list[int]] = []
        used: set[int] = set()
        for a in range(n):
            if a in successors or a in used:
                continue
            chain: list[int] = []
            nxt: int | None = a
            while nxt is not None and nxt not in used:
                used.add(nxt)
                chain += chains[nxt]
                nxt = links.get(nxt)
            merged.append(chain)
        merged += [chains[k] for k in range(n) if k not in used]
        chains = merged

    mapping = {i: chain[0] for chain in chains for i in chain}
    out = [
        TrackPoint(mapping[p.track_id], p.frame, p.x, p.y, p.vx, p.vy, p.observed, p.det_index)
        for p in points
    ]
    out.sort(key=lambda p: (p.frame, p.track_id))
    return out, mapping
