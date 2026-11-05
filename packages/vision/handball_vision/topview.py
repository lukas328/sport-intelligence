"""Automatic court calibration via a metric top view (ADR 025).

Multi-sport halls carry several line sets; a court hypothesis built from the wrong lines can explain
many of them in the perspective image. In a metric top view the search is small and handball's
shapes are unmistakable. The pieces, all with the focal length known from the camera motion:

1. **Floor orientation** (`orientation_from_normals`): nearly every marking in a hall runs along one
   of two orthogonal floor directions; segments from many frames (walls and people masked) give the
   floor tilt and roll in the panorama's camera.
2. **Scale** (`camera_height_from_people`): detected people are about 1.75 m tall.
3. **Top view** (`segments_on_floor`, `line_top_view`): segments along the two directions, drawn on
   the floor at 10 px per metre: a clean map of the hall's markings (walls and reflections drop out).
4. **Court search** (`search_court`): the 40 x 20 m template (goal areas weighted) over yaw, position
   and scale, scored by a truncated chamfer match plus where the players stand (on the court, nobody
   behind the goal lines, a goalkeeper cluster in each goal mouth).
5. **Goal frames** (`refine_on_goals`): the court is nudged so that the projected 3D goal frames
   (posts and crossbar, 2 m high) fall on striped red and white paint; several court candidates
   are refined and the best goal fit wins.
6. **Line colours** (`segment_colours`, `colour_views`, `handball_colour`): when the court found
   among the lines of all sports is not trustworthy, each segment gets the colour of the hall
   image's line mask under it, and the colours whose own top view forms the handball court best
   (outline, centre line, 6 m and 9 m lines) are searched on their own.
7. **Flat views** (`view_depression_deg`): players seen at a median of less than about 10 degrees
   below the horizon (low or distant cameras) make the top view too sensitive to small errors in
   the floor orientation; calibration then stops early and asks for clicked points.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np
from numpy.typing import NDArray

from handball_vision import geometry
from handball_vision.calibration import (
    LINE_COLOURS,
    MODEL_POINTS,
    CalibrationError,
    line_masks,
)

F64 = NDArray[np.float64]
U8 = NDArray[Any]

PERSON_M = 1.75


def _rays(k: F64, pts: F64) -> F64:
    hom = np.column_stack([pts, np.ones(len(pts))])
    r = (np.linalg.inv(k) @ hom.T).T
    return np.asarray(r / np.linalg.norm(r, axis=1, keepdims=True), dtype=np.float64)


def _up(alpha: float, beta: float) -> F64:
    """Up vector in camera coordinates for a camera tilted down by `alpha` and rolled by `beta`."""
    ca, sa, cb, sb = np.cos(alpha), np.sin(alpha), np.cos(beta), np.sin(beta)
    rx = np.array([[1, 0, 0], [0, ca, -sa], [0, sa, ca]])
    rz = np.array([[cb, -sb, 0], [sb, cb, 0], [0, 0, 1]])
    return np.asarray(rx @ rz @ np.array([0.0, -1.0, 0.0]), dtype=np.float64)


def _floor_segments(image: U8, seen: U8) -> F64:
    """Line segments of floor markings (x1, y1, x2, y2) in the hall image."""
    masks = line_masks(image)
    union: U8 = np.zeros(seen.shape, np.uint8)
    for m in masks.values():
        union = cv2.bitwise_or(union, m)
    union[seen == 0] = 0
    lines = cv2.HoughLinesP(union, 1, np.pi / 720, 40, minLineLength=35, maxLineGap=4)
    if lines is None:
        return np.zeros((0, 4))
    return np.asarray(lines.reshape(-1, 4), dtype=np.float64)


def segment_rays(seg: F64, k: F64, rot: F64 | None = None) -> tuple[F64, F64]:
    """Unit rays of both segment ends in the reference camera."""
    ra, rb = _rays(k, seg[:, :2]), _rays(k, seg[:, 2:])
    if rot is not None:
        ra, rb = ra @ rot.T, rb @ rot.T
    return ra, rb


def floor_basis(up: F64, yaw: float) -> tuple[F64, F64]:
    """The two floor line directions for a floor orientation and yaw."""
    ref = np.array([0.0, 0.0, 1.0]) - up * up[2]
    e1 = ref / np.linalg.norm(ref)
    e2 = np.cross(up, e1)
    d1 = np.cos(yaw) * e1 + np.sin(yaw) * e2
    return d1, np.cross(up, d1)


def segments_on_floor(
    ra: F64, rb: F64, up: F64, height: float, yaw: float, tol_deg: float = 2.0, max_m: float = 60.0
) -> tuple[F64, F64]:
    """Segment ends on the floor in metres along the two hall directions (d1, d2), keeping only
    segments that run along one of them (markings; walls and people do not)."""
    d1, d2 = floor_basis(up, yaw)
    da, db = ra @ up, rb @ up
    ok = (da < -1e-3) & (db < -1e-3)
    pa = ra[ok] * (-height / da[ok])[:, None]
    pb = rb[ok] * (-height / db[ok])[:, None]
    a = np.column_stack([pa @ d1, pa @ d2])
    b = np.column_stack([pb @ d1, pb @ d2])
    v = b - a
    ang = np.degrees(np.arctan2(np.abs(v[:, 1]), np.abs(v[:, 0])))
    aligned = (ang < tol_deg) | (ang > 90 - tol_deg)
    near = (np.abs(a).max(axis=1) < max_m) & (np.abs(b).max(axis=1) < max_m)
    keep = aligned & near
    return a[keep], b[keep]


def rays_to_pixels(k: F64, rays: F64) -> F64:
    """Image pixels of unit rays (NaN behind the camera)."""
    p = rays @ k.T
    with np.errstate(divide="ignore", invalid="ignore"):
        px = p[:, :2] / p[:, 2:3]
    px[p[:, 2] <= 1e-6] = np.nan
    return np.asarray(px, dtype=np.float64)


def segment_colours(
    masks: dict[str, U8], a: F64, b: F64, min_share: float = 0.6, samples: int = 9
) -> NDArray[np.int_]:
    """Line colour of each segment (end points `a`, `b` in the pixels of the image the colour
    `masks` come from): the index into LINE_COLOURS of the mask that covers most of it, or -1
    when no mask covers `min_share` of it (walls, people, reflections). The masks are widened by
    2 px: the segments come from sharp single frames, the masks from the median hall image."""
    n = len(a)
    if n == 0:
        return np.zeros(0, dtype=np.int_)
    hh, ww = next(iter(masks.values())).shape[:2]
    t = np.linspace(0.1, 0.9, samples)
    p = a[:, None, :] + (b - a)[:, None, :] * t[None, :, None]
    p = np.where(np.isfinite(p), p, -1.0)
    inside = (p[..., 0] >= 0) & (p[..., 0] < ww) & (p[..., 1] >= 0) & (p[..., 1] < hh)
    xi = np.clip(p[..., 0], 0, ww - 1).astype(np.intp)
    yi = np.clip(p[..., 1], 0, hh - 1).astype(np.intp)
    shares = np.zeros((n, len(LINE_COLOURS)))
    kernel = np.ones((5, 5), np.uint8)
    for c, name in enumerate(LINE_COLOURS):
        if name not in masks:
            continue
        wide = cv2.dilate(masks[name], kernel) > 0
        shares[:, c] = (wide[yi, xi] & inside).mean(axis=1)
    best = shares.argmax(axis=1)
    return np.where(shares.max(axis=1) >= min_share, best, -1).astype(np.int_)


def colour_views(
    ra: F64,
    rb: F64,
    colours: NDArray[np.int_],
    up: F64,
    height: float,
    yaw: float,
    min_segments: int = 60,
    min_share: float = 0.1,
) -> dict[str, TopView]:
    """One top view per line colour that has enough floor segments of its own (at least
    `min_segments` and `min_share` of the coloured floor segments): multi-sport halls draw each
    sport in its own colour, and a view of one colour shows one sport's shapes."""
    floor: dict[str, tuple[F64, F64]] = {}
    for c, name in enumerate(LINE_COLOURS):
        sel = colours == c
        if sel.sum() < min_segments:
            continue
        floor[name] = segments_on_floor(ra[sel], rb[sel], up, height, yaw)
    total = sum(len(a) for a, _ in floor.values())
    return {
        name: line_top_view(a, b)
        for name, (a, b) in floor.items()
        if len(a) >= max(min_segments, min_share * total)
    }


