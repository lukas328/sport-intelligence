"""Court calibration from clicked lines and points (manual calibration, line mode).

The calibration dialog asks for named court points (`calibration.calibrate_points`). On panning
club cameras few of them are in view, and the owner found labelling by named points slow and
ambiguous (calibration test set, docs/plans/kalibrierung.md, round 1). Clicking lines is quicker:
choose a court line (sidelines, goal lines, centre line, 6 m and 9 m lines) and click two or more
points anywhere on it; named points (corners, post feet, marks) may be added.

The court -> image homography is fitted to both: a named point by its distance to the projected
point, a line click by its distance to the projected line (arcs included). On a pan end the
straight lines often fix only 6 of the 8 degrees of freedom (both sidelines and one goal line; a
corner on two of them adds nothing): the clicks on the arcs decide. So the start is searched:
the linear equations (a point gives two, a click on a straight line one) leave up to three
directions open, which are searched on a grid and refined (Nelder-Mead) for the court that
explains all clicks; then a robust least-squares fit from the best starts.

A result counts only when the clicks agree with one court: median distance <= 5 px and at most
20 px for any click; clicks beyond 15 px (a click on a neighbouring line) may be dropped,
at most a fifth of them. With fewer than 10 equations the clicks cannot be checked against each
other and are refused. Same method as the truth of the calibration test set (`ml/calib/clicks.py`,
without lens distortion, which `Calibration` does not model).
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import least_squares, minimize

from handball_court import COURT
from handball_vision.calibration import Calibration, CalibrationError

F64 = NDArray[np.float64]
Px = tuple[float, float]

_FT = math.sqrt(9.0**2 - 8.5**2)  # where the 9 m line meets the sidelines (x from the goal line)

KEYPOINTS: dict[str, tuple[float, float]] = {
    **COURT.keypoints,
    "free_throw_left_side_low": (_FT, 0.0),
    "free_throw_left_side_high": (_FT, 20.0),
    "free_throw_right_side_low": (40.0 - _FT, 0.0),
    "free_throw_right_side_high": (40.0 - _FT, 20.0),
    "subst_left_low": (15.5, 0.0),  # substitution marks, 4.5 m from the centre line
    "subst_right_low": (24.5, 0.0),
    "subst_left_high": (15.5, 20.0),
    "subst_right_high": (24.5, 20.0),
    "gk_line_left": (4.0, 10.0),  # 4 m goalkeeper mark
    "gk_line_right": (36.0, 10.0),
}


def _arc(cx: float, sx: float, r: float, step_deg: float = 1.0) -> F64:
    """Goal area (r = 6) or free-throw line (r = 9) at the goal line x = cx (sx = +1 left goal)."""
    pts = []
    for a in np.arange(0, 90 + 1e-9, step_deg):
        t = math.radians(float(a))
        pts.append((cx + sx * r * math.sin(t), 8.5 - r * math.cos(t)))
    for a in np.arange(90, -1e-9, -step_deg):
        t = math.radians(float(a))
        pts.append((cx + sx * r * math.sin(t), 11.5 + r * math.cos(t)))
    p = np.array(pts)
    return np.asarray(p[(p[:, 1] >= 0) & (p[:, 1] <= 20)], np.float64)


LINES: dict[str, F64] = {
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


def _dense(curve: F64, step: float = 0.05) -> F64:
    out = []
    for a, b in itertools.pairwise(curve):
        n = max(2, int(np.linalg.norm(b - a) / step))
        out.append(np.linspace(a, b, n, endpoint=False))
    out.append(curve[-1:])
    return np.asarray(np.vstack(out), np.float64)


_DENSE = {k: _dense(v) for k, v in LINES.items()}
_COARSE = {k: v[::4] for k, v in _DENSE.items()}  # 20 cm: enough to rank starts

MIN_EQUATIONS = 10  # 8 unknowns and a check
MAX_MEDIAN_PX = 5.0
MAX_CLICK_PX = 20.0
DROP_PX = 15.0


@dataclass
class ClickFit:
    """The court through the clicks and how well each click agrees with it."""

    calibration: Calibration
    residual_px: list[float] = field(default_factory=list)  # per click, points first
    dropped: int = 0  # clicks left out as off-line


def _project(h: F64, pts: F64) -> F64:
    q = np.c_[pts, np.ones(len(pts))] @ h.T
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.asarray(q[:, :2] / q[:, 2:3], np.float64)


def _residuals(
    h: F64, points: dict[str, Px], lines: dict[str, list[Px]], dense: dict[str, F64] = _DENSE
) -> F64:
    out: list[float] = []
    if points:
        src = np.array([KEYPOINTS[n] for n in points], np.float64)
        dst = np.array(list(points.values()), np.float64)
        out.extend(np.linalg.norm(_project(h, src) - dst, axis=1).tolist())
    for name, clicks in lines.items():
        curve = _project(h, dense[name])
        c = np.array(clicks, np.float64)
        out.extend(np.sqrt(((c[:, None] - curve[None]) ** 2).sum(-1)).min(1).tolist())
    r = np.array(out, np.float64)
    r[~np.isfinite(r)] = 1e6
    return r


def _cost(h: F64, points: dict[str, Px], lines: dict[str, list[Px]]) -> float:
    """Mean click distance, each capped at 50 px (a median would let a wrong court explain half
    the clicks)."""
    r = _residuals(h, points, lines, _COARSE)
    return float(np.minimum(r, 50.0).mean()) if len(r) else 1e9


def _starts(
    points: dict[str, Px], lines: dict[str, list[Px]], size: tuple[int, int], keep: int = 5
) -> list[F64]:
    w, hgt = size
    tn = np.array([[2 / w, 0, -1], [0, 2 / w, -hgt / w], [0, 0, 1]])  # image normalisation
    cn = np.array([[1 / 20, 0, -1], [0, 1 / 20, -0.5], [0, 0, 1]])  # court normalisation
    rows = []
    for n, p in points.items():
        x = cn @ np.array([*KEYPOINTS[n], 1.0])
        u = tn @ np.array([p[0], p[1], 1.0])
        rows.append(np.r_[x[2] * u, np.zeros(3), -x[0] * u])
        rows.append(np.r_[np.zeros(3), x[2] * u, -x[1] * u])
    for name, clicks in lines.items():
        c = LINES[name]
        if len(c) != 2:
            continue  # arcs only through the search below
        ln = np.cross(cn @ np.array([*c[0], 1.0]), cn @ np.array([*c[1], 1.0]))
        for p in clicks:
            u = tn @ np.array([p[0], p[1], 1.0])
            rows.append(np.r_[ln[0] * u, ln[1] * u, ln[2] * u])
    if len(rows) < 4:
        return []
    _, _, vt = np.linalg.svd(np.array(rows), full_matrices=True)
    tn_inv = np.linalg.inv(tn)

    def to_h(g: F64) -> F64 | None:
        gm = g.reshape(3, 3)
        if abs(np.linalg.det(gm)) < 1e-12:
            return None
        h = tn_inv @ np.linalg.inv(gm) @ cn
        return np.asarray(h / h[2, 2], np.float64) if abs(h[2, 2]) > 1e-12 else None

    found: list[tuple[float, F64]] = []
    h1 = to_h(vt[-1])
    if h1 is not None:
        found.append((_cost(h1, points, lines), h1))
    # how many directions the clicks leave open is not clear-cut with noisy clicks: two and
    # three open directions are searched too, the clicks decide
    for dim in (2, 3):
        basis = vt[9 - dim :][::-1]

        def g_of(ang: F64, basis: F64 = basis, dim: int = dim) -> F64:
            if dim == 2:
                return np.asarray(np.cos(ang[0]) * basis[0] + np.sin(ang[0]) * basis[1])
            return np.asarray(
                np.cos(ang[0]) * basis[0]
                + np.sin(ang[0]) * (np.cos(ang[1]) * basis[1] + np.sin(ang[1]) * basis[2])
            )

        def cost(ang: F64, g_of: object = g_of) -> float:
            h = to_h(g_of(ang))  # type: ignore[operator]
            return 1e9 if h is None else _cost(h, points, lines)

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
            h = to_h(g_of(r.x))
            if h is not None:
                found.append((float(r.fun), h))
    found.sort(key=lambda t: t[0])
    out: list[F64] = []
    for _, h in found:  # the best few that are not the same court twice
        if all(np.abs(h - o).max() > 1e-3 * np.abs(o).max() for o in out):
            out.append(h)
        if len(out) == keep:
            break
    return out


def _fit(points: dict[str, Px], lines: dict[str, list[Px]], starts: list[F64]) -> tuple[F64, F64]:
    def resid(v: F64) -> F64:
        return _residuals(np.append(v, 1.0).reshape(3, 3), points, lines)

    best = None
    for h0 in starts:
        sol = least_squares(
            resid,
            (h0 / h0[2, 2]).ravel()[:8],
            method="trf",
            loss="soft_l1",
            f_scale=5.0,
            x_scale="jac",
            max_nfev=2000,
        )
        if best is None or sol.cost < best.cost:
            best = sol
    assert best is not None
    h = np.append(best.x, 1.0).reshape(3, 3)
    return h, resid(best.x)


def calibrate_clicks(
    points: dict[str, Px], lines: dict[str, list[Px]], image_size: tuple[int, int]
) -> ClickFit:
    """Court calibration from named points and clicks on court lines (image px).

    `points` maps keypoint names (`KEYPOINTS`) to a pixel, `lines` maps line names (`LINES`)
    to two or more pixels on that line. Raises CalibrationError (reason "court") when the clicks
    are too few to be checked or do not agree with one court."""
    unknown = [n for n in points if n not in KEYPOINTS] + [n for n in lines if n not in LINES]
    if unknown:
        raise CalibrationError(f"unknown court points or lines: {', '.join(unknown)}")
    lines = {n: list(c) for n, c in lines.items() if len(c)}
    points = dict(points)

    def n_eq() -> int:
        return 2 * len(points) + sum(len(c) for c in lines.values())

    if n_eq() < MIN_EQUATIONS or len(points) + len(lines) < 3:
        raise CalibrationError(
            "too few clicks to check them against each other: click at least two lines with "
            "two or three points each and a third line or two named points"
        )
    starts = _starts(points, lines, image_size)
    if not starts:
        raise CalibrationError("the clicks give no court")
    h, res = _fit(points, lines, starts)
    dropped = 0
    if not (np.median(res) <= MAX_MEDIAN_PX and res.max() <= MAX_CLICK_PX):
        bad = set(np.where(res > DROP_PX)[0].tolist())
        if 0 < len(bad) <= max(1, len(res) // 5):
            keys = [("p", n, -1) for n in points] + [
                ("l", n, j) for n, c in lines.items() for j in range(len(c))
            ]
            drop = {keys[i] for i in bad}
            points = {n: p for n, p in points.items() if ("p", n, -1) not in drop}
            lines = {
                n: [p for j, p in enumerate(c) if ("l", n, j) not in drop] for n, c in lines.items()
            }
            lines = {n: c for n, c in lines.items() if c}
            if n_eq() >= MIN_EQUATIONS:
                h, res = _fit(points, lines, [h])
                dropped = len(bad)
    med, mx = float(np.median(res)), float(res.max())
    if med > MAX_MEDIAN_PX or mx > MAX_CLICK_PX:
        raise CalibrationError(
            f"the clicks do not agree with one court (median {med:.1f} px, worst {mx:.1f} px): "
            "check that every click sits on the chosen handball line"
        )
    calib = Calibration(
        h / h[2, 2],
        confidence=1.0,
        reprojection_px=round(med, 2),
        source="user_correction",
        image_size=image_size,
    )
    return ClickFit(calib, [round(float(x), 2) for x in res], dropped)
