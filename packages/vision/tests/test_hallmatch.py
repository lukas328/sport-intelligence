import cv2
import numpy as np
import pytest

from handball_court import COURT
from handball_vision import geometry
from handball_vision.calibration import CalibrationError, court_error_m, pose_homography
from handball_vision.hallmatch import register

PPM = 10.0  # floor texture: pixels per metre
MARGIN = 6.0  # metres of floor around the court


def _floor_texture(seed: int) -> np.ndarray:
    """A top view of the hall floor: wood-coloured with random marks and the court lines."""
    rng = np.random.default_rng(seed)
    w, h = int((40 + 2 * MARGIN) * PPM), int((20 + 2 * MARGIN) * PPM)
    img = np.full((h, w, 3), (60, 110, 170), np.uint8)
    for _ in range(900):
        x, y = int(rng.integers(0, w)), int(rng.integers(0, h))
        colour = tuple(int(c) for c in rng.integers(0, 255, 3))
        cv2.circle(img, (x, y), int(rng.integers(2, 7)), colour, -1)
    for line in COURT.lines.values():
        pts = ((np.array(line, np.float64) + MARGIN) * PPM).round().astype(np.int32)
        cv2.polylines(img, [pts.reshape(-1, 1, 2)], False, (255, 255, 255), 2)
    return img


def _camera(x: float, y: float, z: float, yaw_deg: float = 0.0) -> tuple[np.ndarray, ...]:
    k = np.array([[900.0, 0, 640], [0, 900.0, 360], [0, 0, 1]])
    centre = np.array([x, y, z])
    look = np.array([20.0, 10.0, 0.0]) - centre
    yaw = np.radians(yaw_deg)
    look = (
        np.array([[np.cos(yaw), -np.sin(yaw), 0], [np.sin(yaw), np.cos(yaw), 0], [0, 0, 1]]) @ look
    )
    zc = look / np.linalg.norm(look)
    xc = np.cross(zc, [0, 0, 1.0])
    xc /= np.linalg.norm(xc)
    yc = np.cross(zc, xc)
    r = np.vstack([xc, yc, zc])
    return k, r, -r @ centre


def _hall_image(
    cam: tuple[np.ndarray, ...], floor: np.ndarray, seed: int
) -> tuple[np.ndarray, np.ndarray]:
    """The hall from a camera: the textured floor, stands and walls (random blocks) above it."""
    k, r, t = cam
    court_to_img = pose_homography(r, t, k)
    tex_to_court = np.array([[1 / PPM, 0, -MARGIN], [0, 1 / PPM, -MARGIN], [0, 0, 1.0]])
    img = cv2.warpPerspective(floor, court_to_img @ tex_to_court, (1280, 720))
    covered = cv2.warpPerspective(
        np.full(floor.shape[:2], 255, np.uint8), court_to_img @ tex_to_court, (1280, 720)
    )
    rng = np.random.default_rng(seed)
    walls = np.zeros_like(img)
    for _ in range(1500):
        x, y = int(rng.integers(0, 1280)), int(rng.integers(0, 720))
        colour = tuple(int(c) for c in rng.integers(0, 255, 3))
        cv2.rectangle(
            walls, (x, y), (x + int(rng.integers(4, 30)), y + int(rng.integers(4, 30))), colour, -1
        )
    img[covered == 0] = walls[covered == 0]
    return img, court_to_img


def test_same_camera_place_takes_over_the_court() -> None:
    floor = _floor_texture(1)
    ref, ref_h = _hall_image(_camera(20, -9, 6), floor, 2)
    # a later video: the same place, the camera turned a little (same walls, moved in the image)
    k, r, _ = _camera(20, -9, 6, yaw_deg=4.0)
    k0, r0, _ = _camera(20, -9, 6)
    turn = k @ r @ r0.T @ np.linalg.inv(k0)  # the same camera centre: the image turns as a whole
    img = cv2.warpPerspective(ref, turn, (1280, 720))
    truth = turn @ ref_h
    found = register(ref, ref_h, img)
    assert found.method == "same_place"
    assert found.floor_inliers >= 12
    assert court_error_m(found.calibration, truth) < 0.15
    assert found.calibration.source == "heuristic"
    assert found.info()["method"] == "hall"


def test_a_camera_a_few_metres_away_matches_on_the_floor() -> None:
    floor = _floor_texture(3)
    ref, ref_h = _hall_image(_camera(20, -9, 6), floor, 4)
    # the camera stood elsewhere: walls and stands move differently from the floor (here they
    # stay where they were in the image, and there are more of them than floor marks)
    img, truth = _hall_image(_camera(23, -8, 5), floor, 4)
    found = register(ref, ref_h, img)
    assert found.method == "floor"
    assert court_error_m(found.calibration, truth) < 0.2


def test_another_hall_is_refused() -> None:
    ref, ref_h = _hall_image(_camera(20, -9, 6), _floor_texture(6), 7)
    other, _ = _hall_image(_camera(20, -9, 6), _floor_texture(8), 9)
    with pytest.raises(CalibrationError, match="not the same hall"):
        register(ref, ref_h, other)


def test_transfer_keeps_court_metres() -> None:
    floor = _floor_texture(10)
    ref, ref_h = _hall_image(_camera(20, -9, 6), floor, 11)
    found = register(ref, ref_h, ref.copy())
    pts = np.array([[0.0, 0.0], [40.0, 20.0], [6.0, 10.0]])
    assert np.allclose(found.calibration.to_image(pts), geometry.apply(ref_h, pts), atol=1.0)