def handball_colour(views: dict[str, TopView]) -> list[tuple[str, float]]:
    """Line colours ranked by how well their top view forms the handball court (40 x 20 m
    outline, centre line, 6 m and 9 m lines; goal areas weighted): the best court match of the
    lines alone. Basketball (28 x 15 m), volleyball (18 x 9 m) and badminton markings explain
    only parts of the template."""
    ranked = []
    for name, tv in views.items():
        found = search_court(tv, weights=((0.0, 0.0),))
        ranked.append((name, max(s for _, s in found)))
    return sorted(ranked, key=lambda r: -r[1])


def view_depression_deg(up: F64, height: float, feet_rays: F64) -> float:
    """Median angle below the horizon at which the camera sees the players' feet: below about
    10 degrees the floor is seen so flatly that small errors in the floor orientation move the
    far half of the court by metres (low cameras, cameras far away)."""
    down = -(feet_rays @ up)
    down = down[down > 1e-3]
    if len(down) == 0:
        return 0.0
    return float(np.degrees(np.arcsin(np.clip(np.median(down), 0.0, 1.0))))


def same_court(t1: F64, t2: F64, tol_px: float) -> bool:
    """Two court placements (court metres -> top-view pixels) that put the court corners within
    `tol_px` of each other."""
    corners = np.array([[0.0, 0.0], [40.0, 0.0], [40.0, 20.0], [0.0, 20.0]])
    d = np.linalg.norm(geometry.apply(t1, corners) - geometry.apply(t2, corners), axis=1)
    return bool(d.max() < tol_px)


