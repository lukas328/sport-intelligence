"""Truth from the labelling page v2 (`ml/calib/labelling/feld2.html`): named points and lines.

Round 1 asked for named points only; on panning club cameras few of them are in view (the owner,
2026-11-17: "points on the outer lines are missing", "it takes long and is often not clear").
Version 2 adds clicks on lines: choose a court line (sidelines, goal lines, centre line, 6 m and
9 m lines), click two or more points anywhere on it. The court model of a frame (homography plus
radial distortion k1, k2) is fitted to both: a named point by its distance to the projected point,
a line click by its distance to the projected line (arcs included). The truth of a frame is then a
grid of court points (1 m) that the fitted model puts inside the frame, near the clicks.

    python ml/calib/clicks.py items CACHE OUT_DIR [--done TRUTH_JSON] [--prefill ANSWERS_DIR]
    python ml/calib/clicks.py pull ANSWERS_DIR TRUTH_JSON --cache CACHE [--overlays DIR]

A frame counts only when the clicks agree with one model: median distance <= 5 px and at most
20 px for any click (`consistent`); otherwise it is left out and listed. Lens distortion is fitted
only with at least 16 equations (a handful of points with 10 unknowns explains even mislabelled
points). Of the grid only the points the clicks pin down are kept: every click jittered by 2 px
(6 refits), points whose court position moves by more than 0.3 m are dropped.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import sys
from pathlib import Path
from typing import Any

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import truth  # noqa: E402

_FT = math.sqrt(9.0**2 - 8.5**2)
KEYPOINTS: dict[str, tuple[float, float]] = {
    **truth.KEYPOINTS,
    "subst_left_low": (15.5, 0.0),  # substitution marks, 4.5 m from the centre line
    "subst_right_low": (24.5, 0.0),
    "subst_left_high": (15.5, 20.0),
    "subst_right_high": (24.5, 20.0),
    "gk_line_left": (4.0, 10.0),  # 4 m goalkeeper line (15 cm mark)
    "gk_line_right": (36.0, 10.0),
}


def _arc(cx: float, sx: float, r: float, step_deg: float = 1.0) -> np.ndarray:
    """Goal area (r = 6) or free-throw line (r = 9) at the goal line x = cx (sx = +1 left goal)."""
    pts = []
    for a in np.arange(0, 90 + 1e-9, step_deg):
        t = math.radians(a)
        pts.append((cx + sx * r * math.sin(t), 8.5 - r * math.cos(t)))
    for a in np.arange(90, -1e-9, -step_deg):
        t = math.radians(a)
        pts.append((cx + sx * r * math.sin(t), 11.5 + r * math.cos(t)))
    p = np.array(pts)
    return p[(p[:, 1] >= 0) & (p[:, 1] <= 20)]


CURVES: dict[str, np.ndarray] = {
    "side_near": np.array([(0.0, 0.0), (40.0, 0.0)]),
    "side_far": np.array([(0.0, 20.0), (40.0, 20.0)]),
    "goal_left": np.array([(0.0, 0.0), (0.0, 20.0)]),
    "goal_right": np.array([(40.0, 0.0), (40.0, 20.0)]),
    "centre": np.array([(20.0, 0.0), (20.0, 20.0)]),
    "six_left": _arc(0.0, 1.0, 6.0),
    "six_right": _arc(40.0, -1.0, 6.0),
    "nine_left": _arc(0.0, 1.0, 9.0),
    "nine_right": _arc(40.0, -1.0, 9.0),
}


def dense(curve: np.ndarray, step: float = 0.05) -> np.ndarray:
    out = []
    for a, b in itertools.pairwise(curve):
        n = max(2, int(np.linalg.norm(b - a) / step))
        out.append(np.linspace(a, b, n, endpoint=False))
    out.append(curve[-1:])
    return np.vstack(out)


DENSE = {k: dense(v) for k, v in CURVES.items()}


def _project(h: np.ndarray, k: np.ndarray, size: tuple[int, int], pts: np.ndarray) -> np.ndarray:
    q = np.c_[pts, np.ones(len(pts))] @ h.T
    q = q[:, :2] / q[:, 2:3]
    return truth._distort(q, k, size)


def _click_cost(
    hh: np.ndarray,
    points: dict[str, list[float]],
    lines: dict[str, list[list[float]]],
    size: tuple[int, int],
) -> float:
    """Mean distance (px, each capped at 50) of all clicks to the projected court (points and
    lines, arcs too); a median would let a wrong court explain half the clicks."""
    k = np.zeros(2)
    d = []
    with np.errstate(all="ignore"):
        for n, p in points.items():
            if n in KEYPOINTS:
                d.append(
                    float(np.linalg.norm(_project(hh, k, size, np.array([KEYPOINTS[n]]))[0] - p))
                )
        for name, c in lines.items():
            if name in DENSE and len(c):
                curve = _project(hh, k, size, DENSE[name][::4])
                cc = np.array(c, np.float64)
                d.extend(np.sqrt(((cc[:, None] - curve[None]) ** 2).sum(-1)).min(1).tolist())
    d = [min(x, 50.0) if np.isfinite(x) else 50.0 for x in d]
    return float(np.mean(d)) if d else 1e9


def _init_h(
    points: dict[str, list[float]], lines: dict[str, list[list[float]]], size: tuple[int, int]
) -> np.ndarray | None:
    starts = _init_candidates(points, lines, size)
    return starts[0] if starts else None


def _init_candidates(
    points: dict[str, list[float]],
    lines: dict[str, list[list[float]]],
    size: tuple[int, int],
    keep: int = 5,
) -> list[np.ndarray]:
    """Homography court -> image from the clicks, as a start for the nonlinear fit.

    Linear part (DLT on the inverse map G = H^-1): a named point gives two equations, a click on a
    straight court line one. On a pan end this is often short of the 8 the homography needs (both
    sidelines and one goal line fix 6; a corner on two of those lines adds nothing): the clicks on
    the 6 m and 9 m arcs then decide. The null space of the linear system is searched on a grid
    for the court that explains all clicks, arcs included."""
    w, h = size
    tn = np.array([[2 / w, 0, -1], [0, 2 / w, -h / w], [0, 0, 1]])  # image normalisation
    cn = np.array([[1 / 20, 0, -1], [0, 1 / 20, -0.5], [0, 0, 1]])  # court normalisation
    rows = []
    for n, p in points.items():
        if n not in KEYPOINTS:
            continue
        x = cn @ np.array([*KEYPOINTS[n], 1.0])
        u = tn @ np.array([p[0], p[1], 1.0])
        rows.append(np.r_[x[2] * u, np.zeros(3), -x[0] * u])
        rows.append(np.r_[np.zeros(3), x[2] * u, -x[1] * u])
    for name, clicks in lines.items():
        c = CURVES.get(name)
        if c is None or len(c) != 2:
            continue  # arcs only through the search below
        a = cn @ np.array([*c[0], 1.0])
        b = cn @ np.array([*c[1], 1.0])
        ln = np.cross(a, b)  # court line in normalised court coordinates
        for p in clicks:
            u = tn @ np.array([p[0], p[1], 1.0])
            rows.append(np.r_[ln[0] * u, ln[1] * u, ln[2] * u])
    if len(rows) < 4:
        return []
    _, _, vt = np.linalg.svd(np.array(rows), full_matrices=True)

    # how many directions the clicks leave open is not clear-cut with rounded and noisy clicks:
    # the linear solution and the searches over 2 and 3 open directions are all tried, and the
    # clicks decide (arcs included)
    def to_h(g: np.ndarray) -> np.ndarray | None:
        gm = g.reshape(3, 3)
        if abs(np.linalg.det(gm)) < 1e-12:
            return None
        hh = np.linalg.inv(tn) @ np.linalg.inv(gm) @ cn
        return hh / hh[2, 2] if abs(hh[2, 2]) > 1e-12 else None

    from scipy.optimize import minimize

    found: list[tuple[float, np.ndarray]] = []
    h1 = to_h(vt[-1])
    if h1 is not None:
        found.append((_click_cost(h1, points, lines, size), h1))
    for dim in (2, 3):
        basis = vt[9 - dim :][::-1]  # smallest singular directions first

        def g_of(ang: np.ndarray, basis: np.ndarray = basis, dim: int = dim) -> np.ndarray:
            if dim == 2:
                return np.cos(ang[0]) * basis[0] + np.sin(ang[0]) * basis[1]
            return np.cos(ang[0]) * basis[0] + np.sin(ang[0]) * (
                np.cos(ang[1]) * basis[1] + np.sin(ang[1]) * basis[2]
            )

        def cost(ang: np.ndarray, g_of: Any = g_of) -> float:
            hh = to_h(g_of(ang))
            return 1e9 if hh is None else _click_cost(hh, points, lines, size)

        # directions on the unit sphere of the open space (the sign of G does not matter): a
        # grid, then the best grid points refined locally (the arcs make narrow valleys)
        if dim == 2:
            grid = [np.array([a]) for a in np.linspace(0, np.pi, 180, endpoint=False)]
        else:
            grid = [
                np.array([a, b])
                for a in np.linspace(0, np.pi, 45, endpoint=False)
                for b in np.linspace(0, 2 * np.pi, 90, endpoint=False)
            ]
        scored = sorted(((cost(a), a) for a in grid), key=lambda t: t[0])[: 2 * keep]
        for _, a0 in scored:
            r = minimize(
                cost,
                a0,
                method="Nelder-Mead",
                options={"xatol": 1e-5, "fatol": 1e-3, "maxiter": 400},
            )
            hh = to_h(g_of(r.x))
            if hh is not None:
                found.append((float(r.fun), hh))
    found.sort(key=lambda t: t[0])
    out: list[np.ndarray] = []
    for _, hh in found:  # the best few that are not the same court twice
        if all(np.abs(hh - o).max() > 1e-3 * np.abs(o).max() for o in out):
            out.append(hh)
        if len(out) == keep:
            break
    return out


def fit_clicks(
    points: dict[str, list[float]],
    lines: dict[str, list[list[float]]],
    size: tuple[int, int],
    h0: np.ndarray | None = None,
    distortion: bool = True,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Fit court -> image (H, k) to the clicks; returns H, k and the residual per click (px)."""
    from scipy.optimize import least_squares

    starts = [h0] if h0 is not None else _init_candidates(points, lines, size)
    if not starts:
        raise ValueError("clicks give no court")
    pn = [n for n in points if n in KEYPOINTS]
    src = np.array([KEYPOINTS[n] for n in pn], np.float64).reshape(-1, 2)
    dst = np.array([points[n] for n in pn], np.float64).reshape(-1, 2)
    lc = [(name, np.array(c, np.float64)) for name, c in lines.items() if name in DENSE and len(c)]

    def resid(v: np.ndarray) -> np.ndarray:
        hh = np.append(v[:8], 1.0).reshape(3, 3)
        k = v[8:10] if distortion else np.zeros(2)
        out = []
        if len(src):
            out.append(np.linalg.norm(_project(hh, k, size, src) - dst, axis=1))
        for name, c in lc:
            curve = _project(hh, k, size, DENSE[name])
            d = np.sqrt(((c[:, None, :] - curve[None, :, :]) ** 2).sum(-1)).min(1)
            out.append(d)
        reg = [v[8] * 50.0, v[9] * 50.0] if distortion else []
        return np.concatenate([*out, reg])

    best = None
    for h_start in starts:  # several starts: arcs leave local minima
        v0 = np.r_[(h_start / h_start[2, 2]).ravel()[:8], 0.0, 0.0]
        sol = least_squares(
            resid, v0, method="trf", loss="soft_l1", f_scale=5.0, x_scale="jac", max_nfev=2000
        )
        if best is None or sol.cost < best.cost:
            best = sol
    v = best.x
    hh = np.append(v[:8], 1.0).reshape(3, 3)
    k = v[8:10] if distortion else np.zeros(2)
    r = resid(v)
    return hh, k, (r[:-2] if distortion else r)


