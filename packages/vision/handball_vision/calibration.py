"""Court calibration (BRIEF 7.2 stage 2): image <-> court homography for a fixed camera.

Automatic (source "heuristic"):
1. Median of sampled frames removes moving players (fixed camera); for moving cameras the
   panorama from `motion.py` plays this role.
2. Line masks: bright, low-saturation pixels (white lines on a dark floor), and per colour (white,
   dark, red, blue, yellow, green) the thin structures that differ from the local floor (top-hat /
   black-hat). Multi-sport floors carry many line sets; the handball court picks its colour by the
   best normalised model match.
3. Hough segments are grouped into the four court boundaries (near/far sideline, both goal lines),
   whose intersections give a first homography.
4. Refinement: points sampled on every court line of the model are projected, matched to the
   nearest line pixel (distance transform) and the homography is re-fitted (iterative closest point).
5. Confidence = share of model line points that land on a line pixel; reprojection error in px.
   Masks are compared by that share minus what a mask of the same density explains by chance.

Manual (source "user_correction"): at least four clicked image points with their court keypoints.
A learned keypoint model (BRIEF 7.2) can replace the automatic part behind the same result type.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Any, Literal

import cv2
import numpy as np
from numpy.typing import NDArray

from handball_court import COURT
from handball_vision import geometry

F64 = NDArray[np.float64]


class CalibrationError(Exception):
    pass


@dataclass(frozen=True)
class Calibration:
    homography: F64  # court (m) -> image (px)
    confidence: float
    reprojection_px: float
    source: Literal["heuristic", "user_correction", "synthetic"]
    image_size: tuple[int, int]

    @property
    def inverse(self) -> F64:
        return geometry.invert(self.homography)

    def to_court(self, pts: NDArray[np.floating]) -> F64:
        return geometry.apply(self.inverse, pts)

    def to_image(self, pts: NDArray[np.floating]) -> F64:
        return geometry.apply(self.homography, pts)

    def to_dict(self) -> dict[str, object]:
        return {
            "homography": self.homography.round(8).tolist(),
            "confidence": round(self.confidence, 4),
            "reprojection_px": round(self.reprojection_px, 3),
            "source": self.source,
            "image_size": list(self.image_size),
        }

    @classmethod
    def from_dict(cls, d: dict[str, object]) -> Calibration:
        size = d["image_size"]
        assert isinstance(size, list)
        source = str(d["source"])
        if source not in ("heuristic", "user_correction", "synthetic"):
            raise ValueError(f"unknown calibration source {source}")
        return cls(
            np.array(d["homography"], dtype=np.float64),
            float(str(d["confidence"])),
            float(str(d["reprojection_px"])),
            source,  # type: ignore[arg-type]
            (int(size[0]), int(size[1])),
        )


def model_line_points(step_m: float = 0.25) -> F64:
    """Points sampled along all court lines (metres)."""
    pts: list[F64] = []
    for name, line in COURT.lines.items():
        if name.startswith(("substitution", "gk_line", "penalty_mark", "goal_left", "goal_right")):
            continue
        arr = np.array(line, dtype=np.float64)
        for a, b in itertools.pairwise(arr):
            n = max(2, int(np.linalg.norm(b - a) / step_m))
            pts.append(np.linspace(a, b, n, endpoint=False))
    return np.vstack(pts)


MODEL_POINTS = model_line_points()


def line_mask(img: NDArray[Any]) -> NDArray[Any]:
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = ((hsv[:, :, 1] < 60) & (hsv[:, :, 2] > 185)).astype(np.uint8) * 255
    return cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))


LINE_COLOURS = ("white", "dark", "red", "blue", "yellow", "green")


def line_masks(img: NDArray[Any]) -> dict[str, NDArray[Any]]:
    """Thin line structures per colour class, relative to the local floor colour."""
    w = img.shape[1]
    k = max(7, (w // 220) | 1)
    se = cv2.getStructuringElement(cv2.MORPH_RECT, (k, k))
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lum, hue, sat = lab[:, :, 0], hsv[:, :, 0], hsv[:, :, 1]
    bright = cv2.morphologyEx(lum, cv2.MORPH_TOPHAT, se) > 14
    dark = cv2.morphologyEx(lum, cv2.MORPH_BLACKHAT, se) > 14
    chroma = cv2.morphologyEx(sat, cv2.MORPH_TOPHAT, se) > 28
    valid = cv2.erode((img.max(axis=2) > 0).astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
    coloured = (chroma | bright | dark) & (sat >= 70)
    raw = {
        "white": bright & (sat < 60),
        "dark": dark & (sat < 90) & (lum < 120),
        "red": coloured & ((hue < 10) | (hue > 165)),
        "yellow": coloured & (hue >= 15) & (hue < 36),
        "green": coloured & (hue >= 36) & (hue < 86),
        "blue": coloured & (hue >= 86) & (hue < 131),
    }
    out = {}
    for name, m in raw.items():
        mask = ((m & valid).astype(np.uint8)) * 255
        out[name] = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    return out


def median_background(frames: list[NDArray[Any]]) -> NDArray[Any]:
    return np.median(np.stack(frames), axis=0).astype(np.uint8)


def _line_through(seg: NDArray[np.floating]) -> F64:
    x1, y1, x2, y2 = (float(v) for v in seg)
    return np.cross([x1, y1, 1.0], [x2, y2, 1.0])


def _intersect(l1: F64, l2: F64) -> F64:
    p = np.cross(l1, l2)
    if abs(p[2]) < 1e-9:
        raise CalibrationError("parallel lines")
    return p[:2] / p[2]


def _fit_line(segs: NDArray[np.floating]) -> F64:
    pts = segs.reshape(-1, 2).astype(np.float32)
    vx, vy, x0, y0 = cv2.fitLine(pts, cv2.DIST_HUBER, 0, 0.01, 0.01).ravel()
    return np.cross([x0, y0, 1.0], [x0 + vx, y0 + vy, 1.0])


def _cluster_lines(segs: F64, max_lines: int) -> list[F64]:
    """Group collinear segments into lines, longest total length first."""
    lengths = np.hypot(segs[:, 2] - segs[:, 0], segs[:, 3] - segs[:, 1])
    order = np.argsort(-lengths)
    used = np.zeros(len(segs), bool)
    clusters: list[tuple[float, F64]] = []
    for i in order:
        if used[i]:
            continue
        base = _line_through(segs[i])
        base = base / np.hypot(base[0], base[1])
        members = []
        for j in order:
            if used[j]:
                continue
            a = np.array([segs[j, 0], segs[j, 1], 1.0])
            b = np.array([segs[j, 2], segs[j, 3], 1.0])
            if abs(base @ a) < 4 and abs(base @ b) < 4:
                members.append(j)
                used[j] = True
        clusters.append((float(lengths[members].sum()), _fit_line(segs[members])))
    clusters.sort(key=lambda c: -c[0])
    return [c[1] for c in clusters[:max_lines]]


def _candidates(mask: NDArray[Any]) -> list[F64]:
    h, w = mask.shape
    # thin, broken lines (wide panoramas, faint paint) are joined first; short goal lines must count
    joined = cv2.dilate(mask, np.ones((3, 3), np.uint8)) if w > 1600 else mask
    segs = cv2.HoughLinesP(
        joined, 1, np.pi / 360, threshold=50, minLineLength=min(w // 16, 120), maxLineGap=14
    )
    if segs is None or len(segs) < 4:
        raise CalibrationError("too few court lines visible")
    segs = segs[:, 0, :].astype(np.float64)
    angle = np.degrees(np.arctan2(segs[:, 3] - segs[:, 1], segs[:, 2] - segs[:, 0]))
    angle = np.where(angle < -90, angle + 180, np.where(angle > 90, angle - 180, angle))
    horiz = _cluster_lines(segs[np.abs(angle) < 8], 4)
    left = _cluster_lines(segs[(angle < -10) & (angle > -85)], 4)  # "/" (image y grows downwards)
    right = _cluster_lines(segs[(angle > 10) & (angle < 85)], 4)
    if len(horiz) < 2 or not left or not right:
        raise CalibrationError("court boundary lines not found")
    court_corners = np.array([[0, 0], [40, 0], [40, 20], [0, 20]], dtype=np.float32)
    out: list[F64] = []
    for ni, near in enumerate(horiz):
        for far in horiz[ni + 1 :] + horiz[:ni]:
            ny = -near[2] / near[1] if abs(near[1]) > 1e-9 else 0.0
            fy = -far[2] / far[1] if abs(far[1]) > 1e-9 else 0.0
            if ny <= fy + h * 0.05:  # near sideline must be below the far one
                continue
            for lg in left:
                for rg in right:
                    try:
                        quad = np.array(
                            [
                                _intersect(near, lg),
                                _intersect(near, rg),
                                _intersect(far, rg),
                                _intersect(far, lg),
                            ],
                            dtype=np.float32,
                        )
                    except CalibrationError:
                        continue
                    if not (quad[0, 0] < quad[1, 0] and quad[3, 0] < quad[2, 0]):
                        continue
                    if cv2.contourArea(quad) < w * h * 0.03:
                        continue
                    out.append(cv2.getPerspectiveTransform(court_corners, quad).astype(np.float64))
    if not out:
        raise CalibrationError("no plausible court boundary")
    return out


def initial_homography(mask: NDArray[Any], intrinsics: F64 | None = None) -> F64:
    """Best boundary hypothesis, scored by how many court line points it explains.

    With known `intrinsics` (moving cameras: focal length from the camera motion) hypotheses whose
    court is impossible for that camera are skipped.
    """
    best, best_score = None, -1.0
    size = (mask.shape[1], mask.shape[0])
    lookup = _lookup(mask)
    for cand in _candidates(mask):
        try:
            refined, score, _ = refine(cand, mask, iterations=2, lookup=lookup)
        except CalibrationError:
            continue
        if not plausible(refined, size):
            continue
        if intrinsics is not None and not camera_plausible(refined, intrinsics):
            continue
        if score > best_score:
            best, best_score = cand, score
    if best is None:
        raise CalibrationError("no plausible court boundary")
    return best


Lookup = tuple[NDArray[Any], NDArray[Any], NDArray[np.float64]]


def _lookup(mask: NDArray[Any]) -> Lookup:
    """Distance to the nearest line pixel and that pixel's position (computed once per mask)."""
    inv = (mask == 0).astype(np.uint8)
    dist, labels = cv2.distanceTransformWithLabels(
        inv, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL
    )
    zeros = np.column_stack(np.nonzero(mask == 255)[::-1]).astype(np.float64)  # label -> (x, y)
    label_to_xy = np.zeros((labels.max() + 1, 2))
    lab_at_zero = labels[mask == 255]
    label_to_xy[lab_at_zero] = zeros
    return dist, labels, label_to_xy