def line_top_view(a: F64, b: F64, ppm: float = 10.0, margin_m: float = 3.0) -> TopView:
    """Top view drawn from floor segments (thin lines), with the extent they cover as `seen`."""
    pts = np.vstack([a, b])
    lo = np.percentile(pts, 0.5, axis=0) - margin_m
    hi = np.percentile(pts, 99.5, axis=0) + margin_m
    size = (int((hi[0] - lo[0]) * ppm) + 1, int((hi[1] - lo[1]) * ppm) + 1)
    mask = np.zeros((size[1], size[0]), np.uint8)
    pa = ((a - lo) * ppm).round().astype(np.int32)
    pb = ((b - lo) * ppm).round().astype(np.int32)
    for p, q in zip(pa, pb, strict=True):
        cv2.line(mask, (int(p[0]), int(p[1])), (int(q[0]), int(q[1])), 255, 1)
    hull = cv2.convexHull(np.vstack([pa, pb]))
    seen = np.zeros_like(mask)
    cv2.fillConvexPoly(seen, hull, 255)
    return TopView(mask, seen, (float(lo[0]), float(lo[1])), ppm, np.eye(3))


def segment_normals(seg: F64, k: F64, rot: F64 | None = None) -> tuple[F64, F64]:
    """Plane normals of segments (through the camera centre) and their lengths; `rot` turns the
    frame's rays into the reference camera (the panorama's)."""
    ra, rb = _rays(k, seg[:, :2]), _rays(k, seg[:, 2:])
    if rot is not None:
        ra, rb = ra @ rot.T, rb @ rot.T
    m = np.cross(ra, rb)
    m /= np.linalg.norm(m, axis=1, keepdims=True)
    return m, np.hypot(seg[:, 2] - seg[:, 0], seg[:, 3] - seg[:, 1])


