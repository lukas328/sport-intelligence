"""Moving cameras: camera motion, panorama, per-frame calibration, end-to-end analysis."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from handball_vision import geometry
from handball_vision.calibration import (
    Calibration,
    camera_plausible,
    camera_pose,
    court_error_m,
    line_masks,
)
from handball_vision.detection import MovingBackgroundDetector, court_mask
from handball_vision.motion import (
    CameraMotion,
    _angle,
    _rodrigues,
    estimate_focal,
    estimate_motion,
    fit_rotation,
)
from handball_vision.pipeline import analyse_video, camera_moves
from handball_vision.synthetic import SyntheticConfig, SyntheticMatch

FFMPEG = shutil.which("ffmpeg")
# play switches sides every 4 s, so the camera shows the whole court within the clip
PAN = SyntheticConfig(seconds=10, fps=25, pan=1.0, focal_px=900, phase_s=4.0)


def _rotation_and_focal(p: np.ndarray[Any, Any], size: tuple[int, int]) -> tuple[Any, float]:
    w, h = size
    a = np.linalg.inv(np.array([[1, 0, w / 2], [0, 1, h / 2], [0, 0, 1.0]])) @ p[:, :3]
    a = a / np.linalg.norm(a[2])
    f = float(np.linalg.norm(a[0]))
    return np.vstack([a[0] / f, a[1] / f, a[2]]), f


@pytest.fixture(scope="module")
def pan_clip() -> tuple[SyntheticMatch, list[Any], list[Any], list[Any]]:
    m = SyntheticMatch(PAN)
    frames, truth, cams = [], [], []
    for f, g in m.frames():
        frames.append(f)
        truth.append(g)
        cams.append(_rotation_and_focal(m.p, PAN.size))
    return m, frames, truth, cams


@pytest.fixture(scope="module")
def pan_motion(pan_clip: tuple[Any, list[Any], list[Any], list[Any]]) -> CameraMotion:
    _, frames, _, _ = pan_clip
    return estimate_motion(iter(frames), expected_frames=len(frames))


def test_fit_rotation_recovers_rotation_and_zoom() -> None:
    rng = np.random.default_rng(0)
    r_true = _rodrigues(np.array([0.02, -0.15, 0.01]))
    f_dst, zoom = 800.0, 1.1
    src = rng.uniform(-300, 300, (200, 2))
    rays = np.column_stack([src / (f_dst * zoom), np.ones(len(src))]) @ r_true.T
    dst = f_dst * rays[:, :2] / rays[:, 2:3] + rng.normal(0, 0.3, (len(src), 2))
    dst[:20] += 40  # outliers (moving players)
    r, z, rms = fit_rotation(src, dst, f_dst)
    assert np.degrees(_angle(r, r_true)) < 0.05
    assert z == pytest.approx(zoom, rel=1e-3)
    assert rms < 1.0


def test_estimate_focal_from_rotations() -> None:
    rng = np.random.default_rng(1)
    f_true = 900.0
    pairs = []
    for k in range(6):
        r = _rodrigues(np.array([0.03, 0.12 + 0.03 * k, 0.0]))
        src = rng.uniform(-300, 300, (150, 2))
        rays = np.column_stack([src / f_true, np.ones(len(src))]) @ r.T
        pairs.append((src, f_true * rays[:, :2] / rays[:, 2:3]))
    assert estimate_focal(pairs, 640.0) == pytest.approx(f_true, rel=0.02)


def test_fixed_camera_is_not_moving() -> None:
    m = SyntheticMatch(SyntheticConfig(seconds=3, fps=25))
    motion = estimate_motion((f for f, _ in m.frames()), expected_frames=75)
    assert not motion.moving
    assert motion.coverage == 1.0
    h = motion.frame_to_canvas(10)
    assert h is not None and np.allclose(h, np.eye(3))


def test_panning_motion_matches_ground_truth(
    pan_clip: tuple[Any, list[Any], list[Any], list[Any]], pan_motion: CameraMotion
) -> None:
    _, _, _, cams = pan_clip
    motion = pan_motion
    assert motion.moving and motion.coverage == 1.0
    assert motion.stats["pan_deg"] > 10
    ref = len(cams) // 2
    r_ref = motion.rotations[ref]
    assert r_ref is not None
    errors = []
    for i in range(0, len(cams), 10):
        ri = motion.rotations[i]
        assert ri is not None
        truth = cams[i][0] @ cams[ref][0].T
        errors.append(np.degrees(_angle(ri @ r_ref.T, truth)))
    assert float(np.median(errors)) < 0.5
    assert motion.focals[0] == pytest.approx(PAN.focal_px, rel=0.05)


def test_panorama_calibration_gives_per_frame_court(
    pan_clip: tuple[Any, list[Any], list[Any], list[Any]], pan_motion: CameraMotion
) -> None:
    _, _, truth, _ = pan_clip
    canvas = pan_motion.background()
    assert canvas.shape[:2] == (pan_motion.canvas_size[1], pan_motion.canvas_size[0])
    # calibrate the canvas from the true court of one frame, then check every other frame
    to_canvas = pan_motion.frame_to_canvas(0)
    assert to_canvas is not None
    calib = Calibration(
        to_canvas @ truth[0].homography, 1.0, 0.0, "synthetic", pan_motion.canvas_size
    )
    det = MovingBackgroundDetector(calib, canvas, pan_motion)
    errs = []
    for i in range(0, len(truth), 25):
        frame_calib = det.set_frame(i)
        assert frame_calib is not None and det.background is not None
        errs.append(court_error_m(frame_calib, truth[i].homography))
        assert det.mask.any()
    assert float(np.median(errs)) < 0.5


def test_court_mask_clips_parts_behind_the_camera() -> None:
    # camera looks along the sideline: the far end of the court is in view, the near end behind
    p = geometry.look_at_camera((-5.0, 10.0, 6.0), (20.0, 10.0, 0.0), 600, (640, 360))
    calib = Calibration(geometry.ground_homography(p), 1.0, 0.0, "synthetic", (640, 360))
    mask = court_mask(calib)
    assert mask[300, 320] == 255  # floor in front of the camera
    assert mask[5, 320] == 0  # above the horizon: never court


def test_line_masks_find_white_lines(
    pan_clip: tuple[Any, list[Any], list[Any], list[Any]],
) -> None:
    _, frames, _, _ = pan_clip
    masks = line_masks(frames[0])
    assert set(masks) == {"white", "dark", "red", "blue", "yellow", "green"}
    assert masks["white"].sum() > masks["green"].sum()


@pytest.mark.skipif(FFMPEG is None, reason="ffmpeg not installed")
def test_panning_video_end_to_end(tmp_path: Path) -> None:
    m = SyntheticMatch(PAN)
    video = tmp_path / "pan.mp4"
    truth = m.write(video)
    assert camera_moves(video)
    k = m.cfg.kits
    res = analyse_video(
        video,
        {"home": k.home, "home_gk": k.home_gk, "away": k.away, "away_gk": k.away_gk},
    )
    assert res.extra["camera"] == "moving"
    assert res.extra["frames_without_view"] == 0
    assert res.calibration.confidence > 0.5
    assert res.detections_per_frame > 5
    assert {"home", "away"} <= {v["label"] for v in res.teams.values()}
    assert {"camera_motion", "panorama", "view", "detection"} <= set(res.timings_s)
    # tracked court positions agree with the ground truth
    gt = {g.index: np.array([[o.x, o.y] for o in g.objects if o.label != "ball"]) for g in truth}
    dist = [
        float(np.min(np.linalg.norm(gt[p.frame] - [p.x, p.y], axis=1)))
        for p in res.points
        if p.observed
    ]
    assert len(dist) > 500
    assert float(np.median(dist)) < 0.6


@pytest.mark.skipif(FFMPEG is None, reason="ffmpeg not installed")
def test_fixed_video_is_detected_as_fixed(tmp_path: Path) -> None:
    m = SyntheticMatch(SyntheticConfig(seconds=3))
    video = tmp_path / "fixed.mp4"
    m.write(video)
    assert not camera_moves(video)


def test_camera_pose_separates_real_and_impossible_courts() -> None:
    p = geometry.look_at_camera((20.0, -12.0, 10.0), (20.0, 8.0, 0.0), 900, (1280, 720))
    h = geometry.ground_homography(p)
    k = np.array([[900, 0, 640], [0, 900, 360], [0, 0, 1.0]])
    pose = camera_pose(h, k)
    assert pose["ratio"] == pytest.approx(1.0, abs=1e-6)
    assert pose["cos"] == pytest.approx(0.0, abs=1e-6)
    assert (pose["x"], pose["y"], pose["height"]) == pytest.approx((20.0, -12.0, 10.0), abs=1e-6)
    assert camera_plausible(h, k)
    # a court squeezed to half its length (lines of another sport): no camera can see that
    squeezed = h @ np.diag([0.5, 1.0, 1.0])
    assert not camera_plausible(squeezed, k)