def refine(
    h0: F64,
    mask: NDArray[Any],
    iterations: int = 6,
    radius: float = 12.0,
    lookup: Lookup | None = None,
) -> tuple[F64, float, float]:
    """ICP against all court lines. Returns (homography, inlier share, mean distance px)."""
    dist, labels, label_to_xy = lookup or _lookup(mask)
    h = h0.copy()
    hh, ww = mask.shape
    share, err = 0.0, float("inf")
    for i in range(iterations):
        with np.errstate(divide="ignore", invalid="ignore"):  # degenerate hypotheses
            proj = geometry.apply(h, MODEL_POINTS)
        ok = (proj[:, 0] >= 0) & (proj[:, 0] < ww - 1) & (proj[:, 1] >= 0) & (proj[:, 1] < hh - 1)
        if ok.sum() < 30:
            raise CalibrationError("court projects outside the image")
        pi = proj[ok].round().astype(int)
        d = dist[pi[:, 1], pi[:, 0]]
        r = radius * (0.6**i) + 2.5
        near = d < r
        share = float(near.sum() / len(MODEL_POINTS))
        err = float(d[near].mean()) if near.any() else float("inf")
        if near.sum() < 20:
            break
        matched = label_to_xy[labels[pi[near, 1], pi[near, 0]]]
        h_new, _ = cv2.findHomography(MODEL_POINTS[ok][near], matched, cv2.RANSAC, 3.0)
        if h_new is None:
            break
        h = h_new
    with np.errstate(divide="ignore", invalid="ignore"):
        proj = geometry.apply(h, MODEL_POINTS)
    ok = (proj[:, 0] >= 0) & (proj[:, 0] < ww - 1) & (proj[:, 1] >= 0) & (proj[:, 1] < hh - 1)
    pi = proj[ok].round().astype(int)
    d = dist[pi[:, 1], pi[:, 0]]
    near = d < 3
    share = float(near.sum() / len(MODEL_POINTS))
    err = float(d[near].mean()) if near.any() else float("inf")
    return h, share, err


