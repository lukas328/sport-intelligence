"""Court calibration (BRIEF 7.2 stage 2): image <-> court homography for a fixed camera.

Automatic (source "heuristic"):
1. Median of sampled frames removes moving players (fixed camera).
2. Line mask: bright, low-saturation pixels (court lines are white in most halls).
3. Hough segments are grouped into the four court boundaries (near/far sideline, both goal lines),
   whose intersections give a first homography.
4. Refinement: points sampled on every court line of the model are projected, matched to the
   nearest line pixel (distance transform) and the homography is re-fitted (iterative closest point).
5. Confidence = share of model line points that land on a line pixel; reprojection error in px.

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
    segs = cv2.HoughLinesP(mask, 1, np.pi / 360, threshold=50, minLineLength=w // 16, maxLineGap=12)
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


def initial_homography(mask: NDArray[Any]) -> F64:
    """Best boundary hypothesis, scored by how many court line points it explains."""
    best, best_score = None, -1.0
    size = (mask.shape[1], mask.shape[0])
    for cand in _candidates(mask):
        try:
            refined, score, _ = refine(cand, mask, iterations=2)
        except CalibrationError:
            continue
        if not plausible(refined, size):
            continue
        if score > best_score:
            best, best_score = cand, score
    if best is None:
        raise CalibrationError("no plausible court boundary")
    return best


def refine(
    h0: F64, mask: NDArray[Any], iterations: int = 6, radius: float = 12.0
) -> tuple[F64, float, float]:
    """ICP against all court lines. Returns (homography, inlier share, mean distance px)."""
    inv = (mask == 0).astype(np.uint8)
    dist, labels = cv2.distanceTransformWithLabels(
        inv, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL
    )
    zeros = np.column_stack(np.nonzero(mask == 255)[::-1]).astype(np.float64)  # label -> (x, y)
    label_to_xy = np.zeros((labels.max() + 1, 2))
    lab_at_zero = labels[mask == 255]
    label_to_xy[lab_at_zero] = zeros
    h = h0.copy()
    hh, ww = mask.shape
    share, err = 0.0, float("inf")
    for i in range(iterations):
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


def calibrate_frames(frames: list[NDArray[Any]]) -> Calibration:
    """Automatic calibration of a fixed camera from a handful of frames across the video."""
    if not frames:
        raise CalibrationError("no frames")
    bg = median_background(frames) if len(frames) > 2 else frames[0]
    mask = line_mask(bg)
    h0 = initial_homography(mask)
    h, share, err = refine(h0, mask)
    size = (bg.shape[1], bg.shape[0])
    if not plausible(h, size):
        raise CalibrationError("no consistent court found (is the whole court in view?)")
    if share < 0.25:
        raise CalibrationError(f"court lines do not match the model (match {share:.0%})")
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


def court_error_m(calib: Calibration, truth_h: F64) -> float:
    """Mean distance in metres between estimated and true court positions over the court."""
    grid = np.array([[x, y] for x in np.linspace(0, 40, 21) for y in np.linspace(0, 20, 11)])
    img = geometry.apply(truth_h, grid)
    return float(np.linalg.norm(calib.to_court(img) - grid, axis=1).mean())