def court_grid(
    hh: np.ndarray,
    k: np.ndarray,
    size: tuple[int, int],
    clicks: np.ndarray,
    margin_px: float = 60.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Court points (1 m grid) that the model puts inside the frame and near the clicks (inside
    their convex hull grown by `margin_px`): the truth where the clicks support the model."""
    g = np.array([(x, y) for x in range(0, 41) for y in range(0, 21)], np.float64)
    q = np.c_[g, np.ones(len(g))] @ hh.T
    front = q[:, 2] * np.sign(np.median(q[:, 2])) > 0
    px = _project(hh, k, size, g)
    w, h = size
    inside = front & (px[:, 0] >= 0) & (px[:, 0] < w) & (px[:, 1] >= 0) & (px[:, 1] < h)
    hull = cv2.convexHull(clicks.astype(np.float32))
    near = np.array(
        [cv2.pointPolygonTest(hull, (float(p[0]), float(p[1])), True) >= -margin_px for p in px]
    )
    keep = inside & near
    return px[keep], g[keep]


MIN_EQ_DISTORTION = 16
JITTER_RUNS = 6
MAX_TRUTH_SPREAD_M = 0.3


def evaluate_doc(doc: dict[str, Any], size: tuple[int, int]) -> dict[str, Any]:
    """Fit one answer; returns the truth entry (status, consistency, grid, model)."""
    points = {n: p for n, p in (doc.get("points") or {}).items() if n in KEYPOINTS}
    lines = {n: c for n, c in (doc.get("lines") or {}).items() if n in CURVES and len(c)}
    entry: dict[str, Any] = {
        "status": doc.get("status"),
        "points": points,
        "lines": lines,
        "at": doc.get("at"),
        "version": 2,
    }
    if doc.get("status") == "skip":
        return entry
    n_eq = 2 * len(points) + sum(len(c) for c in lines.values())
    if n_eq < 8 or len(points) + len(lines) < 3:
        entry.update(consistent=False, why="too few clicks")
        return entry
    h0 = np.array(doc["h"], np.float64).reshape(3, 3) if doc.get("h") else None
    # lens distortion only with enough clicks to pin it (10 unknowns instead of 8; with a handful
    # of points a distorted model explains even mislabelled points)
    dist = n_eq >= MIN_EQ_DISTORTION
    try:
        hh, k, res = fit_clicks(points, lines, size, h0, distortion=dist)
    except (ValueError, np.linalg.LinAlgError):
        try:
            hh, k, res = fit_clicks(points, lines, size, None, distortion=dist)
        except (ValueError, np.linalg.LinAlgError):
            entry.update(consistent=False, why="no court through the clicks")
            return entry
    med, mx = float(np.median(res)), float(res.max())
    ok = med <= 5.0 and mx <= 20.0
    clicks = np.array([*points.values(), *[p for c in lines.values() for p in c]], np.float64)
    gpx, gcourt = court_grid(hh, k, size, clicks)
    if ok and len(gpx):
        # the truth only where the clicks pin the court: jitter every click by 2 px, refit, and
        # keep the grid points whose court position moves by at most 0.3 m
        rng = np.random.default_rng(0)
        spread = []
        for _ in range(JITTER_RUNS):
            jp = {n: list(np.array(p) + rng.normal(0, 2.0, 2)) for n, p in points.items()}
            jl = {
                n: [list(np.array(p) + rng.normal(0, 2.0, 2)) for p in c] for n, c in lines.items()
            }
            try:
                h2, k2, _ = fit_clicks(jp, jl, size, hh, distortion=dist)
            except (ValueError, np.linalg.LinAlgError):
                continue
            q = truth._undistort(gpx, k2, size)
            g2 = np.c_[q, np.ones(len(q))] @ np.linalg.inv(h2).T
            spread.append(g2[:, :2] / g2[:, 2:3])
        if spread:
            dev = np.linalg.norm(np.array(spread) - gcourt[None], axis=2).max(0)
            gpx, gcourt = gpx[dev <= MAX_TRUTH_SPREAD_M], gcourt[dev <= MAX_TRUTH_SPREAD_M]
    entry.update(
        consistent=bool(ok and len(gpx) >= 4),
        why=None if ok else f"clicks disagree (median {med:.1f} px, max {mx:.1f} px)",
        residual_px={"median": round(med, 1), "max": round(mx, 1)},
        model={"h": hh.tolist(), "k": [float(k[0]), float(k[1])], "size": list(size)},
        grid={"px": np.round(gpx, 1).tolist(), "court": gcourt.tolist()},
    )
    return entry


def overlay(img: np.ndarray, entry: dict[str, Any]) -> np.ndarray:
    out = img.copy()
    m = entry.get("model")
    size = (img.shape[1], img.shape[0])
    if m:
        hh, k = np.array(m["h"]), np.array(m["k"])
        sign = np.sign(np.median((np.c_[np.array([[20.0, 10.0]]), [[1.0]]] @ hh.T)[:, 2]))
        for name in CURVES:
            pts = DENSE[name][::4]
            w = (np.c_[pts, np.ones(len(pts))] @ hh.T)[:, 2] * sign
            q = _project(hh, k, size, pts)
            ok = (w > 0) & (np.abs(q) < 5000).all(1)
            for run in np.split(np.arange(len(q)), np.where(~ok)[0]):
                run = run[ok[run]]
                if len(run) > 1:
                    cv2.polylines(
                        out, [q[run].astype(np.int32)], False, (255, 0, 255), 1, cv2.LINE_AA
                    )
    for p in (entry.get("points") or {}).values():
        cv2.drawMarker(out, (int(p[0]), int(p[1])), (0, 165, 255), cv2.MARKER_TILTED_CROSS, 9, 2)
    for c in (entry.get("lines") or {}).values():
        for p in c:
            cv2.circle(out, (int(p[0]), int(p[1])), 4, (0, 255, 0), 1)
    tag = "ok" if entry.get("consistent") else (entry.get("why") or entry.get("status"))
    cv2.putText(out, str(tag), (10, 30), 0, 0.8, (0, 255, 255), 2)
    return out


def _rows(answers: Path) -> list[dict[str, Any]]:
    rows = []
    for f in sorted(answers.glob("*.json")):
        d = json.loads(f.read_text())
        rows.append({"id": d.get("id", f.stem), "data": d.get("data", d)})
    return rows


def pull(a: argparse.Namespace) -> None:
    truth_doc = json.loads(a.truth.read_text()) if a.truth.exists() else {}
    for row in _rows(a.answers):
        pid, fr = row["id"].rsplit("_", 1)
        img = cv2.imread(str(a.cache / f"{pid}.frames" / f"{int(fr):05d}.jpg"))
        entry = evaluate_doc(row["data"], (img.shape[1], img.shape[0]))
        truth_doc.setdefault(pid, {})[str(int(fr))] = entry
        if a.overlays:
            a.overlays.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(a.overlays / f"{row['id']}.jpg"), overlay(img, entry))
        print(
            row["id"],
            entry["status"],
            entry.get("consistent"),
            entry.get("why") or "",
            entry.get("residual_px", ""),
            len((entry.get("grid") or {}).get("px", [])),
        )
    a.truth.write_text(json.dumps(truth_doc, indent=1) + "\n")


def line_mask_png(img: np.ndarray) -> np.ndarray:
    h, w = img.shape[:2]
    m = np.zeros((h, w), np.uint8)
    for y in range(0, h, 160):
        for x in range(0, w, 160):
            m[y : y + 160, x : x + 160] = truth._line_mask(img[y : y + 160, x : x + 160])
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    return m


def items(a: argparse.Namespace) -> None:
    """Items of round 1b: per dev piece without a consistent truth frame its main frame first
    (middle of the pan, or the fixed camera's frame), the pan ends after all main frames; the
    answers of round 1 prefill their frames."""
    ps = [
        p
        for p in json.loads((HERE / "testset.json").read_text())["pieces"]
        if p["split"] == a.split
    ]
    done = json.loads(a.done.read_text()) if a.done else {}
    good = {pid for pid, fs in done.items() for e in fs.values() if e.get("consistent")}
    prefill = {}
    if a.prefill:
        for row in _rows(a.prefill):
            d = row["data"]
            if d.get("status") != "skip" and d.get("points"):
                prefill[row["id"]] = {"points": d["points"], "lines": d.get("lines") or {}}
    (a.out / "frames").mkdir(parents=True, exist_ok=True)
    first, later = [], []
    for p in ps:
        pid = p["id"]
        frames = sorted(int(f.stem) for f in (a.cache / f"{pid}.frames").glob("*.jpg"))
        if not frames:
            continue
        main = frames[len(frames) // 2]
        rest = [f for f in frames if f != main]
        for fr in [main, *rest]:
            fid = f"{pid}_{fr:05d}"
            img = cv2.imread(str(a.cache / f"{pid}.frames" / f"{fr:05d}.jpg"))
            cv2.imwrite(str(a.out / "frames" / f"{fid}.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 85])
            cv2.imwrite(str(a.out / "frames" / f"{fid}.mask.png"), line_mask_png(img))
            it = {
                "id": fid,
                "pid": pid,
                "frame": fr,
                "img": f"frames/{fid}.jpg",
                "mask": f"frames/{fid}.mask.png",
                "label": p["game"].replace("_", " "),
                "prefill": prefill.get(fid),
            }
            if pid in good:
                continue  # this piece has a consistent frame already
            (first if fr == main else later).append(it)
    out = first + later
    (a.out / "items.json").write_text(json.dumps(out, ensure_ascii=False) + "\n")
    print(len(first), "main frames,", len(later), "pan ends,", len(good), "pieces already done")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("items")
    p.add_argument("cache", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument("--split", default="dev")
    p.add_argument("--done", type=Path)
    p.add_argument("--prefill", type=Path)
    p.set_defaults(fn=items)
    p = sub.add_parser("pull")
    p.add_argument("answers", type=Path)
    p.add_argument("truth", type=Path)
    p.add_argument("--cache", type=Path, required=True)
    p.add_argument("--overlays", type=Path)
    p.set_defaults(fn=pull)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