def plausible(h: F64, size: tuple[int, int]) -> bool:
    """Projected court must be a convex, correctly ordered quadrilateral of reasonable size."""
    w, hgt = size
    quad = geometry.apply(h, np.array([[0, 0], [40, 0], [40, 20], [0, 20]])).astype(np.float32)
    if not np.all(np.isfinite(quad)):
        return False
    if not cv2.isContourConvex(quad.reshape(-1, 1, 2)):
        return False
    near_left, near_right, far_right, far_left = quad
    if not (near_left[0] < near_right[0] and far_left[0] < far_right[0]):
        return False
    if not (far_left[1] < near_left[1] and far_right[1] < near_right[1]):
        return False
    area = cv2.contourArea(quad)
    return w * hgt * 0.05 < area < w * hgt * 4


def _chance(mask: NDArray[Any], h: F64) -> float:
    """Share of court-area pixels within 3 px of a line pixel: the match a random court gets."""
    hh, ww = mask.shape
    poly = geometry.apply(h, np.array([[0, 0], [40, 0], [40, 20], [0, 20]], np.float64))
    area = np.zeros((hh, ww), np.uint8)
    cv2.fillPoly(area, [np.clip(poly, -1e5, 1e5).round().astype(np.int32)], 1)
    if area.sum() == 0:
        return 1.0
    near = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))) > 0
    return float(near[area > 0].mean())


