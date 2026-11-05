"""Court calibration from an earlier video of the same hall (backlog item 1, ADR 025).

A club films most of its home games from the same place: once a coach has clicked (or confirmed)
the court on one video, every later video of that hall and camera position can take it over. The
two hall images (panorama of a moving camera, median frame of a fixed one) both show the floor, a
plane, so their floors are related by a homography whatever the camera did in between: matched
image features give it, and the earlier court (court metres -> earlier hall image) followed by it
is the court in the new hall image.

1. **Features** (`register`): SIFT on both hall images (scaled to at most `MAX_SIDE` px), the
   unseen black border of a panorama masked, Lowe's ratio test.
2. **One homography for the whole image** when the camera stood at the same place (walls, stands
   and floor then move together) and the floor matches agree with it; otherwise **one for the
   floor alone** (matches inside the earlier court, widened by 3 m): a camera a few metres away
   moves the walls differently, the floor still by one homography.
3. **Checks**: enough inliers, most floor matches agree, the court in the new image is a
   plausible quadrilateral. Anything else raises CalibrationError and the analysis carries on
   with the automatic court.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np
from numpy.typing import NDArray

from handball_vision import geometry
from handball_vision.calibration import Calibration, CalibrationError, plausible

F64 = NDArray[np.float64]
U8 = NDArray[Any]

MAX_SIDE = 2000  # hall images are matched at this width at most (panoramas reach 3600 px)
MIN_INLIERS = 30  # matches that agree with the whole-image homography
MIN_FLOOR_INLIERS = 12  # matches on the floor that agree with it
MIN_FLOOR_SHARE = 0.5  # share of the floor matches that agree


@dataclass(frozen=True)
class HallMatch:
    calibration: Calibration
    inliers: int
    floor_inliers: int
    matches: int
    method: str  # "same_place" (one homography for the image) or "floor" (the floor alone)
    error_px: float  # median transfer error of the floor inliers, in new-image pixels

    def info(self) -> dict[str, Any]:
        return {
            "method": "hall",
            "hall_match": self.method,
            "inliers": self.inliers,
            "floor_inliers": self.floor_inliers,
            "matches": self.matches,
            "error_px": round(self.error_px, 2),
        }


def _scaled(image: U8) -> tuple[U8, float]:
    s = min(1.0, MAX_SIDE / max(image.shape[:2]))
    if s < 1.0:
        image = cv2.resize(image, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    return image, s


def _features(image: U8) -> tuple[F64, NDArray[np.float32] | None]:
    grey = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    seen = image.max(axis=2) if image.ndim == 3 else image
    mask = cv2.erode((seen > 0).astype(np.uint8) * 255, np.ones((9, 9), np.uint8))
    grey = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(grey)
    kp, desc = cv2.SIFT.create(nfeatures=6000).detectAndCompute(grey, mask)
    pts = np.array([k.pt for k in kp], dtype=np.float64).reshape(-1, 2)
    return pts, None if desc is None else np.asarray(desc, np.float32)


def _floor_polygon(court_to_image: F64, margin_m: float = 3.0) -> F64:
    """The court widened by `margin_m`, in image pixels."""
    m = margin_m
    corners = np.array([[-m, -m], [40 + m, -m], [40 + m, 20 + m], [-m, 20 + m]], np.float64)
    return geometry.apply(court_to_image, corners)


def _inside(poly: F64, pts: F64) -> NDArray[np.bool_]:
    if not np.isfinite(poly).all():
        return np.zeros(len(pts), bool)
    contour = poly.astype(np.float32).reshape(-1, 1, 2)
    return np.array(
        [cv2.pointPolygonTest(contour, (float(x), float(y)), False) >= 0 for x, y in pts],
        dtype=bool,
    )


@dataclass(frozen=True)
class FloorMatch:
    homography: F64  # reference hall image px -> new hall image px (valid on the floor)
    inliers: int
    floor_inliers: int
    matches: int
    method: str
    error_px: float


def match_floor(reference: U8, image: U8, floor_polygon: F64, ransac_px: float = 4.0) -> FloorMatch:
    """The homography that carries the floor of `reference` (inside `floor_polygon`, reference
    pixels) onto `image`; CalibrationError when the two images do not show the same floor."""
    ref_s, s_ref = _scaled(reference)
    img_s, s_img = _scaled(image)
    p_ref, d_ref = _features(ref_s)
    p_img, d_img = _features(img_s)
    if d_ref is None or d_img is None or len(p_ref) < 20 or len(p_img) < 20:
        raise CalibrationError("too few features to recognise the hall")
    pairs = cv2.BFMatcher(cv2.NORM_L2).knnMatch(d_ref, d_img, k=2)
    good = [m[0] for m in pairs if len(m) == 2 and m[0].distance < 0.75 * m[1].distance]
    if len(good) < MIN_FLOOR_INLIERS:
        raise CalibrationError(f"not the same hall or camera position ({len(good)} matches)")
    a = p_ref[[m.queryIdx for m in good]]
    b = p_img[[m.trainIdx for m in good]]
    floor = _inside(floor_polygon * s_ref, a)

    def fit(sel: NDArray[np.bool_]) -> tuple[F64 | None, NDArray[np.bool_]]:
        if sel.sum() < 4:
            return None, np.zeros(len(a), bool)
        found, _ = cv2.findHomography(a[sel], b[sel], cv2.RANSAC, ransac_px, maxIters=4000)
        if found is None:
            return None, np.zeros(len(a), bool)
        h = np.asarray(found, np.float64)
        err = np.linalg.norm(geometry.apply(h, a) - b, axis=1)
        return h, err < ransac_px

    method = "same_place"
    h, ok = fit(np.ones(len(a), bool))
    n_floor = int(floor.sum())
    if (
        h is None
        or ok.sum() < MIN_INLIERS
        or (ok & floor).sum() < max(MIN_FLOOR_INLIERS, MIN_FLOOR_SHARE * n_floor)
    ):
        # walls and floor do not move together: the camera stood elsewhere, the floor decides
        method = "floor"
        h, ok = fit(floor)
        ok &= floor
        if h is None or ok.sum() < max(MIN_FLOOR_INLIERS, MIN_FLOOR_SHARE * n_floor):
            raise CalibrationError(
                "not the same hall or camera position "
                f"({int(ok.sum())} of {n_floor} floor matches agree)"
            )
    floor_ok = ok & floor
    err_px = np.linalg.norm(geometry.apply(h, a[floor_ok]) - b[floor_ok], axis=1) / s_img
    full = np.diag([1 / s_img, 1 / s_img, 1.0]) @ h @ np.diag([s_ref, s_ref, 1.0])
    return FloorMatch(
        full / full[2, 2],
        int(ok.sum()),
        int(floor_ok.sum()),
        len(good),
        method,
        float(np.median(err_px)) if len(err_px) else 0.0,
    )


def register(reference: U8, reference_court: F64, image: U8, ransac_px: float = 4.0) -> HallMatch:
    """The court of `image` from `reference` (an earlier hall image of the same hall) and its
    court homography `reference_court` (court metres -> reference pixels)."""
    fm = match_floor(reference, image, _floor_polygon(reference_court), ransac_px)
    court = fm.homography @ reference_court
    court = court / court[2, 2]
    size = (int(image.shape[1]), int(image.shape[0]))
    if not plausible(court, size):
        raise CalibrationError("the earlier court does not fit this hall image")
    calib = Calibration(
        court,
        confidence=float(min(1.0, fm.floor_inliers / 60)),
        reprojection_px=fm.error_px,
        source="heuristic",
        image_size=size,
    )
    return HallMatch(calib, fm.inliers, fm.floor_inliers, fm.matches, fm.method, fm.error_px)
