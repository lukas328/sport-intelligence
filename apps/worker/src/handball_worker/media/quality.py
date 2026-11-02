"""Heuristic quality check (BRIEF 7.2 stage 1). source: heuristic.

Runs on a sample of frames: resolution, frame rate, exposure, flicker (50 Hz lighting),
camera motion and sharpness. Field visibility needs the court keypoint model (M3) and is
reported as "not_evaluated" until then. Each check yields ok / warn / fail and a tip code
that the UI translates.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
from numpy.typing import NDArray

from handball_worker.media.probe import VideoInfo

Level = str  # "ok" | "warn" | "fail" | "not_evaluated"


@dataclass(frozen=True)
class Check:
    id: str
    level: Level
    value: float | None
    tip: str | None = None


def _worst(levels: list[Level]) -> Level:
    order = {"fail": 3, "warn": 2, "ok": 1, "not_evaluated": 0}
    return max(levels, key=lambda lvl: order[lvl]) if levels else "ok"


def check_resolution(info: VideoInfo) -> Check:
    s = info.short_side
    if s >= 1080:
        return Check("resolution", "ok", s)
    if s >= 720:
        return Check("resolution", "warn", s, "resolution_low")
    return Check("resolution", "fail", s, "resolution_too_low")


def check_fps(info: VideoInfo) -> Check:
    if info.fps >= 49:
        return Check("fps", "ok", round(info.fps, 2))
    if info.fps >= 24:
        return Check("fps", "warn", round(info.fps, 2), "fps_low")
    return Check("fps", "fail", round(info.fps, 2), "fps_too_low")


def check_duration(info: VideoInfo) -> Check:
    if info.duration_s >= 20 * 60:
        return Check("duration", "ok", round(info.duration_s))
    return Check("duration", "warn", round(info.duration_s), "duration_short")


def analyse_windows(windows: list[NDArray[np.uint8]]) -> list[Check]:
    """windows: lists of consecutive grayscale frames (n, h, w) sampled at ~10 fps."""
    all_frames = np.concatenate(windows).astype(np.float32)
    checks: list[Check] = []
    mean = float(all_frames.mean())
    if mean < 50:
        checks.append(
            Check("exposure", "warn" if mean >= 30 else "fail", round(mean, 1), "too_dark")
        )
    elif mean > 215:
        checks.append(Check("exposure", "warn", round(mean, 1), "too_bright"))
    else:
        checks.append(Check("exposure", "ok", round(mean, 1)))

    # Flicker: fast oscillation of global brightness between consecutive frames (second
    # difference), typical for 50 Hz light filmed at 30/60 fps. Median over windows.
    jitters, motions = [], []
    for w in windows:
        f = w.astype(np.float32)
        means = f.reshape(len(f), -1).mean(axis=1)
        if len(means) >= 3:
            jitters.append(float(np.abs(np.diff(means, 2)).mean()))
        if len(f) >= 2:
            motions.append(float(np.abs(np.diff(f[:, ::4, ::4], axis=0)).mean()))
    if jitters:
        jitter = float(np.median(jitters))
        level = "ok" if jitter < 1.5 else "warn" if jitter < 4 else "fail"
        checks.append(
            Check("flicker", level, round(jitter, 2), None if level == "ok" else "flicker")
        )
    # Camera motion: mean absolute difference of consecutive downsampled frames.
    if motions:
        motion = float(np.median(motions))
        level = "ok" if motion < 6 else "warn" if motion < 15 else "fail"
        checks.append(
            Check(
                "camera_motion", level, round(motion, 2), None if level == "ok" else "camera_moving"
            )
        )
    # Sharpness: variance of a discrete Laplacian.
    f = all_frames
    lap = (
        -4 * f[:, 1:-1, 1:-1] + f[:, :-2, 1:-1] + f[:, 2:, 1:-1] + f[:, 1:-1, :-2] + f[:, 1:-1, 2:]
    )
    sharp = float(lap.var(axis=(1, 2)).mean())
    level = "ok" if sharp >= 40 else "warn" if sharp >= 10 else "fail"
    checks.append(Check("sharpness", level, round(sharp, 1), None if level == "ok" else "blurry"))
    checks.append(Check("field_visible", "not_evaluated", None))
    return checks


def report(info: VideoInfo, frame_checks: list[Check]) -> dict[str, object]:
    checks = [check_resolution(info), check_fps(info), check_duration(info), *frame_checks]
    overall = _worst([c.level for c in checks if c.level != "not_evaluated"])
    return {"overall": overall, "source": "heuristic", "checks": [asdict(c) for c in checks]}
