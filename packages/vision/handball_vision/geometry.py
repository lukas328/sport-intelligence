"""Homographies between the court plane (metres) and the image (pixels)."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

F64 = NDArray[np.float64]


def apply(h: F64, pts: NDArray[np.floating]) -> F64:
    """Apply a 3x3 homography to (n, 2) points."""
    p = np.asarray(pts, dtype=np.float64).reshape(-1, 2)
    hom = np.hstack([p, np.ones((len(p), 1))]) @ h.T
    return hom[:, :2] / hom[:, 2:3]


def invert(h: F64) -> F64:
    return np.linalg.inv(h)


def look_at_camera(
    position: tuple[float, float, float],
    target: tuple[float, float, float],
    focal_px: float,
    size: tuple[int, int],
) -> F64:
    """3x4 projection matrix for a pinhole camera (world z is up, court on z = 0)."""
    w, h = size
    k = np.array([[focal_px, 0, w / 2], [0, focal_px, h / 2], [0, 0, 1]])
    c = np.array(position, dtype=np.float64)
    forward = np.array(target, dtype=np.float64) - c
    forward /= np.linalg.norm(forward)
    right = np.cross(forward, [0.0, 0.0, 1.0])
    right /= np.linalg.norm(right)
    down = np.cross(forward, right)
    r = np.vstack([right, down, forward])  # camera axes: x right, y down, z forward
    t = -r @ c
    return k @ np.hstack([r, t[:, None]])


def project(p: F64, xyz: NDArray[np.floating]) -> F64:
    pts = np.asarray(xyz, dtype=np.float64).reshape(-1, 3)
    hom = np.hstack([pts, np.ones((len(pts), 1))]) @ p.T
    return hom[:, :2] / hom[:, 2:3]


def ground_homography(p: F64) -> F64:
    """Court plane (x, y, 0) -> image homography from a projection matrix."""
    return p[:, [0, 1, 3]] / p[2, 3]
