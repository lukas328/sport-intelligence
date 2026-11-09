import cv2
import numpy as np

from handball_vision.calibration import (
    GOAL_HEIGHT_M,
    GOAL_POSTS,
    Calibration,
    calibrate_points,
    calibrate_pose,
    court_error_m,
    pose_homography,
)


def _camera() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    k = np.array([[1200.0, 0, 640], [0, 1200.0, 360], [0, 0, 1]])
    centre = np.array([20.0, -8.0, 7.0])  # balcony on the near side, 7 m up
    look = np.array([20.0, 10.0, 0.0]) - centre
    z = look / np.linalg.norm(look)
    x = np.cross(z, [0, 0, 1.0])
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    r = np.vstack([x, y, z])
    return k, r, -r @ centre


def _project(
    k: np.ndarray, r: np.ndarray, t: np.ndarray, pts3: list[tuple[float, float, float]]
) -> np.ndarray:
    p, _ = cv2.projectPoints(
        np.array(pts3, float).reshape(-1, 1, 3), cv2.Rodrigues(r)[0], t, k, None
    )
    return p.reshape(-1, 2)


def test_goal_posts_fix_the_court_with_a_known_focal_length() -> None:
    k, r, t = _camera()
    truth = pose_homography(r, t, k)
    feet = [(x, y, 0.0) for x, y in GOAL_POSTS.values()]
    tops = [(x, y, GOAL_HEIGHT_M) for x, y in GOAL_POSTS.values()]
    rng = np.random.default_rng(1)
    noisy = _project(k, r, t, feet) + rng.normal(0, 2.0, (4, 2))
    # feet only: four points, 3 m wide at each end, plus the known camera
    calib = calibrate_pose([tuple(p) for p in noisy], feet, k, (1280, 720))
    assert court_error_m(calib, truth) < 0.6
    # the same four points as a plain homography stretch the court
    plain = calibrate_points([tuple(p) for p in noisy], [f[:2] for f in feet], (1280, 720))
    assert court_error_m(plain, truth) > court_error_m(calib, truth)
    # with the crossbar ends the error shrinks further
    pts = feet + tops
    noisy8 = _project(k, r, t, pts) + rng.normal(0, 2.0, (8, 2))
    calib8 = calibrate_pose([tuple(p) for p in noisy8], pts, k, (1280, 720))
    assert court_error_m(calib8, truth) < 0.4
    assert isinstance(calib8, Calibration)