def frame_segments(
    frame: U8, boxes: list[tuple[float, float, float, float]], top_share: float = 0.3
) -> F64:
    """Floor marking segments in one frame: below the top part (walls, banners), outside people."""
    seen = np.full(frame.shape[:2], 255, np.uint8)
    seen[: int(frame.shape[0] * top_share)] = 0
    for x1, y1, x2, y2 in boxes:
        cv2.rectangle(seen, (int(x1) - 3, int(y1) - 3), (int(x2) + 3, int(y2) + 3), 0, -1)
    return _floor_segments(frame, seen)


def orientation_from_normals(m: F64, length: F64) -> tuple[float, float, float, float]:
    """Floor tilt, roll and the yaw of the two line directions from segment plane normals.

    Nearly all markings in a hall run along two orthogonal floor directions; a floor direction d
    lies in a segment's plane when m . d = 0. Returns (alpha, beta, yaw, fit share).
    """
    if len(m) < 30:
        raise CalibrationError("too few floor lines")
    wts = length / length.sum()
    tol = np.sin(np.radians(1.0))

    def cost(alpha: float, beta: float, yaw: float) -> float:
        u = _up(alpha, beta)
        ref = np.array([0.0, 0.0, 1.0]) - u * u[2]
        e1 = ref / np.linalg.norm(ref)
        e2 = np.cross(u, e1)
        d1 = np.cos(yaw) * e1 + np.sin(yaw) * e2
        d2 = np.cross(u, d1)
        r = np.minimum(np.abs(m @ d1), np.abs(m @ d2))
        return float((wts * np.minimum(r / tol, 1.0) ** 2).sum())

    best = (np.inf, 0.0, 0.0, 0.0)
    for a in np.radians(np.arange(2, 70, 1.0)):
        for b in np.radians(np.arange(-6, 6.1, 3.0)):
            for y in np.radians(np.arange(0, 90, 3.0)):
                c = cost(a, b, y)
                if c < best[0]:
                    best = (c, a, b, y)
    _, a0, b0, y0 = best
    step = np.radians(1.0)
    for _ in range(5):
        for da in (-1, 0, 1):
            for db in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    c = cost(a0 + da * step, b0 + db * step, y0 + dy * step)
                    if c < best[0]:
                        best = (c, a0 + da * step, b0 + db * step, y0 + dy * step)
        _, a0, b0, y0 = best
        step /= 2
    c, a, b, y = best
    return float(a), float(b), float(y), 1.0 - c


def camera_height_from_people(
    up: F64, feet: F64, heads: F64, k: F64, person_m: float = PERSON_M
) -> float:
    """Camera height for a known floor orientation: the median over people of the height that
    makes each a `person_m` tall upright person."""
    rf, rh = _rays(k, feet), _rays(k, heads)
    down = rf @ up
    valid = down < -1e-3
    units = []
    for f, h, dn in zip(rf[valid], rh[valid], down[valid], strict=True):
        xf = f * (-1.0 / dn)
        sol, *_ = np.linalg.lstsq(np.column_stack([up, -h]), -xf, rcond=None)
        if sol[0] > 0.02:
            units.append(sol[0])
    if len(units) < 20:
        raise CalibrationError("too few people to scale the floor")
    height = person_m / float(np.median(units))
    if not 1.0 <= height <= 40.0:
        raise CalibrationError(f"implausible camera height {height:.1f} m")
    return height


def _weights(points: F64) -> F64:
    """Goal areas (within 9.5 m of a goal) count three times: handball's own shapes."""
    near_goal = (points[:, 0] < 9.5) | (points[:, 0] > 30.5)
    return np.where(near_goal, 3.0, 1.0)


