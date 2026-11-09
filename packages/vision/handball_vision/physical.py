"""Physical load per track from court positions (BRIEF 7.2 stage 5 consumers, M5).

Positions from a single broadcast-style camera are noisy (foot point jitter of 0.3 to 0.5 m), so raw
frame-to-frame distances overestimate running distance by a lot. We therefore:

1. resample to 5 Hz (mean position per 200 ms bin),
2. smooth with a centred moving average over 3 bins (600 ms),
3. drop steps across gaps longer than 1 s (track lost) and physically impossible steps (> 10 m/s),
   found before smoothing so that a jump is not smeared into plausible steps,
4. use only observed points (the tracker's predictions in between are not measurements).

Speed bands follow common handball load monitoring practice (local positioning systems report similar
bands); see packages/metrics/DEFINITIONS.md "Physical". All values are estimates and labelled as such in
the UI.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np
from numpy.typing import NDArray

BIN_MS = 200
MAX_GAP_MS = 1000
MAX_SPEED = 10.0  # m/s, above this a step is a tracking jump
# lower bounds in m/s: walking, jogging, running, sprinting
BANDS = {"walk": 0.0, "jog": 2.0, "run": 4.0, "sprint": 5.5}
SPRINT_MIN_MS = 1000
MAX_HOLD_MS = 1000  # a top speed must be held this long
HEAT_COLS, HEAT_ROWS = 10, 5
COURT_L, COURT_W = 40.0, 20.0


@dataclass
class Physical:
    distance_m: float
    duration_s: float
    max_speed_ms: float
    sprints: int
    band_distance_m: dict[str, float] = field(default_factory=dict)
    heatmap: list[list[float]] = field(default_factory=list)  # rows (y) x cols (x), share of time

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["distance_m"] = round(self.distance_m, 1)
        d["duration_s"] = round(self.duration_s, 1)
        d["max_speed_ms"] = round(self.max_speed_ms, 2)
        d["band_distance_m"] = {k: round(v, 1) for k, v in self.band_distance_m.items()}
        d["heatmap"] = [[round(v, 4) for v in row] for row in self.heatmap]
        return d


def _resample(
    t_ms: NDArray[np.float64], xy: NDArray[np.float64]
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    bins = np.floor(t_ms / BIN_MS).astype(np.int64)
    uniq, inv = np.unique(bins, return_inverse=True)
    sums = np.zeros((len(uniq), 2))
    np.add.at(sums, inv, xy)
    counts = np.bincount(inv).astype(np.float64)
    return uniq.astype(np.float64) * BIN_MS + BIN_MS / 2, sums / counts[:, None]


def _smooth(
    t: NDArray[np.float64], xy: NDArray[np.float64], seg: NDArray[np.int64]
) -> NDArray[np.float64]:
    """Centred 3-bin moving average that does not smear across gaps or jumps (`seg` changes)."""
    out = xy.copy()
    for i in range(1, len(xy) - 1):
        if t[i + 1] - t[i - 1] <= 2 * BIN_MS + 1 and seg[i - 1] == seg[i + 1]:
            out[i] = xy[i - 1 : i + 2].mean(axis=0)
    return out


def physical(
    t_ms: NDArray[np.float64],
    x: NDArray[np.float64],
    y: NDArray[np.float64],
    observed: NDArray[np.bool_] | None = None,
) -> Physical:
    """Load metrics for one track. `t_ms` must be sorted ascending (video time). `observed` marks
    the points backed by a detection; the tracker's predictions in between are not measurements
    and are left out (a coasting prediction that snaps back on the next detection is a jump)."""
    heat = np.zeros((HEAT_ROWS, HEAT_COLS))
    if observed is not None:
        keep = np.asarray(observed, bool)
        t_ms, x, y = np.asarray(t_ms)[keep], np.asarray(x)[keep], np.asarray(y)[keep]
    if len(t_ms) < 2:
        return Physical(0.0, 0.0, 0.0, 0, {k: 0.0 for k in BANDS}, heat.tolist())
    t, xy = _resample(np.asarray(t_ms, float), np.column_stack([x, y]).astype(float))
    dt = np.diff(t)
    # gaps and jumps are found on the raw positions: smoothing spreads a jump (the track taking
    # over a neighbour 2 m away) over three steps that each look like a plausible sprint
    raw_speed = np.linalg.norm(np.diff(xy, axis=0), axis=1) / (dt / 1000)
    breaks = (dt > MAX_GAP_MS) | (raw_speed > MAX_SPEED)
    seg = np.concatenate([[0], np.cumsum(breaks)]).astype(np.int64)
    xy = _smooth(t, xy, seg)
    step = np.linalg.norm(np.diff(xy, axis=0), axis=1)
    speed = step / (dt / 1000)
    valid = ~breaks & (speed <= MAX_SPEED)

    band_dist = {}
    names = list(BANDS)
    for i, name in enumerate(names):
        lo = BANDS[name]
        hi = BANDS[names[i + 1]] if i + 1 < len(names) else np.inf
        band_dist[name] = float(step[valid & (speed >= lo) & (speed < hi)].sum())

    # sprints: runs of consecutive valid steps at sprint speed lasting at least SPRINT_MIN_MS
    sprints, run_ms = 0, 0.0
    for ok, s, d in zip(valid, speed, dt, strict=True):
        if ok and s >= BANDS["sprint"]:
            run_ms += d
        else:
            sprints += run_ms >= SPRINT_MIN_MS
            run_ms = 0.0
    sprints += run_ms >= SPRINT_MIN_MS

    # max speed: the highest speed held over MAX_HOLD_MS (consecutive valid steps), so that a short
    # tracking error (a lagging box catching up, two players merged for a moment) is not a top speed
    max_speed = 0.0
    k = MAX_HOLD_MS // BIN_MS
    if len(speed) >= k:
        win = np.lib.stride_tricks.sliding_window_view
        held = win(np.where(valid, speed, 0.0), k).min(axis=1)
        held_ok = win(valid, k).all(axis=1)
        max_speed = float(held[held_ok].max()) if held_ok.any() else 0.0

    cols = np.clip((xy[:, 0] / COURT_L * HEAT_COLS).astype(int), 0, HEAT_COLS - 1)
    rows = np.clip((xy[:, 1] / COURT_W * HEAT_ROWS).astype(int), 0, HEAT_ROWS - 1)
    np.add.at(heat, (rows, cols), 1)
    heat /= heat.sum()

    observed_s = float(dt[dt <= MAX_GAP_MS].sum() / 1000)
    return Physical(
        distance_m=float(step[valid].sum()),
        duration_s=observed_s,
        max_speed_ms=max_speed,
        sprints=int(sprints),
        band_distance_m=band_dist,
        heatmap=heat.tolist(),
    )


def merge(items: list[Physical]) -> Physical:
    """Combine several tracks of the same player (track fragments, several halves)."""
    if not items:
        return physical(np.zeros(0), np.zeros(0), np.zeros(0))
    total = sum(p.duration_s for p in items) or 1.0
    heat = sum(np.array(p.heatmap) * (p.duration_s / total) for p in items)
    return Physical(
        distance_m=sum(p.distance_m for p in items),
        duration_s=sum(p.duration_s for p in items),
        max_speed_ms=max(p.max_speed_ms for p in items),
        sprints=sum(p.sprints for p in items),
        band_distance_m={k: sum(p.band_distance_m.get(k, 0.0) for p in items) for k in BANDS},
        heatmap=np.asarray(heat).tolist(),
    )


def from_dict(d: dict[str, Any]) -> Physical:
    return Physical(
        distance_m=float(d["distance_m"]),
        duration_s=float(d["duration_s"]),
        max_speed_ms=float(d["max_speed_ms"]),
        sprints=int(d["sprints"]),
        band_distance_m={k: float(v) for k, v in d.get("band_distance_m", {}).items()},
        heatmap=d.get("heatmap", []),
    )