MIN_SEEN = 0.85  # share of the court the camera must have seen for automatic calibration


def camera_pose(h: F64, k: F64) -> dict[str, float]:
    """What a court homography implies for a pinhole camera with known intrinsics `k`.

    H ~ K [r1 r2 t]: for a real court r1 and r2 have equal length and are orthogonal, and the camera
    centre lies a few metres above the floor. Returns the axis length ratio, the cosine between the
    axes and the camera position in court coordinates (z = height above the floor).
    """
    m = np.linalg.inv(k) @ h
    a, b = m[:, 0], m[:, 1]
    na, nb = float(np.linalg.norm(a)), float(np.linalg.norm(b))
    s = 2.0 / (na + nb)
    if m[2, 2] * s < 0:  # court in front of the camera
        s = -s
    r1, r2, tr = a * s, b * s, m[:, 2] * s
    r = np.column_stack([r1, r2, np.cross(r1, r2)])
    centre = -r.T @ tr
    return {
        "ratio": na / nb if nb else float("inf"),
        "cos": float(a @ b / (na * nb)) if na and nb else 1.0,
        "x": float(centre[0]),
        "y": float(centre[1]),
        "height": abs(float(centre[2])),
    }


def camera_plausible(h: F64, k: F64) -> bool:
    pose = camera_pose(h, k)
    dist = float(np.hypot(pose["x"] - 20, pose["y"] - 10))
    return (
        abs(pose["ratio"] - 1) < 0.15
        and abs(pose["cos"]) < 0.15
        and 2.0 <= pose["height"] <= 30.0
        and dist <= 60.0
    )