@dataclass
class TopView:
    mask: U8  # line pixels
    seen: U8  # pixels the camera showed
    origin: tuple[float, float]  # floor metres at pixel (0, 0)
    ppm: float  # pixels per metre
    floor_to_image: F64

    def to_px(self, floor_m: F64) -> F64:
        return np.asarray((floor_m - np.array(self.origin)) * self.ppm, dtype=np.float64)

    def pixel_to_floor(self) -> F64:
        """Homography top-view pixel -> floor metres."""
        ox, oy = self.origin
        return np.array([[1 / self.ppm, 0, ox], [0, 1 / self.ppm, oy], [0, 0, 1]])


def _dominant_angles(mask: U8) -> list[float]:
    lines = cv2.HoughLinesP(mask, 1, np.pi / 360, 60, minLineLength=40, maxLineGap=6)
    if lines is None:
        return [0.0, np.pi / 2]
    seg = lines.reshape(-1, 4).astype(np.float64)
    ang = np.arctan2(seg[:, 3] - seg[:, 1], seg[:, 2] - seg[:, 0]) % (np.pi / 2)
    length = np.hypot(seg[:, 2] - seg[:, 0], seg[:, 3] - seg[:, 1])
    hist, edges = np.histogram(ang, bins=90, range=(0, np.pi / 2), weights=length)
    hist = np.convolve(np.r_[hist[-2:], hist, hist[:2]], np.ones(5) / 5, mode="same")[2:-2]
    a = float(edges[int(np.argmax(hist))] + (edges[1] - edges[0]) / 2)
    return [a, a + np.pi / 2]


CANDIDATE_WEIGHTS: tuple[tuple[float, float], ...] = (
    (0.0, 0.0),
    (0.6, 0.0),
    (1.0, 0.0),
    (0.3, 4.0),
    (0.6, 4.0),
    (1.0, 4.0),
)


def _people_parts(court: F64) -> tuple[F64, F64, F64]:
    """(on court, behind a goal line, goalkeeper clusters) for feet in court metres (..., n, 2)."""
    x, y = court[..., 0], court[..., 1]
    inside = ((x >= -0.5) & (x <= 40.5) & (y >= -0.5) & (y <= 20.5)).mean(axis=-1)
    behind = (((x < -1.0) | (x > 41.0)) & (y > 3) & (y < 17)).mean(axis=-1)

    def mouth(gx: float) -> F64:
        return np.asarray((np.hypot(x - gx, y - 10.0) < 3.0).mean(axis=-1), dtype=np.float64)

    return (
        np.asarray(inside, dtype=np.float64),
        np.asarray(behind, dtype=np.float64),
        np.minimum(mouth(1.3), mouth(38.7)),
    )


