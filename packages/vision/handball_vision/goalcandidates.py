"""Goal candidates: moments of the video that are probably goals, for a coach to confirm or reject
with one click (research: ml/goals/README.md, "Club footage: goal candidates").

Everything comes from the observation pass (`observe.observe`): the camera motion and the people
detections. Nothing is decoded a second time and no court calibration is needed.

Signals on a 10 Hz grid of video time (`signals`), in "reference pixels" (a 1280 px wide frame at
the median zoom, the units the template was learned in):
- `pan`: horizontal camera speed (canvas x of the frame centre per second; 0 for a fixed camera);
- `cx_v`: speed of the people's median x in the image (canvas velocity minus the camera's): the
  play running towards one half while the camera lags or swings;
- `vx`, `speed`: people matched mutual-nearest between detection frames 0.5 s apart on the canvas;
  their mean x velocity in the image and their mean speed in body heights per second (activity).
People are sampled at 2 Hz as in the training data; benches, spectators and the officials' table
are dropped as "static" (a canvas spot occupied in most detection frames of the surrounding 30 s).

Score (`score`): a matched filter (cosine similarity of the channels from 2 s before to 3 s after
t with the mean goal profile learned from overlay score changes, `data/goal_template.json`) plus
the post-goal lull (busy around t, quiet 8 to 24 s later), each as a rolling robust z-score.
Channels and scores are normalised over a rolling window of 3 minutes, the segment length the
template was learned on, so the camera operator's style and the zoom may change during a game.

Candidates (`pick`): a fixed number per minute, not a score threshold (score scales vary per game):
per 3-minute block the best peaks with 8 s non-maximum suppression, none in the first and last
2 s. Every candidate carries the lowest rate (1, 2 or 4 per minute) at which it is proposed, so
the coach can ask for more without a re-run; the clip runs from 10 s before to 4 s after the peak,
which lies a median 1.5 s after the goal.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

F64 = NDArray[np.float64]

TEMPLATE_PATH = Path(__file__).resolve().parent / "data" / "goal_template.json"
DT = 0.1  # grid step (s)
PEOPLE_DT = 0.5  # people sampled at 2 Hz (as in the training data)
REF_WIDTH = 1280.0  # reference pixels: a frame this wide
BLOCK_S = 180.0  # normalisation window and selection block (the training segments' length)
NMS_S = 8.0
EDGE_S = 2.0
RATES = (1, 2, 4)  # candidates per minute
DEFAULT_RATE = 2
CLIP_BEFORE_S, CLIP_AFTER_S = 10.0, 4.0
GOAL_OFFSET_S = 1.5  # median peak - goal on the labelled games
MIN_DURATION_S = 30.0
# static people (bench, spectators, table): canvas spot occupied in `STATIC_SHARE` of the frames
STATIC_WIN_S, STATIC_RX, STATIC_RY, STATIC_SHARE = 15.0, 25.0, 15.0, 0.6
MIN_BOX_PX = 18.0  # reference px
MATCH_HEIGHTS = 1.2  # nearest-neighbour match within this many body heights
# no play (half-time, before and after the game): an operated camera standing still for minutes
STILL_PX_S = 40.0  # camera speed below this is "still" (reference px/s)
STILL_WINDOW_S = 120.0  # centred window
STILL_SHARE = 0.97  # share of the window the camera must be still


@dataclass(frozen=True)
class Template:
    version: str
    channels: tuple[str, ...]
    sign_cols: tuple[int, ...]
    window_s: tuple[float, float]
    profile: F64  # samples x channels, per-window standardised channels
    lull_busy_s: tuple[float, float]
    lull_quiet_s: tuple[float, float]
    meta: dict[str, Any]

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Template:
        channels = tuple(str(c) for c in d["channels"])
        profile = np.asarray(d["profile"], dtype=np.float64)
        n = round((d["window_s"][1] - d["window_s"][0]) / d["dt_s"])
        if profile.shape != (n, len(channels)) or abs(float(d["dt_s"]) - DT) > 1e-9:
            raise ValueError(
                f"goal template: profile {profile.shape}, expected ({n}, {len(channels)})"
            )
        return cls(
            version=str(d["version"]),
            channels=channels,
            sign_cols=tuple(channels.index(c) for c in d["sign_channels"]),
            window_s=(float(d["window_s"][0]), float(d["window_s"][1])),
            profile=profile,
            lull_busy_s=(float(d["lull"]["busy_s"][0]), float(d["lull"]["busy_s"][1])),
            lull_quiet_s=(float(d["lull"]["quiet_s"][0]), float(d["lull"]["quiet_s"][1])),
            meta={k: v for k, v in d.items() if k not in ("profile",)},
        )


@lru_cache(maxsize=4)
def load_template(path: Path = TEMPLATE_PATH) -> Template:
    return Template.from_dict(json.loads(Path(path).read_text()))


@dataclass(frozen=True)
class Candidate:
    t: float  # peak (s of video)
    score: float
    rate: int  # lowest candidates-per-minute rate that proposes it
    rank: int  # position in its block (0 = best)

    def to_dict(self, duration_s: float) -> dict[str, Any]:
        return {
            "t_ms": round(self.t * 1000),
            "goal_ms": round(max(0.0, self.t - GOAL_OFFSET_S) * 1000),
            "start_ms": round(max(0.0, self.t - CLIP_BEFORE_S) * 1000),
            "end_ms": round(min(duration_s, self.t + CLIP_AFTER_S) * 1000),
            "score": round(float(self.score), 3),
            "rate": self.rate,
            "rank": self.rank,
        }


# --- small numeric helpers -----------------------------------------------------------------------


def smooth(x: F64, sec: float) -> F64:
    """Hanning smoothing over about `sec` seconds (edges padded)."""
    k = max(1, round(sec / DT))
    if k <= 1:
        return x
    w = np.hanning(k + 2)[1:-1]
    w /= w.sum()
    xp = np.pad(x, (k, k), mode="edge")
    return np.asarray(np.convolve(xp, w, mode="same")[k:-k], dtype=np.float64)


def median3(x: F64) -> F64:
    """Running median of 3 (edges repeated): removes one-sample spikes, keeps steps and ramps."""
    if len(x) < 3:
        return x
    p = np.pad(x, 1, mode="edge")
    return np.asarray(np.median(np.stack([p[:-2], p[1:-1], p[2:]]), axis=0), dtype=np.float64)


def bin_mean(t: F64, x: F64, n: int) -> F64:
    """Mean of x per grid cell [k DT, (k + 1) DT); empty cells interpolated."""
    idx = np.floor(t / DT).astype(int)
    ok = (idx >= 0) & (idx < n) & np.isfinite(x)
    s = np.bincount(idx[ok], weights=x[ok], minlength=n)
    c = np.bincount(idx[ok], minlength=n)
    have = c > 0
    out = np.zeros(n)
    out[have] = s[have] / c[have]
    if 2 <= have.sum() < n:
        tg = np.arange(n) * DT
        out[~have] = np.interp(tg[~have], tg[have], out[have])
    return out


def _interp(tg: F64, t: F64, v: F64, sec: float) -> F64:
    ok = np.isfinite(v)
    if ok.sum() < 5:
        return np.zeros(len(tg))
    return smooth(np.interp(tg, t[ok], v[ok]), sec)


def _robust_scale(x: F64) -> float:
    return float(max(np.percentile(np.abs(x), 90), 1e-6)) if len(x) else 1.0


def _window_bounds(n: int, win_s: float) -> tuple[NDArray[np.int_], NDArray[np.int_]]:
    """[lo, hi) of a window of `win_s` centred on each grid index, moved inwards at the ends so
    it keeps its full length (a video as short as the window gets one set of statistics, as the
    3-minute training segments did)."""
    m = min(n, max(1, round(win_s / DT)))
    lo = np.clip(np.arange(n) - m // 2, 0, n - m)
    return lo, lo + m


def rolling_standardise(ch: F64, win_s: float = BLOCK_S) -> F64:
    """(x - mean) / sd per column over a rolling window of `win_s` (`_window_bounds`)."""
    lo, hi = _window_bounds(len(ch), win_s)
    c1 = np.vstack([np.zeros((1, ch.shape[1])), np.cumsum(ch, axis=0)])
    c2 = np.vstack([np.zeros((1, ch.shape[1])), np.cumsum(ch**2, axis=0)])
    cnt = (hi - lo)[:, None].astype(np.float64)
    mean = (c1[hi] - c1[lo]) / cnt
    var = np.maximum((c2[hi] - c2[lo]) / cnt - mean**2, 0.0)
    return np.asarray((ch - mean) / (np.sqrt(var) + 1e-6), dtype=np.float64)


def rolling_rz(v: F64, win_s: float = BLOCK_S, step_s: float = 5.0) -> F64:
    """Robust z-score (median / IQR, clipped to -3..10) over a rolling window of `win_s`
    (`_window_bounds`), the statistics taken every `step_s` and interpolated."""
    n = len(v)
    if n == 0:
        return v
    lo, hi = _window_bounds(n, win_s)
    at = np.unique(np.r_[np.arange(0, n, max(1, round(step_s / DT))), n - 1])
    med, iqr = [], []
    for i in at:
        q1, q2, q3 = np.percentile(v[lo[i] : hi[i]], [25, 50, 75])
        med.append(q2)
        iqr.append(max(q3 - q1, 1e-6))
    idx = np.arange(n)
    m = np.interp(idx, at, med)
    s = np.interp(idx, at, iqr)
    return np.asarray(np.clip((v - m) / s, -3, 10), dtype=np.float64)


# --- signals -------------------------------------------------------------------------------------


def static_mask(pt: F64, px: F64, py: F64) -> NDArray[np.bool_]:
    """True for detections at a canvas spot that is occupied in at least `STATIC_SHARE` of the
    detection frames within +-`STATIC_WIN_S` (benches, spectators, the officials' table)."""
    out = np.zeros(len(pt), bool)
    if len(pt) == 0:
        return out
    order = np.argsort(pt, kind="stable")
    ts, xs, ys = pt[order], px[order], py[order]
    frames, fidx = np.unique(ts, return_inverse=True)
    starts = np.searchsorted(ts, frames, side="left")
    ends = np.searchsorted(ts, frames, side="right")
    for f in range(len(frames)):
        a, b = starts[f], ends[f]
        lo = np.searchsorted(ts, frames[f] - STATIC_WIN_S - 1e-9, side="left")
        hi = np.searchsorted(ts, frames[f] + STATIC_WIN_S + 1e-9, side="right")
        near = (np.abs(xs[lo:hi][None, :] - xs[a:b, None]) <= STATIC_RX) & (
            np.abs(ys[lo:hi][None, :] - ys[a:b, None]) <= STATIC_RY
        )
        f0, f1 = fidx[lo], fidx[hi - 1] + 1
        occ = np.zeros((b - a, f1 - f0), bool)
        rows, cols = np.nonzero(near)
        occ[rows, fidx[lo:hi][cols] - f0] = True
        out[order[a:b]] = occ.sum(axis=1) >= STATIC_SHARE * (f1 - f0)
    return out


def people_motion(
    pt: F64, px: F64, py: F64, ph: F64, keep: NDArray[np.bool_]
) -> tuple[F64, F64, F64, F64]:
    """Per detection frame: median canvas x of the kept people, and of the people matched
    mutual-nearest to the previous detection frame (within `MATCH_HEIGHTS` body heights) their
    mean canvas x velocity and mean speed in body heights per second."""
    frames = np.unique(pt)
    med = np.full(len(frames), np.nan)
    vx = np.full(len(frames), np.nan)
    sp = np.full(len(frames), np.nan)
    prev: tuple[float, F64] | None = None
    order = np.argsort(pt, kind="stable")
    ts = pt[order]
    starts = np.searchsorted(ts, frames, side="left")
    ends = np.searchsorted(ts, frames, side="right")
    for k, f in enumerate(frames):
        sel = order[starts[k] : ends[k]]
        sel = sel[keep[sel]]
        cur = np.column_stack([px[sel], py[sel], ph[sel]])
        if len(cur) >= 2:
            med[k] = float(np.median(cur[:, 0]))
        if prev is not None and len(cur) and len(prev[1]):
            p = prev[1]
            dt = f - prev[0]
            d = np.hypot(cur[:, None, 0] - p[None, :, 0], cur[:, None, 1] - p[None, :, 1])
            a = d.argmin(axis=1)
            mutual = d.argmin(axis=0)[a] == np.arange(len(cur))
            hh = (cur[:, 2] + p[a, 2]) / 2
            ok = mutual & (d[np.arange(len(cur)), a] <= MATCH_HEIGHTS * hh) & (dt > 0)
            if ok.sum() >= 2:
                dx = (cur[ok, 0] - p[a[ok], 0]) / dt
                dy = (cur[ok, 1] - p[a[ok], 1]) / dt
                vx[k] = float(np.mean(dx))
                sp[k] = float(np.mean(np.hypot(dx, dy) / hh[ok]))
        prev = (float(f), cur)
    return frames, med, vx, sp


def signals(
    cam_t: F64, cam_x: F64, pt: F64, px: F64, py: F64, ph: F64, duration_s: float | None = None
) -> dict[str, F64]:
    """The template's channels on the 10 Hz grid.

    `cam_t`, `cam_x`: frame times (s) and the canvas x of the frame centre (reference px; NaN for
    frames without camera pose); `pt`, `px`, `py`, `ph`: people detections sampled at about 2 Hz,
    time, canvas foot position and canvas height (reference px)."""
    end = float(duration_s if duration_s is not None else (cam_t[-1] if len(cam_t) else 0.0))
    n = max(1, int(np.ceil(end / DT)))
    tg = np.arange(n, dtype=np.float64) * DT
    ok = np.isfinite(cam_x)
    if ok.sum() >= 2:
        cx_cam = np.interp(cam_t, cam_t[ok], cam_x[ok])
        dt = np.diff(cam_t, prepend=cam_t[0] - (cam_t[1] - cam_t[0] if len(cam_t) > 1 else DT))
        step = median3(np.diff(cx_cam, prepend=cx_cam[0]))  # a cut jumps for one frame only
        pan = smooth(bin_mean(cam_t, step / np.maximum(dt, 1e-3), n), 0.3)
    else:
        pan = np.zeros(n)
    keep = (ph >= MIN_BOX_PX) & ~static_mask(pt, px, py)
    frames, med, vx, sp = people_motion(pt, px, py, ph, keep)
    cx = _interp(tg, frames, med, 1.0)
    out: dict[str, F64] = {
        "t": tg,
        "pan": np.asarray(pan, dtype=np.float64),
        "cx_v": np.asarray(np.gradient(cx, DT) - pan if n > 1 else np.zeros(n), dtype=np.float64),
        "vx": _interp(tg, frames, vx, 1.0) - pan,
        "speed": _interp(tg, frames, sp, 1.0),
    }
    return out


# --- score ---------------------------------------------------------------------------------------


def windows(
    ch: F64, at: NDArray[np.int_], window_s: tuple[float, float], sign_cols: tuple[int, ...]
) -> F64:
    """The channels from `window_s[0]` to `window_s[1]` around each grid index in `at`
    (edge-padded), windows x samples x channels. The signed channels of a window are flipped
    together so that their sum after t is positive: a goal happens in either direction."""
    n = len(ch)
    i0 = round(window_s[0] / DT)
    m = round((window_s[1] - window_s[0]) / DT)
    after = round(window_s[1] / DT)
    idx = np.clip(np.asarray(at)[:, None] + i0 + np.arange(m)[None, :], 0, n - 1)
    w = ch[idx]
    if sign_cols:
        sign = list(sign_cols)
        flip = w[:, m - after :, :][:, :, sign].sum(axis=(1, 2)) < 0
        w[np.ix_(flip, np.arange(m), sign)] *= -1
    return np.asarray(w, dtype=np.float64)


def template_series(ch: F64, tmpl: Template, step: int = 2) -> F64:
    """Cosine similarity of each window (`windows`) with the template, every `step` grid
    points and interpolated in between."""
    n = len(ch)
    tpv = (tmpl.profile - tmpl.profile.mean()).ravel()
    tnorm = float(np.linalg.norm(tpv)) + 1e-9
    at = np.arange(0, n, step)
    vals = np.empty(len(at))
    for s in range(0, len(at), 2048):  # windows in chunks: bounded memory on long games
        w = windows(ch, at[s : s + 2048], tmpl.window_s, tmpl.sign_cols)
        w = w.reshape(len(w), -1)
        w = w - w.mean(axis=1, keepdims=True)
        vals[s : s + 2048] = (w @ tpv) / (np.linalg.norm(w, axis=1) * tnorm + 1e-9)
    return np.asarray(np.interp(np.arange(n), at, vals), dtype=np.float64)


def activity(s: dict[str, F64]) -> F64:
    """People speed relative to the median, with the part that follows the camera speed taken
    out (a fast pan blurs and misplaces the boxes): least-squares fit on |pan|."""
    sp, ap = s["speed"], np.abs(s["pan"])
    a = np.column_stack([np.ones_like(ap), ap])
    coef, *_ = np.linalg.lstsq(a, sp, rcond=None)
    med = max(float(np.median(sp)), 1e-6)
    return np.asarray(np.clip((sp - coef[1] * ap) / med, 0, 10), dtype=np.float64)


def lull_series(s: dict[str, F64], tmpl: Template) -> F64:
    """Busy play around t, then a long lull: log ratio of activity plus camera speed in the busy
    window to the quiet one. After a goal the players celebrate, walk back and wait for the
    throw-off; after a turnover or a save the play goes straight on."""
    act = activity(s)
    pan = np.abs(s["pan"]) / _robust_scale(s["pan"])
    v = act + pan
    n = len(v)
    c = np.r_[0.0, np.cumsum(v)]
    idx = np.arange(n)
    b0, b1 = (round(x / DT) for x in tmpl.lull_busy_s)
    q0, q1 = (round(x / DT) for x in tmpl.lull_quiet_s)

    def mean(a: NDArray[np.int_], b: NDArray[np.int_]) -> F64:
        a, b = np.clip(a, 0, n), np.clip(b, 0, n)
        return np.asarray((c[b] - c[a]) / np.maximum(b - a, 1), dtype=np.float64)

    busy = mean(idx + b0, idx + b1)
    quiet = np.where(idx + q0 < n, mean(idx + q0, idx + q1), busy)
    return np.asarray(np.log((busy + 0.2) / (quiet + 0.2)), dtype=np.float64)


def channels(s: dict[str, F64], names: tuple[str, ...]) -> F64:
    """The named signals as columns, standardised over the rolling window."""
    return rolling_standardise(np.column_stack([s[c] for c in names]))


def score(s: dict[str, F64], tmpl: Template) -> F64:
    ch = channels(s, tmpl.channels)
    return rolling_rz(template_series(ch, tmpl)) + rolling_rz(lull_series(s, tmpl))


# --- play ----------------------------------------------------------------------------------------


def running_mean(x: F64, win_s: float) -> F64:
    """Mean over a centred window of `win_s`, clipped at the ends."""
    n = len(x)
    m = min(n, max(1, round(win_s / DT)))
    c = np.r_[0.0, np.cumsum(x)]
    i = np.arange(n)
    lo = np.clip(i - m // 2, 0, n)
    hi = np.clip(i - m // 2 + m, 0, n)
    return np.asarray((c[hi] - c[lo]) / np.maximum(hi - lo, 1), dtype=np.float64)


def no_play(s: dict[str, F64], moving: bool) -> NDArray[np.bool_]:
    """True where nobody plays as far as the camera tells: an operated camera that stands still
    (below `STILL_PX_S`) for `STILL_SHARE` of a centred `STILL_WINDOW_S` window. During play the
    operator follows the ball across the court at least every minute or two; at half-time and
    before or after the game the camera is parked. Time-outs (60 s) are too short to tell from a
    long attack filmed by a parked camera, and a fixed camera is always still: never flagged."""
    n = len(s["t"])
    if not moving or n == 0:
        return np.zeros(n, bool)
    still = (np.abs(s["pan"]) < STILL_PX_S).astype(np.float64)
    return np.asarray(running_mean(still, STILL_WINDOW_S) >= STILL_SHARE, dtype=bool)


def intervals(t: F64, mask: NDArray[np.bool_]) -> list[tuple[float, float]]:
    """[start, end) times of the runs of True."""
    if not mask.any():
        return []
    d = np.diff(np.r_[0, mask.astype(np.int8), 0])
    starts, ends = np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]
    return [(float(t[a]), float(t[b - 1]) + DT) for a, b in zip(starts, ends, strict=True)]


# --- candidates ----------------------------------------------------------------------------------


def pick(
    t: F64,
    sc: F64,
    rates: tuple[int, ...] = RATES,
    block_s: float = BLOCK_S,
    step: int = 2,
    play: NDArray[np.bool_] | None = None,
) -> list[Candidate]:
    """The best peaks per block: `max(rates)` per minute of play in each block, greedy in score
    order with `NMS_S` suppression (also against the blocks before), none within `EDGE_S` of the
    ends and none outside `play` (default: everywhere). The candidates of a lower rate are the
    first ones of a higher rate."""
    if len(t) == 0:
        return []
    end = float(t[-1])
    ts, ss = t[::step], sc[::step]
    valid = (ts >= t[0] + EDGE_S) & (ts <= end - EDGE_S)
    playing = np.ones(len(t), bool) if play is None else np.asarray(play, bool)
    valid &= playing[::step]
    out: list[Candidate] = []
    top = max(rates)
    start = 0.0
    while start < end:
        stop = min(end, start + block_s)
        if end - stop < 0.25 * block_s:  # a short rest joins the last block
            stop = end
        minutes = float(playing[(t >= start) & (t < stop)].sum()) * DT / 60
        quota = {r: round(r * minutes) for r in rates}
        inside = np.nonzero(valid & (ts >= start) & (ts < stop + (1e-9 if stop == end else 0)))[0]
        got: list[Candidate] = []
        for i in inside[np.argsort(-ss[inside], kind="stable")]:
            if len(got) >= quota[top]:
                break
            if all(abs(ts[i] - c.t) > NMS_S for c in (*out, *got)):
                rank = len(got)
                rate = next(r for r in sorted(rates) if rank < quota[r])
                got.append(Candidate(float(ts[i]), float(ss[i]), rate, rank))
        out.extend(got)
        start = stop
    return sorted(out, key=lambda c: c.t)


def candidates(
    s: dict[str, F64], tmpl: Template | None = None, moving: bool = True
) -> list[Candidate]:
    tmpl = tmpl or load_template()
    return pick(s["t"], score(s, tmpl), play=~no_play(s, moving))


# --- from the observation pass -------------------------------------------------------------------


def _reference_focal(motion: Any) -> float:
    """Focal length of the reference frame (`REF_WIDTH` wide, at the median zoom) in px."""
    fw = float(motion.frame_size[0]) or REF_WIDTH
    focal = float(np.median(motion.focals)) if motion.focals else fw
    return focal * REF_WIDTH / fw


def _camera_x(motion: Any, n_frames: int) -> F64:
    """Pan of every frame's optical axis in reference px: its azimuth on the canvas times the
    reference focal length (NaN for frames without camera pose; 0 for a fixed camera).

    An angle, not the planar canvas x: on the planar canvas a degree of pan is stretched by
    1 / cos^2 of the azimuth (about 3x at 55 degrees, where club cameras look at the goals) and
    explodes near 90 degrees."""
    if not motion.moving:
        return np.zeros(n_frames)
    rots = motion.rotations
    out = np.full(n_frames, np.nan)
    have = [i for i in range(min(n_frames, len(rots))) if rots[i] is not None]
    if have:
        axes = np.stack([np.asarray(rots[i], np.float64)[2] for i in have])  # optical axes (world)
        cam = axes @ np.asarray(motion.ref_r, np.float64).T  # in canvas camera coordinates
        out[have] = np.arctan2(cam[:, 0], cam[:, 2]) * _reference_focal(motion)
    return out


def _canvas_to_reference(motion: Any, pts: F64) -> F64:
    """Canvas px -> reference px on the same cylinder as `_camera_x` (x: azimuth, y: elevation,
    both times the reference focal length); a fixed camera's frame is only scaled."""
    if not motion.moving:
        return np.asarray(pts * (REF_WIDTH / (float(motion.frame_size[0]) or REF_WIDTH)))
    f = max(float(motion.canvas_f), 1e-6)
    u = pts[:, 0] - motion.canvas_c[0]
    v = pts[:, 1] - motion.canvas_c[1]
    fref = _reference_focal(motion)
    return np.column_stack([np.arctan2(u, f) * fref, v / np.hypot(u, f) * fref])


def inputs_from_observations(obs: Any) -> tuple[F64, F64, F64, F64, F64, F64, float]:
    """Camera track and 2 Hz people samples of an `observe.Observations`, in reference px."""
    fps = float(obs.fps) or 25.0
    n_frames = max(int(obs.total), (obs.frames[-1].index + 1) if obs.frames else 0)
    cam_x = _camera_x(obs.motion, n_frames)
    cam_t = np.arange(n_frames) / fps
    motion = obs.motion
    ts, xs, ys, hs = [], [], [], []
    next_t = 0.0
    for fo in obs.frames:
        t = fo.index / fps
        if t < next_t - 0.5 * (1 / fps) or not fo.people:
            continue
        next_t = max(next_t + PEOPLE_DT, t + 0.5 * PEOPLE_DT)
        h = motion.frame_to_canvas(fo.index)
        if h is None:
            continue
        boxes = np.array([(d.x1, d.y1, d.x2, d.y2) for d in fo.people], np.float64)
        cx = (boxes[:, 0] + boxes[:, 2]) / 2
        pts = (
            np.column_stack(
                [np.r_[cx, cx], np.r_[boxes[:, 3], boxes[:, 1]], np.ones(2 * len(boxes))]
            )
            @ np.asarray(h, np.float64).T
        )
        pts = _canvas_to_reference(motion, pts[:, :2] / pts[:, 2:3])
        feet, heads = pts[: len(boxes)], pts[len(boxes) :]
        ts.append(np.full(len(boxes), t))
        xs.append(feet[:, 0])
        ys.append(feet[:, 1])
        hs.append(np.hypot(*(feet - heads).T))

    def cat(v: list[F64]) -> F64:
        return np.asarray(np.concatenate(v) if v else np.zeros(0), dtype=np.float64)

    return cam_t, cam_x, cat(ts), cat(xs), cat(ys), cat(hs), n_frames / fps


def from_observations(obs: Any, tmpl: Template | None = None) -> dict[str, Any] | None:
    """Goal candidates for the analysis payload, or None when the video is too short or the
    detector saw (almost) nobody."""
    t0 = time.perf_counter()
    tmpl = tmpl or load_template()
    cam_t, cam_x, pt, px, py, ph, duration = inputs_from_observations(obs)
    if duration < MIN_DURATION_S or len(np.unique(pt)) < 20:
        return None
    s = signals(cam_t, cam_x, pt, px, py, ph, duration)
    idle = no_play(s, bool(obs.motion.moving))
    found = pick(s["t"], score(s, tmpl), play=~idle)
    return {
        "template": tmpl.version,
        "default_rate": DEFAULT_RATE,
        "rates": list(RATES),
        "duration_s": round(duration, 1),
        "play_s": round(float((~idle).sum()) * DT, 1),
        "no_play_ms": [[round(a * 1000), round(b * 1000)] for a, b in intervals(s["t"], idle)],
        "clip_s": [-CLIP_BEFORE_S, CLIP_AFTER_S],
        "candidates": [c.to_dict(duration) for c in found],
        "elapsed_s": round(time.perf_counter() - t0, 2),
    }
