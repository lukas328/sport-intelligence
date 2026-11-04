"""Learned-detector path (ADR 025): floor orientation, top-view court search, goal stripes,
observation storage and tracking from stored observations (oracle detector on synthetic video)."""

import shutil
from pathlib import Path

import cv2
import numpy as np
import pytest

from handball_vision import geometry, observe, topview
from handball_vision.calibration import MODEL_POINTS, Calibration
from handball_vision.detection import Detection
from handball_vision.synthetic import SyntheticConfig, SyntheticMatch

FFMPEG = shutil.which("ffmpeg")


def _camera(tilt_deg: float) -> tuple[np.ndarray, np.ndarray]:
    k = np.array([[1000.0, 0, 640], [0, 1000.0, 360], [0, 0, 1]])
    a = np.radians(tilt_deg)
    # world: x along the hall, y away from the camera, z up; camera looks along +y, tilted down
    r = np.array([[1, 0, 0], [0, -np.sin(a), -np.cos(a)], [0, np.cos(a), -np.sin(a)]], float)
    return k, r


def test_floor_orientation_from_two_line_families() -> None:
    k, r = _camera(22.0)
    centre = np.array([20.0, -8.0, 6.0])
    segs = []
    rng = np.random.default_rng(3)
    for _ in range(200):
        x0, y0 = rng.uniform(0, 40), rng.uniform(2, 20)
        d = np.array([1.0, 0, 0]) if rng.random() < 0.5 else np.array([0, 1.0, 0])
        a3, b3 = np.array([x0, y0, 0]), np.array([x0, y0, 0]) + d * 2.0
        pa, pb = (k @ (r @ (p - centre)) for p in (a3, b3))
        segs.append([*(pa[:2] / pa[2]), *(pb[:2] / pb[2])])
    m, length = topview.segment_normals(np.array(segs), k)
    alpha, beta, _, fit = topview.orientation_from_normals(m, length)
    assert abs(np.degrees(alpha) - 22.0) < 1.0
    assert abs(np.degrees(beta)) < 1.0
    assert fit > 0.9


def test_court_search_finds_the_court_in_a_top_view() -> None:
    ppm = 10.0
    mask = np.zeros((400, 700), np.uint8)
    # the handball court at (7, 5) metres among a few other lines
    true = np.array([[ppm, 0, 70], [0, ppm, 50], [0, 0, 1.0]])
    for p in geometry.apply(true, MODEL_POINTS).round().astype(int):
        cv2.circle(mask, tuple(int(v) for v in p), 1, 255, -1)
    cv2.rectangle(mask, (150, 80), (330, 170), 255, 1)  # a volleyball court
    tv = topview.TopView(mask, np.full_like(mask, 255), (0.0, 0.0), ppm, np.eye(3))
    found = topview.search_court(tv, scales=np.array([1.0]))
    t, _ = max(found, key=lambda c: c[1])
    centre = geometry.apply(t, np.array([[20.0, 10.0]]))[0]
    assert np.linalg.norm(centre - [270, 150]) < 0.6 * ppm


def test_stripe_score_prefers_striped_posts_over_solid_paint() -> None:
    img = np.full((200, 200, 3), 200, np.uint8)
    for k in range(10):  # a striped post: 10 alternating red and white parts
        colour = (0, 0, 220) if k % 2 == 0 else (250, 250, 250)
        cv2.rectangle(img, (50, 20 + k * 15), (54, 34 + k * 15), colour, -1)
    cv2.rectangle(img, (150, 20), (154, 170), (0, 0, 220), -1)  # a solid red frame
    paint = topview.goal_paint_mask(img)
    striped = topview.stripe_score(paint, np.array([[52.0, 20.0], [52.0, 168.0]]))
    solid = topview.stripe_score(paint, np.array([[152.0, 20.0], [152.0, 168.0]]))
    plain = topview.stripe_score(paint, np.array([[100.0, 20.0], [100.0, 168.0]]))
    assert striped > 0.5
    assert solid < 0.15 and plain < 0.05


def test_orientation_is_normalised_to_the_near_side() -> None:
    k, r = _camera(20.0)
    centre = np.array([20.0, 28.0, 6.0])  # camera on the y = 20 side
    look = np.array([20.0, 10.0, 0.0]) - centre
    z = look / np.linalg.norm(look)
    x = np.cross(z, [0, 0, 1.0])
    x /= np.linalg.norm(x)
    rot = np.vstack([x, np.cross(z, x), z])
    t = -rot @ centre
    h = k @ np.column_stack([rot[:, 0], rot[:, 1], t])
    norm = topview.normalise_orientation(h / h[2, 2], k)
    r2, t2 = topview.pose_from_homography(norm, k)
    assert (-r2.T @ t2)[1] < 0  # camera now on the near side
    left, right = geometry.apply(norm, np.array([[0.0, 10.0], [40.0, 10.0]]))
    assert left[0] < right[0]


class _Oracle:
    """A detector that returns the synthetic ground truth boxes (people only)."""

    source = "model"

    def __init__(self, truth: dict[int, list[Detection]]) -> None:
        self.truth = truth
        self.n = 0

    def detect(self, frames: list[np.ndarray]) -> list[list[Detection]]:
        out = [self.truth.get(self.n, [])]
        self.n += observe_step
        return out


observe_step = 3


@pytest.mark.skipif(FFMPEG is None, reason="ffmpeg not installed")
def test_observe_store_and_track(tmp_path: Path) -> None:
    cfg = SyntheticConfig(seconds=12, pan=1.0)
    m = SyntheticMatch(cfg)
    video = tmp_path / "pan.mp4"
    truth = m.write(video)
    boxes = {
        g.index: [Detection(*o.bbox, 0.9) for o in g.objects if o.label != "ball"] for g in truth
    }
    obs = observe.observe(video, _Oracle(boxes), detect_every=observe_step, segment_every=30)
    assert obs.motion.moving
    assert len(obs.frames) == len(truth) // observe_step + (len(truth) % observe_step > 0)
    assert obs.segments
    # storage round trip
    observe.save_observations(obs, tmp_path / "obs.npz")
    back = observe.load_observations(tmp_path / "obs.npz", obs.motion)
    assert [f.index for f in back.frames] == [f.index for f in obs.frames]
    assert sum(len(f.people) for f in back.frames) == sum(len(f.people) for f in obs.frames)
    # tracking with the true court (panorama space): positions agree with the ground truth
    g0 = truth[0]
    assert g0.homography is not None
    to_canvas = obs.motion.frame_to_canvas(0)
    assert to_canvas is not None
    hall = obs.motion.background()
    calib = Calibration(
        to_canvas @ g0.homography, 1.0, 0.0, "synthetic", (hall.shape[1], hall.shape[0])
    )
    k = cfg.kits
    res = observe.track(
        back,
        calib,
        {"home": k.home, "away": k.away, "home_gk": k.home_gk, "away_gk": k.away_gk},
        hall,
    )
    gt = {g.index: np.array([[o.x, o.y] for o in g.objects if o.label != "ball"]) for g in truth}
    dist = [
        float(np.min(np.linalg.norm(gt[p.frame] - [p.x, p.y], axis=1)))
        for p in res.points
        if p.observed
    ]
    assert len(dist) > 200
    assert float(np.median(dist)) < 0.6
    assert {"home", "away"} <= {v["label"] for v in res.teams.values()}