def search_court(
    tv: TopView,
    scales: F64 | None = None,
    feet_px: F64 | None = None,
    weights: tuple[tuple[float, float], ...] = CANDIDATE_WEIGHTS,
) -> list[tuple[F64, float]]:
    """Court placements in the top view, one per (people weight, keeper weight): each a 3x3 court
    metres -> top-view pixel transform and its score.

    Score: truncated chamfer match of the court lines (goal areas weighted) plus, with `feet_px`
    (players' feet over the match, top-view pixels), how well the players fit the court (on it,
    nobody behind the goal lines, goalkeepers in the goal mouths). The line and people parts are
    computed once per hypothesis and combined for every weighting: several candidates for the
    price of one search."""
    dist = cv2.distanceTransform(255 - tv.mask, cv2.DIST_L2, 3)
    tau = 0.6 * tv.ppm
    seen = tv.seen > 0
    hh, ww = dist.shape
    pts = MODEL_POINTS[::2]
    wts = _weights(pts)
    centred = pts - np.array([20.0, 10.0])
    scales = scales if scales is not None else np.linspace(0.85, 1.15, 13)
    best: list[tuple[float, F64]] = [(-1e9, np.eye(3)) for _ in weights]

    def score(p: F64) -> F64:
        """p: (..., n, 2) pixel positions -> line score per hypothesis."""
        xi = np.clip(p[..., 0].round().astype(int), 0, ww - 1)
        yi = np.clip(p[..., 1].round().astype(int), 0, hh - 1)
        inside = (p[..., 0] >= 0) & (p[..., 0] < ww) & (p[..., 1] >= 0) & (p[..., 1] < hh)
        vis = inside & seen[yi, xi]
        d = np.minimum(dist[yi, xi], tau)
        good = (1 - d / tau) * vis
        return np.asarray((good * wts).sum(axis=-1) / wts.sum(), dtype=np.float64)

    feet = None if feet_px is None or len(feet_px) == 0 else np.asarray(feet_px, dtype=np.float64)
    if feet is not None and len(feet) > 4000:
        feet = feet[np.random.default_rng(0).choice(len(feet), 4000, replace=False)]

    def combine(line: F64, parts: tuple[F64, F64, F64] | None, w: tuple[float, float]) -> F64:
        if parts is None:
            return line
        inside, behind, keepers = parts
        return line + w[0] * (inside - 2.0 * behind + w[1] * keepers)

    def total(t: F64, w: tuple[float, float]) -> float:
        line = score(geometry.apply(t, pts)[None])
        parts = None
        if feet is not None:
            parts = _people_parts(geometry.apply(geometry.invert(t), feet)[None])
        return float(combine(line, parts, w)[0])

    ys, xs = np.nonzero(seen)
    cx_range = (xs.min(), xs.max())
    cy_range = (ys.min(), ys.max())
    for theta in _dominant_angles(tv.mask):
        c, s = np.cos(theta), np.sin(theta)
        rot = np.array([[c, -s], [s, c]])
        for sc in scales:
            shape = centred @ rot.T * sc * tv.ppm  # court around its centre, in pixels
            step = max(2, int(tv.ppm))  # 1 m
            gx = np.arange(cx_range[0], cx_range[1], step)
            gy = np.arange(cy_range[0], cy_range[1], step)
            cxs, cys = np.meshgrid(gx, gy)
            centres = np.column_stack([cxs.ravel(), cys.ravel()]).astype(np.float64)
            for start in range(0, len(centres), 256):
                cc = centres[start : start + 256]
                line = score(shape[None, :, :] + cc[:, None, :])
                parts = None
                if feet is not None:
                    # feet in court metres for every centre: rotate back, unscale
                    rel = feet[None, :, :] - cc[:, None, :]
                    parts = _people_parts(rel @ rot / (sc * tv.ppm) + np.array([20.0, 10.0]))
                for wi, w in enumerate(weights):
                    sco = combine(line, parts, w)
                    i = int(np.argmax(sco))
                    if sco[i] > best[wi][0]:
                        t = np.eye(3)
                        t[:2, :2] = rot * sc * tv.ppm
                        t[:2, 2] = cc[i] - (np.array([20.0, 10.0]) @ rot.T) * sc * tv.ppm
                        best[wi] = (float(sco[i]), t)
    out: list[tuple[F64, float]] = []
    for (sc0, t0), w in zip(best, weights, strict=True):
        if sc0 <= -1e8:
            continue
        # local refinement: 0.1 m, 0.25 degree, 1 % steps around the best
        score0 = total(t0, w)
        for _ in range(3):
            improved = False
            for dx, dy, da, ds in (
                (1, 0, 0, 0),
                (-1, 0, 0, 0),
                (0, 1, 0, 0),
                (0, -1, 0, 0),
                (0, 0, 1, 0),
                (0, 0, -1, 0),
                (0, 0, 0, 1),
                (0, 0, 0, -1),
            ):
                for k in (1.0, 0.5, 0.25):
                    cand = _nudge(
                        t0,
                        dx * k * tv.ppm * 0.3,
                        dy * k * tv.ppm * 0.3,
                        da * k * np.radians(0.5),
                        1 + ds * k * 0.01,
                    )
                    val = total(cand, w)
                    if val > score0:
                        score0, t0, improved = val, cand, True
            if not improved:
                break
        out.append((t0, score0))
    if not out:
        raise CalibrationError("no court found in the top view")
    return out