def seen_share(h: F64, seen: NDArray[Any]) -> float:
    """Share of the court's line points that fall into the seen part of the image or panorama."""
    with np.errstate(divide="ignore", invalid="ignore"):  # points on the camera plane
        proj = geometry.apply(h, MODEL_POINTS)
    hh, ww = seen.shape
    ok = np.isfinite(proj).all(axis=1)
    ok &= (proj[:, 0] >= 0) & (proj[:, 1] >= 0) & (proj[:, 0] < ww) & (proj[:, 1] < hh)
    pi = proj[ok].astype(int)
    return float((seen[pi[:, 1], pi[:, 0]] > 0).sum() / len(MODEL_POINTS))


def _calibrate_mask(
    mask: NDArray[Any],
    size: tuple[int, int],
    seen: NDArray[Any] | None = None,
    intrinsics: F64 | None = None,
) -> tuple[F64, float, float, float]:
    """(homography, share, reprojection px, normalised score) for one line mask."""
    h0 = initial_homography(mask, intrinsics)
    h, share, err = refine(h0, mask)
    if not plausible(h, size):
        raise CalibrationError("no consistent court found (is the whole court in view?)")
    if intrinsics is not None and not camera_plausible(h, intrinsics):
        raise CalibrationError("court shape does not fit the camera (wrong lines)")
    if seen is not None and seen_share(h, seen) < MIN_SEEN:
        raise CalibrationError("the camera never showed the whole court; calibrate by hand")
    chance = _chance(mask, h)
    score = (share - chance) / max(1e-6, 1 - chance)
    return h, share, err, score


def calibrate_frames(
    frames: list[NDArray[Any]],
    colours: bool = True,
    seen: NDArray[Any] | None = None,
    intrinsics: F64 | None = None,
) -> Calibration:
    """Automatic calibration from a handful of frames across the video (or one panorama).

    Tries the classic white-line mask first and, with `colours`, one mask per line colour; the mask
    whose best court explains most line points beyond chance wins. `seen` (panoramas) marks the
    pixels the camera actually showed: a court that lies mostly outside is not trusted.
    `intrinsics` (3x3, known for moving cameras) rejects courts no real camera could produce.
    """
    if not frames:
        raise CalibrationError("no frames")
    bg = median_background(frames) if len(frames) > 2 else frames[0]
    size = (bg.shape[1], bg.shape[0])
    masks = {"classic": line_mask(bg)}
    if colours:
        masks.update(line_masks(bg))
    best: tuple[F64, float, float, float] | None = None
    errors: list[str] = []
    for name, mask in masks.items():
        try:
            found = _calibrate_mask(mask, size, seen, intrinsics)
        except CalibrationError as e:
            errors.append(f"{name}: {e}")
            continue
        if found[1] >= 0.25 and (best is None or found[3] > best[3]):
            best = found
        if name == "classic" and found[1] >= 0.6:
            break  # clean white lines (the common fixed-camera case): no need to search colours
    if best is None:
        reason = errors[0].split(": ", 1)[1] if errors else "court lines do not match the model"
        raise CalibrationError(reason)
    h, share, err, _ = best
    return Calibration(
        h,
        confidence=min(1.0, share / 0.7),
        reprojection_px=err,
        source="heuristic",
        image_size=size,
    )


def calibrate_points(
    image_pts: list[tuple[float, float]],
    court_pts: list[tuple[float, float]],
    image_size: tuple[int, int],
) -> Calibration:
    """Manual calibration from clicked correspondences (at least 4, not collinear)."""
    if len(image_pts) != len(court_pts) or len(image_pts) < 4:
        raise CalibrationError("need at least four point pairs")
    src = np.array(court_pts, dtype=np.float64)
    dst = np.array(image_pts, dtype=np.float64)
    found, _inliers = cv2.findHomography(src, dst, cv2.RANSAC if len(src) > 4 else 0, 4.0)
    if found is None:
        raise CalibrationError("points are degenerate")
    h: F64 = np.asarray(found, dtype=np.float64)
    err = float(np.linalg.norm(geometry.apply(h, src) - dst, axis=1).mean())
    return Calibration(
        h, confidence=1.0, reprojection_px=err, source="user_correction", image_size=image_size
    )


