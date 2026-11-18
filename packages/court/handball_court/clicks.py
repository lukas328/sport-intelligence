"""Court calibration from clicked lines and points (manual calibration, line mode).

On panning club cameras few named court points are in view, and labelling by named points was
slow and ambiguous (calibration test set, docs/plans/kalibrierung.md, round 1). Clicking lines is
quicker: choose a court line (sidelines, goal lines, centre line, 6 m and 9 m lines) and click two
or more points anywhere on it; named points (corners, post feet, marks) may be added.

The court -> image homography is fitted to both: a named point by its distance to the projected
point, a line click by its distance to the projected line (arcs included). On a pan end the
straight lines often fix only 6 of the 8 degrees of freedom (both sidelines and one goal line; a
corner on two of them adds nothing): the clicks on the arcs decide. So the start is searched:
the linear equations (a point gives two, a click on a straight line one) leave up to three
directions open, which are searched on a grid and refined (Nelder-Mead) for the court that
explains all clicks; then a robust least-squares fit from the best starts.

A result counts only when the clicks agree with one court: median distance <= 5 px and at most
20 px for any click; clicks beyond 15 px (a click on a neighbouring line) may be dropped, one at
a time, at most a fifth of them. With fewer than 10 equations the clicks cannot be checked
against each other and are refused. Same method as the truth of the calibration test set
(`ml/calib/clicks.py`), without lens distortion.

Pure numpy and scipy (extra "clicks" of this package), so the API can check clicks without the
vision stack; `handball_vision.courtclicks` wraps the result as a `Calibration`.
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import least_squares, minimize

from handball_court.geometry import COURT

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


_DENSE = {k: _dense(v, 0.1) for k, v in LINES.items()}
_COARSE = {k: v[::3] for k, v in _DENSE.items()}  # 30 cm: enough to rank starts

MIN_EQUATIONS = 10  # 8 unknowns and a check
MAX_MEDIAN_PX = 5.0
MAX_CLICK_PX = 20.0
DROP_PX = 15.0


class ClicksError(ValueError):
    """The clicks give no court. `code`: "unknown" (a name not in KEYPOINTS or LINES),
    "too_few" (too few clicks to check them against each other), "disagree" (no court explains
    all clicks)."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class Click:
    """One click: a named point (index -1) or the index-th click on a line."""

    kind: str  # "point" or "line"
    name: str
    index: int = -1


@dataclass
class ClicksFit:
    """The court through the clicks (court metres -> image px) and how well the clicks agree."""

    homography: F64
    residual_px: list[float] = field(default_factory=list)  # per used click, points first
    dropped: list[Click] = field(default_factory=list)  # clicks left out as off-line

    @property
    def median_px(self) -> float:
        return float(np.median(self.residual_px)) if self.residual_px else 0.0

    @property
    def max_px(self) -> float:
        return float(max(self.residual_px)) if self.residual_px else 0.0


def _project(h: F64, pts: F64) -> F64:
    q = np.c_[pts, np.ones(len(pts))] @ h.T
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.asarray(q[:, :2] / q[:, 2:3], np.float64)


