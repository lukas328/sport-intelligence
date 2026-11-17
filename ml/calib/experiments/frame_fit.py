"""Feasibility probe (2026-11-18): the court of one frame fitted directly to the frame's lines.

The product finds the court through a top view of all marking frames (floor orientation from the
line directions, scale from the players, template search). That fails on low cameras (`flat_view`)
and when the camera motion is a degree off between frames (`no_floor`), 15 of the 30 development
pieces (docs/plans/kalibrierung.md 4.2, 4.8). Here each frame is calibrated on its own:

- camera model: position C (x, y, z in court metres), look-at point on the floor (tx, ty),
  focal length f (start from the camera motion), roll; pinhole, no distortion;
- score: handball court lines (6 and 9 m arcs included) projected into the frame land on the
  frame's line pixels (`clicks.line_mask_png`, Gaussian of the distance, sigma 3 px, summed over
  the court samples, so a court that shows more of itself scores more);
- players: the detector's boxes of the nearest detection frame; a foot on the floor seen from the
  camera must have its head 1.75 m up where the box top is (relative error), and the feet must lie
  on the court;
- search: a grid of camera positions beside and behind the court and look-at points (about 1 600
  starts), the best 25 refined (Nelder-Mead), the best kept;
- acceptance, fixed before looking at the truth: share of the court samples in the frame that sit
  on a line pixel (within 3 px) >= 0.5, median player-height error <= 0.15, >= 80 % of the feet on
  the court, camera 1.5 to 25 m up and beside or behind the court.

    uv run --project packages/vision python ml/calib/experiments/frame_fit.py CACHE TRUTH OUT_JSON [--ids c001 ...]

Writes per truth frame the fitted floor homography (frame px -> court m) and its acceptance; the
evaluation against the truth is in `report()` (also run at the end).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from scipy.optimize import minimize

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[2] / "packages/vision"))

import clicks  # noqa: E402
import evaluate  # noqa: E402

PERSON_M = 1.75
SIGMA_PX = 3.0
COURT = np.vstack([v[:: max(1, len(v) // 160)] for v in clicks.DENSE.values()])  # ~0.25 m steps


def rotation(c: np.ndarray, t: np.ndarray, roll: float) -> np.ndarray:
    """World (court, z up) -> camera (x right, y down, z forward), looking from c at t."""
    fwd = t - c
    fwd = fwd / np.linalg.norm(fwd)
    right = np.cross(fwd, [0.0, 0.0, 1.0])
    n = np.linalg.norm(right)
    right = np.array([1.0, 0.0, 0.0]) if n < 1e-09 else right / n
    down = np.cross(fwd, right)
    r = np.vstack([right, down, fwd])
    cr, sr = np.cos(roll), np.sin(roll)
    return np.array([[cr, -sr, 0], [sr, cr, 0], [0, 0, 1.0]]) @ r


def unpack(v: np.ndarray, size: tuple[int, int]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    c = v[0:3]
    t = np.array([v[3], v[4], 0.0])
    f = float(np.exp(v[5]))
    r = rotation(c, t, v[6])
    k = np.array([[f, 0, size[0] / 2], [0, f, size[1] / 2], [0, 0, 1.0]])
    return c, r, k


def project(
    c: np.ndarray, r: np.ndarray, k: np.ndarray, pts3: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    cam = (pts3 - c) @ r.T
    z = cam[:, 2]
    front = z > 0.1
    uv = np.full((len(pts3), 2), -1e6)
    uv[front] = (cam[front, :2] / z[front, None]) @ k[:2, :2].T + k[:2, 2]
    return uv, front


def floor_h(c: np.ndarray, r: np.ndarray, k: np.ndarray) -> np.ndarray:
    """Court floor (x, y, 1) -> frame px."""
    return k @ np.column_stack([r[:, 0], r[:, 1], -r @ c])


class Frame:
    def __init__(self, img: np.ndarray, people: np.ndarray, focal: float):
        self.size = (img.shape[1], img.shape[0])
        mask = clicks.line_mask_png(img)
        self.dt = cv2.distanceTransform(255 - mask, cv2.DIST_L2, 3).astype(np.float32)
        self.people = people  # rows x1, y1, x2, y2
        self.focal = focal
        self.court3 = np.c_[COURT, np.zeros(len(COURT))]

    def terms(self, v: np.ndarray) -> dict[str, float]:
        c, r, k = unpack(v, self.size)
        w, h = self.size
        uv, front = project(c, r, k, self.court3)
        inside = front & (uv[:, 0] >= 0) & (uv[:, 0] < w - 1) & (uv[:, 1] >= 0) & (uv[:, 1] < h - 1)
        d = np.full(len(uv), 99.0)
        if inside.any():
            d[inside] = clicks.truth._sample(self.dt, uv[inside])
        line = float(np.exp(-0.5 * (d / SIGMA_PX) ** 2).sum() / len(uv))
        hit = float((d[inside] <= 3).mean()) if inside.sum() >= 30 else 0.0
        # players: back-project the foot to the floor, put a head 1.75 m above it
        res, on_court = [], []
        if len(self.people):
            hh = floor_h(c, r, k)
            try:
                inv = np.linalg.inv(hh)
            except np.linalg.LinAlgError:
                inv = None
            if inv is not None:
                foot = np.c_[
                    (self.people[:, 0] + self.people[:, 2]) / 2,
                    self.people[:, 3],
                    np.ones(len(self.people)),
                ]
                g = foot @ inv.T
                ok = np.abs(g[:, 2]) > 1e-9
                xy = g[ok, :2] / g[ok, 2:3]
                head3 = np.c_[xy, np.full(len(xy), PERSON_M)]
                huv, hfront = project(c, r, k, head3)
                obs_h = self.people[ok, 3] - self.people[ok, 1]
                rr = np.where(hfront, (huv[:, 1] - self.people[ok, 1]) / np.maximum(obs_h, 1), 1.0)
                res = np.abs(rr)
                on_court = (xy[:, 0] > -2) & (xy[:, 0] < 42) & (xy[:, 1] > -2) & (xy[:, 1] < 22)
        res = np.asarray(res, float)
        people_err = float(np.median(np.minimum(res, 1.0))) if len(res) else 1.0
        on = float(np.mean(on_court)) if len(res) else 0.0
        return {
            "line": line,
            "hit": hit,
            "people_err": people_err,
            "on_court": on,
            "cam_z": float(c[2]),
            "cam_x": float(c[0]),
            "cam_y": float(c[1]),
        }

    def cost(self, v: np.ndarray) -> float:
        if not (0.5 < v[2] < 30 and -0.6 < v[6] < 0.6 and -1.5 < v[5] - np.log(self.focal) < 1.5):
            return 10.0
        t = self.terms(v)
        return -t["line"] * 4.0 + t["people_err"] + 0.5 * (1 - t["on_court"])


def fit_frame(fr: Frame) -> tuple[np.ndarray, dict[str, float]]:
    lf = np.log(fr.focal)
    starts = []
    for cx in (0, 10, 20, 30, 40):
        for cy in (-2, -5, -9, -14, -20):
            for cz in (2.5, 5, 9):
                for tx in (3, 10, 20, 30, 37):
                    for ty in (6, 12):
                        for df in (-0.3, 0.0, 0.3):
                            starts.append(np.array([cx, cy, cz, tx, ty, lf + df, 0.0]))
    # behind-the-goal cameras too
    for cx in (-12, -6, 46, 52):
        for cz in (4, 8):
            for ty in (6, 10, 14):
                for tx in (8, 20, 32):
                    starts.append(np.array([cx, 10.0, cz, tx, ty, lf, 0.0]))
    costs = np.array([fr.cost(s) for s in starts])
    best = None
    for i in np.argsort(costs)[:25]:
        x0 = starts[i]
        simplex = np.vstack([x0, x0 + np.diag([2.0, 2.0, 1.0, 2.0, 2.0, 0.15, 0.05])])
        rr = minimize(
            fr.cost,
            x0,
            method="Nelder-Mead",
            options={"maxiter": 1500, "xatol": 1e-3, "fatol": 1e-5, "initial_simplex": simplex},
        )
        if best is None or rr.fun < best.fun:
            best = rr
    return best.x, fr.terms(best.x)


def accept(t: dict[str, float]) -> bool:
    plausible = 1.5 <= t["cam_z"] <= 25 and (t["cam_y"] < 1 or t["cam_x"] < -1 or t["cam_x"] > 41)
    return plausible and t["hit"] >= 0.5 and t["people_err"] <= 0.15 and t["on_court"] >= 0.8


def nearest_people(obs: Any, frame: int) -> np.ndarray:
    fo = min(obs.frames, key=lambda f: abs(f.index - frame))
    rows = [(d.x1, d.y1, d.x2, d.y2) for d in fo.people if d.score >= 0.5 and (d.y2 - d.y1) >= 25]
    return np.array(rows, float).reshape(-1, 4)


def run_one(args: tuple[str, str, str]) -> dict[str, Any]:
    cache, pid, frame = args
    sys.path.insert(0, str(HERE.parent))
    import run as calib_run

    t0 = time.perf_counter()
    obs, _ = calib_run.load(Path(cache), pid)
    img = cv2.imread(str(Path(cache) / f"{pid}.frames" / f"{int(frame):05d}.jpg"))
    focal = (
        float(obs.motion._k_frame(int(frame))[0, 0]) if obs.motion.moving else float(img.shape[1])
    )
    fr = Frame(img, nearest_people(obs, int(frame)), focal)
    v, t = fit_frame(fr)
    c, r, k = unpack(v, fr.size)
    hh = floor_h(c, r, k)
    f2c = np.linalg.inv(hh)
    return {
        "id": pid,
        "frame": frame,
        "accept": accept(t),
        "terms": {k2: round(x, 3) for k2, x in t.items()},
        "params": v.round(4).tolist(),
        "frame_to_court": (f2c / f2c[2, 2]).tolist(),
        "seconds": round(time.perf_counter() - t0, 1),
        "people": len(fr.people),
    }


def report(
    results: list[dict[str, Any]], truth: dict[str, Any], good_m: float = 1.0
) -> dict[str, Any]:
    """Per frame and per piece: correct / wrong / rejected against the clicked truth."""
    frames, pieces = [], {}
    for r in results:
        e = truth.get(r["id"], {}).get(str(int(r["frame"])))
        tp = evaluate.truth_points(e) if e else None
        if tp is None:
            continue
        err = float(np.median(evaluate.errors_m(r["frame_to_court"], *tp)))
        cls = "rejected" if not r["accept"] else ("correct" if err <= good_m else "wrong")
        frames.append(
            {"id": r["id"], "frame": r["frame"], "err_m": round(err, 2), "cls": cls, **r["terms"]}
        )
        pieces.setdefault(r["id"], []).append((r["accept"], err))
    per_piece = {}
    for pid, lst in pieces.items():
        acc = [e for a, e in lst if a]
        per_piece[pid] = (
            "rejected" if not acc else ("correct" if float(np.median(acc)) <= good_m else "wrong")
        )
    count = lambda xs, k: sum(1 for x in xs if x == k)  # noqa: E731
    fc = [f["cls"] for f in frames]
    pc = list(per_piece.values())
    oracle = sum(1 for f in frames if f["err_m"] <= good_m)
    return {
        "frames": len(frames),
        "frame_classes": {k: count(fc, k) for k in ("correct", "wrong", "rejected")},
        "frames_within_1m_if_all_accepted": oracle,
        "pieces": len(pc),
        "piece_classes": {k: count(pc, k) for k in ("correct", "wrong", "rejected")},
        "rows": frames,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cache")
    ap.add_argument("truth", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--ids", nargs="*")
    ap.add_argument("--jobs", type=int, default=4)
    a = ap.parse_args()
    truth = json.loads(a.truth.read_text())
    todo = [
        (a.cache, pid, fr)
        for pid, fs in sorted(truth.items())
        for fr in fs
        if not a.ids or pid in a.ids
    ]
    with ProcessPoolExecutor(a.jobs) as ex:
        results = list(ex.map(run_one, todo))
    for r in results:
        print(
            r["id"],
            r["frame"],
            "ACCEPT" if r["accept"] else "reject",
            r["terms"],
            r["seconds"],
            "s",
            flush=True,
        )
    rep = report(results, truth)
    a.out.write_text(json.dumps({"results": results, "report": rep}, indent=1) + "\n")
    print(json.dumps({k: v for k, v in rep.items() if k != "rows"}, indent=1))
    for row in rep["rows"]:
        print(
            row["id"],
            row["frame"],
            row["cls"],
            row["err_m"],
            "hit",
            row["hit"],
            "people",
            row["people_err"],
        )


if __name__ == "__main__":
    main()