def _nudge(t: F64, dx: float, dy: float, da: float, ds: float) -> F64:
    centre = geometry.apply(t, np.array([[20.0, 10.0]]))[0]
    c, s = np.cos(da), np.sin(da)
    m = np.array([[c * ds, -s * ds, 0], [s * ds, c * ds, 0], [0, 0, 1]])
    shift = np.array([[1, 0, centre[0] + dx], [0, 1, centre[1] + dy], [0, 0, 1]])
    back = np.array([[1, 0, -centre[0]], [0, 1, -centre[1]], [0, 0, 1]])
    return np.asarray(shift @ m @ back @ t, dtype=np.float64)


def pose_from_homography(h: F64, k: F64) -> tuple[F64, F64]:
    """Camera rotation (court -> camera) and translation from a floor homography and known K.
    The third court axis points up (towards the camera)."""
    m = np.linalg.inv(k) @ h
    s = 2.0 / (np.linalg.norm(m[:, 0]) + np.linalg.norm(m[:, 1]))
    if m[2, 2] * s < 0:
        s = -s
    r1, r2, t = m[:, 0] * s, m[:, 1] * s, m[:, 2] * s
    r1 /= np.linalg.norm(r1)
    r2 = r2 - r1 * (r1 @ r2)
    r2 /= np.linalg.norm(r2)
    r3 = np.cross(r1, r2)
    r = np.column_stack([r1, r2, r3])
    # court z must point towards the camera: the camera centre has positive height
    if (-r.T @ t)[2] < 0:
        r = np.column_stack([r1, r2, -r3])
    return r, t


def project_points(r: F64, t: F64, k: F64, pts3: F64) -> F64:
    cam = pts3 @ r.T + t
    p = cam @ k.T
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.asarray(p[:, :2] / p[:, 2:3], dtype=np.float64)


def goal_paint_mask(image: U8) -> U8:
    """Strongly coloured paint (red is by far the most common goal colour; the stripes alternate
    with white)."""
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    return ((((h < 10) | (h > 168)) & (s > 90) & (v > 70)).astype(np.uint8)) * 255


def goal_segments(n: int = 60) -> list[F64]:
    """Each goal's two posts (0 to 2 m) and crossbar as 3D sample lines."""
    out = []
    for gx in (0.0, 40.0):
        for py in (8.5, 11.5):
            z = np.linspace(0.05, 2.0, n)
            out.append(np.column_stack([np.full(n, gx), np.full(n, py), z]))
        y = np.linspace(8.5, 11.5, n)
        out.append(np.column_stack([np.full(n, gx), y, np.full(n, 2.0)]))
    return out


def stripe_score(paint: U8, line_px: F64) -> float:
    """How much a projected post or crossbar looks like a striped goal frame: painted and plain
    parts alternate (about 20 cm each). Solid red walls and plain floor score 0."""
    hh, ww = paint.shape
    ok = np.isfinite(line_px).all(axis=1)
    if ok.sum() < len(line_px) * 0.8:
        return 0.0
    p = line_px[ok]
    if not (
        (p[:, 0] >= 1).all()
        and (p[:, 0] < ww - 1).all()
        and (p[:, 1] >= 1).all()
        and (p[:, 1] < hh - 1).all()
    ):
        return 0.0
    length = float(np.linalg.norm(p[-1] - p[0]))
    if length < 12:  # too small to see stripes
        return 0.0
    n = int(min(200, max(20, length)))
    t = np.linspace(0, 1, n)
    q = p[0] + (p[-1] - p[0]) * t[:, None]
    d = (p[-1] - p[0]) / length
    normal = np.array([-d[1], d[0]])
    vals = np.zeros(n, bool)
    for off in (-1.5, 0.0, 1.5):
        qi = (q + normal * off).round().astype(int)
        qx, qy = np.clip(qi[:, 0], 0, ww - 1), np.clip(qi[:, 1], 0, hh - 1)
        vals |= paint[qy, qx] > 0
    frac = float(vals.mean())
    runs = int(np.sum(vals[1:] != vals[:-1]))
    # a post (2 m) has about ten 20 cm stripes, so about nine changes; short images show fewer
    expected = 9.0 if length >= 40 else max(3.0, length / 4.5)
    return float(min(1.0, runs / expected) * max(0.0, 1.0 - abs(frac - 0.5) * 2.2))