def _residuals(
    h: F64, points: dict[str, Px], lines: dict[str, list[Px]], dense: dict[str, F64] | None = None
) -> F64:
    """Distance of every click to the projected court (points first). A straight court line stays
    straight in the image: exact point-to-line distance; arcs: nearest projected sample."""
    out: list[float] = []
    if points:
        src = np.array([KEYPOINTS[n] for n in points], np.float64)
        dst = np.array(list(points.values()), np.float64)
        out.extend(np.linalg.norm(_project(h, src) - dst, axis=1).tolist())
    curves = dense if dense is not None else _DENSE
    for name, clicks in lines.items():
        c = np.array(clicks, np.float64)
        if len(LINES[name]) == 2:
            a, b = _project(h, LINES[name])
            d = b - a
            n = float(np.hypot(d[0], d[1]))
            if not np.isfinite(n) or n < 1e-9:
                out.extend([1e6] * len(c))
                continue
            out.extend((np.abs(d[0] * (c[:, 1] - a[1]) - d[1] * (c[:, 0] - a[0])) / n).tolist())
            continue
        curve = _project(h, curves[name])
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
            grid = [np.array([a]) for a in np.linspace(0, np.pi, 120, endpoint=False)]
        else:
            grid = [
                np.array([a, b])
                for a in np.linspace(0, np.pi, 30, endpoint=False)
                for b in np.linspace(0, 2 * np.pi, 60, endpoint=False)
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


# court metres to roughly [-1, 1]: the solver then sees well scaled parameters
_NORM = np.array([[1 / 20, 0, -1], [0, 1 / 10, -1], [0, 0, 1]])
_NORM_INV = np.linalg.inv(_NORM)


def _fit(points: dict[str, Px], lines: dict[str, list[Px]], starts: list[F64]) -> tuple[F64, F64]:
    best: tuple[float, F64, F64] | None = None
    for h0 in starts[:2]:
        # H = A (I + D) N with A the start in normalised court units: D starts at zero
        a = h0 @ _NORM_INV
        a = a / np.abs(a).max()

        def hom(d: F64, a: F64 = a) -> F64:
            return np.asarray(a @ (np.eye(3) + np.append(d, 0.0).reshape(3, 3)) @ _NORM)

        def resid(d: F64, hom: Callable[[F64], F64] = hom) -> F64:
            return _residuals(hom(d), points, lines)

        sol = least_squares(
            resid, np.zeros(8), method="trf", loss="soft_l1", f_scale=5.0, max_nfev=400
        )
        if best is None or sol.cost < best[0]:
            h = hom(sol.x)
            best = (float(sol.cost), h / h[2, 2], resid(sol.x))
    assert best is not None
    return best[1], best[2]


def fit_clicks(
    points: dict[str, Px], lines: dict[str, list[Px]], image_size: tuple[int, int]
) -> ClicksFit:
    """The court from named points and clicks on court lines (image px).

    `points` maps keypoint names (`KEYPOINTS`) to a pixel, `lines` maps line names (`LINES`)
    to two or more pixels on that line. Raises ClicksError when the clicks are too few to be
    checked or do not agree with one court."""
    unknown = [n for n in points if n not in KEYPOINTS] + [n for n in lines if n not in LINES]
    if unknown:
        raise ClicksError("unknown", f"unknown court points or lines: {', '.join(unknown)}")
    pts = {n: (float(p[0]), float(p[1])) for n, p in points.items()}
    # every line click keeps its index in the request, so a dropped one can be named
    lns = {n: [(j, (float(p[0]), float(p[1]))) for j, p in enumerate(c)] for n, c in lines.items()}
    lns = {n: c for n, c in lns.items() if c}

    def plain(lc: dict[str, list[tuple[int, Px]]]) -> dict[str, list[Px]]:
        return {n: [p for _, p in c] for n, c in lc.items()}

    def n_eq(p: dict[str, Px], lc: dict[str, list[tuple[int, Px]]]) -> int:
        return 2 * len(p) + sum(len(c) for c in lc.values())

    if n_eq(pts, lns) < MIN_EQUATIONS or len(pts) + len(lns) < 3:
        raise ClicksError(
            "too_few",
            "too few clicks to check them against each other: click at least two lines with "
            "two or three points each and a third line or two named points",
        )
    starts = _starts(pts, plain(lns), image_size)
    if not starts:
        raise ClicksError("disagree", "the clicks give no court")
    h, res = _fit(pts, plain(lns), starts)
    dropped: list[Click] = []
    max_drop = max(1, len(res) // 5)

    def bad_fit(r: F64) -> bool:
        return bool(np.median(r) > MAX_MEDIAN_PX or r.max() > MAX_CLICK_PX)

    # a click that snapped to a neighbouring line: drop the worst click beyond 15 px and fit
    # again, one at a time, at most a fifth of the clicks
    while bad_fit(res) and len(dropped) < max_drop and res.max() > DROP_PX:
        keys = [Click("point", n) for n in pts] + [
            Click("line", n, j) for n, c in lns.items() for j, _ in c
        ]
        worst = keys[int(np.argmax(res))]
        trial_pts = {
            n: p for n, p in pts.items() if not (worst.kind == "point" and n == worst.name)
        }
        trial_lns = {
            n: [
                (j, p)
                for j, p in c
                if not (worst.kind == "line" and n == worst.name and j == worst.index)
            ]
            for n, c in lns.items()
        }
        trial_lns = {n: c for n, c in trial_lns.items() if c}
        if n_eq(trial_pts, trial_lns) < MIN_EQUATIONS:
            break
        pts, lns = trial_pts, trial_lns
        h, res = _fit(pts, plain(lns), [h])
        dropped.append(worst)
    med, mx = float(np.median(res)), float(res.max())
    if med > MAX_MEDIAN_PX or mx > MAX_CLICK_PX:
        raise ClicksError(
            "disagree",
            f"the clicks do not agree with one court (median {med:.1f} px, worst {mx:.1f} px): "
            "check that every click sits on the chosen handball line",
        )
    return ClicksFit(
        np.asarray(h / h[2, 2], np.float64), [round(float(x), 2) for x in res], dropped
    )


def court_model(arc_step_m: float = 0.5) -> dict[str, Any]:
    """The clickable court for a client: lines as polylines and named points, court metres."""
    out_lines: dict[str, Any] = {}
    for name, c in LINES.items():
        if len(c) == 2:
            out_lines[name] = {"kind": "line", "court": c.tolist()}
        else:
            d = _dense(c, arc_step_m)
            out_lines[name] = {"kind": "arc", "court": np.round(d, 3).tolist()}
    return {"lines": out_lines, "points": {k: list(v) for k, v in KEYPOINTS.items()}}
