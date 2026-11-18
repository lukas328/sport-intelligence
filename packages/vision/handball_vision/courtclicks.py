"""Court calibration from clicked lines and points (manual calibration, line mode).

The solver lives in `handball_court.clicks` (numpy and scipy only, so the API can check clicks);
this wraps its result as a `Calibration` (source "user_correction") and its refusals as
`CalibrationError`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from handball_court.clicks import (
    KEYPOINTS,
    LINES,
    MAX_CLICK_PX,
    MAX_MEDIAN_PX,
    MIN_EQUATIONS,
    Click,
    ClicksError,
    fit_clicks,
)
from handball_vision.calibration import Calibration, CalibrationError

Px = tuple[float, float]

__all__ = [
    "KEYPOINTS",
    "LINES",
    "MAX_CLICK_PX",
    "MAX_MEDIAN_PX",
    "MIN_EQUATIONS",
    "ClickFit",
    "calibrate_clicks",
]


@dataclass
class ClickFit:
    """The court through the clicks and how well each click agrees with it."""

    calibration: Calibration
    residual_px: list[float] = field(default_factory=list)  # per used click, points first
    dropped: list[Click] = field(default_factory=list)  # clicks left out as off-line


def calibrate_clicks(
    points: dict[str, Px], lines: dict[str, list[Px]], image_size: tuple[int, int]
) -> ClickFit:
    """Court calibration from named points and clicks on court lines (image px). Raises
    CalibrationError when the clicks are too few to be checked or do not agree with one court."""
    try:
        fit = fit_clicks(points, lines, image_size)
    except ClicksError as exc:
        raise CalibrationError(str(exc)) from exc
    calib = Calibration(
        fit.homography,
        confidence=1.0,
        reprojection_px=round(fit.median_px, 2),
        source="user_correction",
        image_size=image_size,
    )
    return ClickFit(calib, fit.residual_px, fit.dropped)