def refine_on_goals(
    h: F64, k: F64, image: U8, search_m: float = 2.5, move_penalty: float = 0.04
) -> tuple[F64, float, float]:
    """Move the court (shift, yaw, scale on the floor) so that the projected goal frames fall on
    painted goal posts. Returns (homography, goal score before, goal score after)."""
    paint = goal_paint_mask(image)
    segs = goal_segments()

    def score(hc: F64) -> float:
        r, t = pose_from_homography(hc, k)
        vals = [stripe_score(paint, project_points(r, t, k, sg)) for sg in segs]
        # both goals count: the mean over the six frame parts
        return float(np.mean(vals))

    def moved(dx: float, dy: float, da: float, ds: float) -> F64:
        c, s = np.cos(da), np.sin(da)
        # similarity about the court centre
        m = np.array([[ds * c, -ds * s, 0], [ds * s, ds * c, 0], [0, 0, 1]])
        to_c = np.array([[1, 0, -20], [0, 1, -10], [0, 0, 1.0]])
        back = np.array([[1, 0, 20 + dx], [0, 1, 10 + dy], [0, 0, 1.0]])
        hc = h @ back @ m @ to_c
        return np.asarray(hc / hc[2, 2], dtype=np.float64)

    def penalised(dx: float, dy: float, da: float, ds: float) -> float:
        # the top-view court is already close: large moves need clearly better goals
        shift = np.hypot(dx, dy) + 20 * abs(ds - 1) + 20 * abs(da)
        return score(moved(dx, dy, da, ds)) - move_penalty * shift

    s0 = score(h)
    best = (s0, 0.0, 0.0, 0.0, 1.0)
    for dx in np.arange(-search_m, search_m + 1e-6, 0.5):
        for dy in np.arange(-search_m, search_m + 1e-6, 0.5):
            for da in np.radians([-2.0, -1.0, 0.0, 1.0, 2.0]):
                for ds in (0.94, 0.97, 1.0, 1.03, 1.06):
                    sc = penalised(dx, dy, da, ds)
                    if sc > best[0]:
                        best = (sc, dx, dy, da, ds)
    # fine search around the best
    _, bx, by, ba, bs = best
    for dx in np.arange(bx - 0.5, bx + 0.51, 0.125):
        for dy in np.arange(by - 0.5, by + 0.51, 0.125):
            for da in ba + np.radians([-0.5, 0.0, 0.5]):
                for ds in bs + np.array([-0.02, -0.01, 0.0, 0.01, 0.02]):
                    sc = penalised(dx, dy, da, ds)
                    if sc > best[0]:
                        best = (sc, dx, dy, da, ds)
    _, dx, dy, da, ds = best
    hb = moved(dx, dy, da, ds)
    return hb, s0, score(hb)


def normalise_orientation(h: F64, k: F64) -> F64:
    """Court coordinates as the product uses them: the camera on the near side (y < 0) and the
    goal at x = 0 on the camera's left. The court is symmetric, so the search may return it turned
    by 180 degrees or mirrored; positions stay the same, only the labels of sides and goals change."""
    r, t = pose_from_homography(h, k)
    centre = -r.T @ t
    if centre[1] > 10:  # camera on the y = 20 side: turn the court by 180 degrees
        turn = np.array([[-1.0, 0, 40], [0, -1.0, 20], [0, 0, 1]])
        h = h @ turn
    left, right = geometry.apply(h, np.array([[0.0, 10.0], [40.0, 10.0]]))
    if left[0] > right[0]:  # x = 0 must be on the left of the image: mirror along the length
        mirror = np.array([[-1.0, 0, 40], [0, 1.0, 0], [0, 0, 1]])
        h = h @ mirror
    return np.asarray(h / h[2, 2], dtype=np.float64)