# goal posts (court metres): post feet on the floor, the crossbar 2 m above them
GOAL_POSTS: dict[str, tuple[float, float]] = {
    "goal_left_post_a": (0.0, 8.5),
    "goal_left_post_b": (0.0, 11.5),
    "goal_right_post_a": (40.0, 8.5),
    "goal_right_post_b": (40.0, 11.5),
}
GOAL_HEIGHT_M = 2.0


def pose_homography(r: F64, t: F64, k: F64) -> F64:
    """Floor homography H = K [r1 r2 t] of a camera with rotation r and translation t."""
    h = k @ np.column_stack([r[:, 0], r[:, 1], t.ravel()])
    return np.asarray(h / h[2, 2], dtype=np.float64)


def calibrate_pose(
    image_pts: list[tuple[float, float]],
    world_pts: list[tuple[float, float, float]],
    intrinsics: F64,
    image_size: tuple[int, int],
    source: Literal["heuristic", "user_correction", "synthetic"] = "user_correction",
) -> Calibration:
    """Calibration from points with known 3D court coordinates and a known camera (focal length
    from the camera motion). Only the camera pose is estimated (6 parameters), so few points that
    span little width are enough: the four goal-post feet fix the court once the focal length is
    known (a plain homography from the same points would leave the width loose), and points above
    the floor (crossbar, z = 2 m) help further. Rejects poses no real camera could have."""
    if len(image_pts) != len(world_pts) or len(image_pts) < 4:
        raise CalibrationError("need at least four point pairs")
    obj = np.array(world_pts, dtype=np.float64).reshape(-1, 1, 3)
    img = np.array(image_pts, dtype=np.float64).reshape(-1, 1, 2)
    k = np.asarray(intrinsics, dtype=np.float64)
    best: tuple[float, F64, F64] | None = None
    for flag in (cv2.SOLVEPNP_SQPNP, cv2.SOLVEPNP_ITERATIVE, cv2.SOLVEPNP_EPNP):
        try:
            ok, rvec, tvec = cv2.solvePnP(obj, img, k, None, flags=flag)
        except cv2.error:
            continue
        if not ok:
            continue
        rvec, tvec = cv2.solvePnPRefineLM(obj, img, k, None, rvec, tvec)
        proj, _ = cv2.projectPoints(obj, rvec, tvec, k, None)
        err = float(np.linalg.norm(proj.reshape(-1, 2) - img.reshape(-1, 2), axis=1).mean())
        if best is None or err < best[0]:
            best = (err, np.asarray(rvec, np.float64), np.asarray(tvec, np.float64))
    if best is None:
        raise CalibrationError("points are degenerate")
    err, rvec, tvec = best
    r = np.asarray(cv2.Rodrigues(rvec)[0], dtype=np.float64)
    centre = -r.T @ tvec.ravel()
    # the camera stands above the floor, outside or at the edge of the court, not far away
    if not (1.0 <= centre[2] <= 40.0) or np.hypot(centre[0] - 20, centre[1] - 10) > 80:
        raise CalibrationError("these points give an impossible camera position; check them")
    h = pose_homography(r, tvec, k)
    return Calibration(
        h,
        confidence=1.0 if source == "user_correction" else max(0.0, min(1.0, 1 - err / 20)),
        reprojection_px=err,
        source=source,
        image_size=image_size,
    )


def court_error_m(calib: Calibration, truth_h: F64) -> float:
    """Mean distance in metres between estimated and true court positions over the court."""
    grid = np.array([[x, y] for x in np.linspace(0, 40, 21) for y in np.linspace(0, 20, 11)])
    img = geometry.apply(truth_h, grid)
    return float(np.linalg.norm(calib.to_court(img) - grid, axis=1).mean())
