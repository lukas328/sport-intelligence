"""Goal-moment cues per time step from the cached clip passes (`extract.py`).

All cues live on one grid (0.2 s steps) over clip time; windows look `BEFORE` s back and `AFTER`
s ahead, so the grid stays inside the clip (`GRID`). Coordinates are 1280-wide image pixels; the
camera-compensated "canvas" adds the accumulated pan.

Whole-frame cues (no ball, no model):
- `pan_after`: how far the camera swings in the `AFTER` seconds (after a goal it pans back to
  the centre for the throw-off);
- `pan_rev`: opposite swings before and after (camera followed the attack, then turns round);
  geometric mean of the two opposite displacements;
- `still_swing`: a quiet camera before (positional attack, the shot) and a swing after;
- `energy_drop`: compensated motion energy before / after (players stop, jog back);
- `cut`: scene cut / replay (phase-correlation response collapses), broadcast only;
- `zone_leave`: share of goal-area paint in view before minus after (camera leaves the goal).

Ball cues (3-frame net + balltrack path):
- `ball_fast`: highest path speed (canvas px/s) in the `BEFORE` window (the shot);
- `ball_fast_lost`: a fast path segment that ends, followed by no ball for >= 1 s (the ball
  disappears in the goal / net);
- `ball_zone`: the last fast path point lies in the goal area (6 m zone paint; hall-specific
  colour, see `zone_masks`).

People cues (YOLOX every 0.5 s):
- `people_flow`: mean horizontal speed of people (canvas px/s) after vs before; after a goal
  everybody runs the same way (back) - one team towards its own half.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "packages/vision"))
from handball_vision import balltrack as bt  # noqa: E402

STEP_S = 0.2
BEFORE, AFTER = 2.0, 2.0
ZONE_HUE = (36, 52)  # green goal area of this hall (OpenCV hue 0..180)
GRID = (0.5, 7.0)  # clip seconds; logged goal time is at 6.0 in goal clips (windows truncate)


def grid() -> np.ndarray:
    return np.round(np.arange(GRID[0], GRID[1] + 1e-6, STEP_S), 3)


def _window(x: np.ndarray, fps: float, t: float, a: float, b: float) -> np.ndarray:
    i0, i1 = max(0, int((t + a) * fps)), min(len(x), int((t + b) * fps))
    return x[i0:i1]


def ball_path(z: Any) -> tuple[np.ndarray, dict[str, int]]:
    """Ball path as array (t_s, x_canvas, y_canvas, observed) on the ball-net time grid."""
    fps, step = float(z["fps"]), int(z["ball_step"])
    pk = z["peaks"]
    peaks = [bt.Peak(int(p[0]) // step, float(p[3]), float(p[4]), float(p[5])) for p in pk]
    if not peaks:
        return np.zeros((0, 4)), {}
    path, stats = bt.track(peaks, fps / step, max_speed=1280 * 0.9, radius=1280 / 160,
                           min_score=0.35, max_gap=3)
    arr = np.array([(p.frame * step / fps, p.x, p.y, p.score > 0) for p in path], float)
    return arr.reshape(-1, 4), stats


def ball_speed(path: np.ndarray) -> np.ndarray:
    if len(path) < 2:
        return np.zeros(len(path))
    dt = np.diff(path[:, 0])
    v = np.hypot(np.diff(path[:, 1]), np.diff(path[:, 2])) / np.maximum(dt, 1e-6)
    v[dt > 0.3] = 0  # across a chain gap: no speed
    return np.concatenate([[0.0], v])


def zone_masks(z: Any) -> np.ndarray:
    """Goal-area paint per thumbnail (320x180). Hall-specific: in this hall the 6 m zone is green
    (OpenCV hue `ZONE_HUE`); many halls only draw a line, then this cue is unavailable."""
    out = []
    for t in z["thumbs"]:
        hsv = cv2.cvtColor(t, cv2.COLOR_BGR2HSV)
        m = (hsv[..., 0] >= ZONE_HUE[0]) & (hsv[..., 0] <= ZONE_HUE[1]) & (hsv[..., 1] > 50)
        m &= hsv[..., 2] > 50
        m[int(0.84 * 180):] = False  # overlay band
        out.append(m)
    return np.array(out)


def compute(z: Any) -> dict[str, np.ndarray]:
    """Cue name -> value per grid step."""
    fps = float(z["fps"])
    pan = z["pan"][:, 0].astype(float) * fps  # px/s, horizontal
    energy = z["energy"].astype(float)
    resp = z["resp"].astype(float)
    tg = grid()
    out: dict[str, list[float]] = {k: [] for k in (
        "pan_after", "pan_rev", "still_swing", "energy_drop", "cut", "zone_leave",
        "ball_fast", "ball_fast_lost", "ball_zone", "people_flow")}
    path, _ = ball_path(z)
    speed = ball_speed(path)
    pe = z["people"]
    offs = z["offs"]
    zm = zone_masks(z)
    zt = z["thumb_idx"] / fps
    zshare = zm.mean(axis=(1, 2))
    zdil = np.array([cv2.dilate(m.astype(np.uint8), np.ones((7, 7), np.uint8)) for m in zm])
    # people: median canvas x per detection frame
    pflow_t, pflow_x = [], []
    for f in np.unique(pe[:, 0]).astype(int) if len(pe) else []:
        m = pe[:, 0] == f
        cx = (pe[m, 1] + pe[m, 3]) / 2 + offs[f, 0]
        pflow_t.append(f / fps)
        pflow_x.append(np.median(cx))
    pflow_t, pflow_x = np.array(pflow_t), np.array(pflow_x)
    for t in tg:
        vb = _window(pan, fps, t, -BEFORE, 0).mean()  # mean pan speed px/s
        va = _window(pan, fps, t, 0, AFTER).mean()
        out["pan_after"].append(abs(va))
        out["pan_rev"].append(float(np.sqrt(max(0.0, -vb * va))))
        quiet = np.abs(_window(pan, fps, t, -1.0, 0)).mean()
        out["still_swing"].append(abs(va) / (1.0 + quiet / 100))
        eb = _window(energy, fps, t, -BEFORE, 0).mean()
        ea = _window(energy, fps, t, 0, AFTER).mean()
        out["energy_drop"].append(float(np.log((eb + 0.1) / (ea + 0.1))))
        out["cut"].append(float(1 - _window(resp, fps, t, -1.0, 1.0).min()))
        zb = zshare[(zt >= t - BEFORE) & (zt < t)]
        za = zshare[(zt >= t) & (zt < t + AFTER)]
        out["zone_leave"].append(float(zb.mean() - za.mean()) * 100 if len(zb) and len(za) else 0.0)
        fast = lost = in_zone = 0.0
        if len(path):
            mb = (path[:, 0] >= t - BEFORE) & (path[:, 0] < t)
            fast = speed[mb].max() if mb.any() else 0.0
            # last fast path point before t; the ball is not seen for a while after (in the net)
            fast_idx = np.where(mb & (speed > 600))[0]
            if len(fast_idx):
                last = fast_idx[-1]
                t_end = path[last:, 0][np.r_[np.diff(path[last:, 0]) > 0.3, True]][0]
                nxt = path[path[:, 0] > t_end + 1e-6]
                gap = (nxt[0, 0] - t_end) if len(nxt) else 9.0 - t_end
                lost = float(speed[last] * min(gap, 2.0) / 2.0)
                k = int(np.argmin(np.abs(zt - path[last, 0])))
                f = int(round(path[last, 0] * fps))
                xi = (path[last, 1] - offs[f, 0]) / 4
                yi = (path[last, 2] - offs[f, 1]) / 4
                if 0 <= xi < 320 and 0 <= yi < 180 and zdil[k, int(yi), int(xi)]:
                    in_zone = float(speed[last])
        out["ball_fast"].append(float(fast))
        out["ball_fast_lost"].append(lost)
        out["ball_zone"].append(in_zone)
        if len(pflow_t) > 3:
            b = (pflow_t >= t - BEFORE) & (pflow_t < t)
            a = (pflow_t >= t) & (pflow_t <= t + AFTER)
            vb = np.polyfit(pflow_t[b], pflow_x[b], 1)[0] if b.sum() >= 2 else 0.0
            va = np.polyfit(pflow_t[a], pflow_x[a], 1)[0] if a.sum() >= 2 else 0.0
            out["people_flow"].append(float(np.sqrt(max(0.0, -vb * va)) + 0.5 * abs(va)))
        else:
            out["people_flow"].append(0.0)
    return {k: np.array(v) for k, v in out.items()}


PROFILE_DT = 0.1
PROFILE_WIN = (-2.0, 3.0)  # seconds around the time step


def profile_channels(z: Any) -> np.ndarray:
    """(T, 3) at 10 Hz: horizontal pan speed (px/s / 100), goal-area share (%), motion energy."""
    fps = float(z["fps"])
    n = int(z["n"])
    pan = z["pan"][:, 0].astype(float) * fps / 100
    energy = z["energy"].astype(float)
    zm = zone_masks(z).mean(axis=(1, 2)) * 100
    zt = z["thumb_idx"] / fps
    ts = np.arange(0, n / fps, PROFILE_DT)
    step = int(fps * PROFILE_DT)
    p = np.array([pan[int(t * fps):int(t * fps) + step].mean() for t in ts])
    e = np.array([energy[int(t * fps):int(t * fps) + step].mean() for t in ts])
    zs = np.interp(ts, zt, zm)
    return np.column_stack([p, zs, e])


def profile_at(ch: np.ndarray, t: float) -> np.ndarray:
    """Window of the channels around t (edge-padded), pan sign-normalised so that the camera
    swings in the positive direction after t."""
    i0 = round((t + PROFILE_WIN[0]) / PROFILE_DT)
    n = round((PROFILE_WIN[1] - PROFILE_WIN[0]) / PROFILE_DT)
    idx = np.clip(np.arange(i0, i0 + n), 0, len(ch) - 1)
    w = ch[idx].copy()
    after = w[-round(PROFILE_WIN[1] / PROFILE_DT):, 0].mean()
    if after < 0:
        w[:, 0] = -w[:, 0]
    return w
