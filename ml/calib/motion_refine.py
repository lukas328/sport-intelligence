"""Experiment: correct the camera rotations on the marking frames so their floor lines agree.

The floor markings of one frame lie along two floor directions far better (median 40 to 66 % of
the line length) than the markings of all frames together (15 to 33 %): the camera motion is about
a degree off between frames, and `auto_calibrate` stops at "no clear floor". Here each marking
frame gets a small rotation (at most `max_deg`, in canvas coordinates) that brings its segment
normals onto the common floor directions; the floor orientation and the corrections are estimated
in turns. The corrections are interpolated over the frames in between (rotation vectors, linear in
the frame index) and written into the motion, so the hall image, the court and every later frame
use the corrected motion.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages/vision"))

from handball_vision import observe as ob  # noqa: E402
from handball_vision import topview  # noqa: E402


def _rotvec_to_mat(v: np.ndarray) -> np.ndarray:
    return cv2.Rodrigues(np.asarray(v, np.float64).reshape(3, 1))[0]


def _dirs(alpha: float, beta: float, yaw: float) -> tuple[np.ndarray, np.ndarray]:
    u = topview._up(alpha, beta)
    ref = np.array([0.0, 0.0, 1.0]) - u * u[2]
    e1 = ref / np.linalg.norm(ref)
    e2 = np.cross(u, e1)
    d1 = np.cos(yaw) * e1 + np.sin(yaw) * e2
    return d1, np.cross(u, d1)


def _frame_cost(m: np.ndarray, w: np.ndarray, d1: np.ndarray, d2: np.ndarray, tol: float) -> float:
    r = np.minimum(np.abs(m @ d1), np.abs(m @ d2))
    return float((w * np.minimum(r / tol, 1.0) ** 2).sum())


def refine_rotations(
    obs: ob.Observations, max_deg: float = 3.0, rounds: int = 3, tol_deg: float = 1.0
) -> dict[str, Any]:
    """Correct `obs.motion` in place; returns fit before / after and the corrections."""
    motion = obs.motion
    if not motion.moving:
        return {"skipped": "fixed camera"}
    static = obs.static if motion.stats.get("pan_deg", 0.0) >= 15 else None
    frames: dict[int, tuple[np.ndarray, np.ndarray]] = {}
    for idx, raw in obs.segments.items():
        rot = ob._to_canvas_rot(motion, idx)
        seg = ob.drop_static(raw, static) if static is not None else raw
        if rot is None or len(seg) < 15:
            continue
        frames[idx] = topview.segment_normals(seg, ob._frame_k(motion, idx), rot)
    if len(frames) < 3:
        return {"skipped": "too few marking frames"}
    total = sum(float(v[1].sum()) for v in frames.values())
    tol = np.sin(np.radians(tol_deg))
    corr = {i: np.zeros(3) for i in frames}

    def all_normals() -> tuple[np.ndarray, np.ndarray]:
        ms = [frames[i][0] @ _rotvec_to_mat(corr[i]).T for i in frames]
        return np.vstack(ms), np.concatenate([frames[i][1] for i in frames])

    m0, l0 = all_normals()
    before = topview.orientation_from_normals(m0, l0)
    orient = before
    lim = np.radians(max_deg)
    for _ in range(rounds):
        d1, d2 = _dirs(*orient[:3])
        for i, (m, length) in frames.items():
            w = length / total
            v = corr[i].copy()
            best = _frame_cost(m @ _rotvec_to_mat(v).T, w, d1, d2, tol)
            step = np.radians(1.0)
            while step > np.radians(0.05):
                improved = False
                for ax in range(3):
                    for sgn in (-1, 1):
                        t = v.copy()
                        t[ax] = np.clip(t[ax] + sgn * step, -lim, lim)
                        c = _frame_cost(m @ _rotvec_to_mat(t).T, w, d1, d2, tol)
                        if c < best - 1e-12:
                            best, v, improved = c, t, True
                if not improved:
                    step /= 2
            corr[i] = v
        m1, l1 = all_normals()
        orient = topview.orientation_from_normals(m1, l1)
    # write the corrections into the motion (interpolated between marking frames)
    keys = sorted(corr)
    vecs = np.array([corr[k] for k in keys])
    n = len(motion.rotations)
    for f in range(n):
        r = motion.rotations[f]
        if r is None:
            continue
        v = np.array([np.interp(f, keys, vecs[:, a]) for a in range(3)])
        rd = _rotvec_to_mat(v)
        # canvas rotation ref_r @ r.T becomes rd @ ref_r @ r.T
        motion.rotations[f] = r @ motion.ref_r.T @ rd.T @ motion.ref_r
    motion.panorama = None  # the hall image must be rendered again
    deg = np.degrees(np.linalg.norm(vecs, axis=1))
    return {
        "fit_before": round(before[3], 3),
        "fit_after": round(orient[3], 3),
        "corr_deg_median": round(float(np.median(deg)), 2),
        "corr_deg_max": round(float(deg.max()), 2),
        "frames": len(keys),
    }
