"""Learned-detector path (ADR 025): floor orientation, top-view court search, goal stripes,
observation storage and tracking from stored observations (oracle detector on synthetic video)."""

import shutil
from pathlib import Path

import cv2
import numpy as np
import pytest

from handball_vision import geometry, observe, topview
from handball_vision.calibration import MODEL_POINTS, Calibration, CalibrationError
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


def test_segment_colours_from_the_hall_image() -> None:
    from handball_vision.calibration import LINE_COLOURS, line_masks

    img = np.full((300, 600, 3), (150, 110, 70), np.uint8)  # a blue-grey floor
    cv2.line(img, (20, 50), (580, 50), (245, 245, 245), 3)  # white line
    cv2.line(img, (20, 150), (580, 150), (40, 200, 40), 3)  # green line
    cv2.line(img, (20, 250), (580, 250), (30, 30, 220), 3)  # red line
    a = np.array([[40.0, 51.0], [40.0, 149.0], [40.0, 250.0], [40.0, 100.0], [-50.0, 50.0]])
    b = np.array([[500.0, 50.0], [500.0, 151.0], [500.0, 249.0], [500.0, 100.0], [-10.0, 50.0]])
    found = topview.segment_colours(line_masks(img), a, b)
    names = [LINE_COLOURS[c] if c >= 0 else None for c in found]
    assert names == ["white", "green", "red", None, None]


def _draw_court(mask: np.ndarray, t: np.ndarray, pts: np.ndarray) -> None:
    for p in geometry.apply(t, pts).round().astype(int):
        cv2.circle(mask, (int(p[0]), int(p[1])), 1, 255, -1)


def _basketball_points() -> np.ndarray:
    """A 28 x 15 m basketball court in metres (outline, centre line and circle, keys, arcs)."""
    pts: list[np.ndarray] = []
    for (x1, y1), (x2, y2) in (
        ((0, 0), (28, 0)),
        ((28, 0), (28, 15)),
        ((28, 15), (0, 15)),
        ((0, 15), (0, 0)),
        ((14, 0), (14, 15)),
        ((0, 5.05), (5.8, 5.05)),
        ((0, 9.95), (5.8, 9.95)),
        ((5.8, 5.05), (5.8, 9.95)),
        ((28, 5.05), (22.2, 5.05)),
        ((28, 9.95), (22.2, 9.95)),
        ((22.2, 5.05), (22.2, 9.95)),
    ):
        n = int(np.hypot(x2 - x1, y2 - y1) / 0.25) + 1
        pts.append(np.column_stack([np.linspace(x1, x2, n), np.linspace(y1, y2, n)]))
    ang = np.linspace(-np.pi / 2, np.pi / 2, 120)
    pts.append(np.column_stack([14 + 1.8 * np.cos(2 * ang), 7.5 + 1.8 * np.sin(2 * ang)]))
    pts.append(np.column_stack([1.575 + 6.75 * np.cos(ang), 7.5 + 6.75 * np.sin(ang)]))
    pts.append(np.column_stack([26.425 - 6.75 * np.cos(ang), 7.5 + 6.75 * np.sin(ang)]))
    return np.vstack(pts)


def test_handball_colour_is_the_one_that_forms_the_court() -> None:
    """A multi-sport floor: the white lines form the handball court, the blue ones a basketball
    court and the green ones a volleyball court, all overlapping in one hall."""
    ppm = 10.0
    size = (700, 400)
    views = {}
    for name in ("white", "blue", "green"):
        mask = np.zeros((size[1], size[0]), np.uint8)
        if name == "white":
            _draw_court(mask, np.array([[ppm, 0, 70], [0, ppm, 50], [0, 0, 1.0]]), MODEL_POINTS)
            mask[:, 300:330] = 0  # partly hidden (players, the camera never looked there)
        elif name == "blue":
            _draw_court(
                mask, np.array([[ppm, 0, 130], [0, ppm, 75], [0, 0, 1.0]]), _basketball_points()
            )
        else:
            cv2.rectangle(mask, (180, 105), (360, 195), 255, 1)
            cv2.line(mask, (270, 105), (270, 195), 255, 1)
            cv2.line(mask, (240, 105), (240, 195), 255, 1)
            cv2.line(mask, (300, 105), (300, 195), 255, 1)
        views[name] = topview.TopView(mask, np.full_like(mask, 255), (0.0, 0.0), ppm, np.eye(3))
    ranked = topview.handball_colour(views)
    assert ranked[0][0] == "white"
    assert ranked[0][1] > ranked[1][1] + 0.15


def test_colour_views_keep_colours_with_enough_floor_lines() -> None:
    from handball_vision.calibration import LINE_COLOURS

    _, r = _camera(25.0)
    centre = np.array([20.0, -8.0, 7.0])
    rng = np.random.default_rng(1)
    ends_a: list[np.ndarray] = []
    ends_b: list[np.ndarray] = []
    colours = []
    for i in range(400):
        x0, y0 = rng.uniform(0, 40), rng.uniform(0, 20)
        d = np.array([1.0, 0, 0]) if i % 2 else np.array([0, 1.0, 0])
        for p, out in ((np.array([x0, y0, 0]), ends_a), (np.array([x0, y0, 0]) + d, ends_b)):
            q = r @ (p - centre)
            out.append(q / np.linalg.norm(q))
        colours.append(LINE_COLOURS.index("white") if i < 380 else LINE_COLOURS.index("red"))
    ra, rb = np.array(ends_a), np.array(ends_b)
    up = r @ np.array([0, 0, 1.0])
    # yaw 0: the first floor direction is the camera's viewing direction on the floor (world y)
    views = topview.colour_views(ra, rb, np.array(colours), up, 7.0, 0.0, min_segments=30)
    assert set(views) == {"white"}  # 20 red segments are too few for a court of their own
    tv = views["white"]
    extent = np.array(tv.mask.shape[::-1]) / tv.ppm
    assert np.all(extent > 18) and np.all(extent < 50)


def test_view_depression_of_the_players() -> None:
    up = np.array([0.0, -1.0, 0.0])  # camera looking horizontally (y down in the image)
    angles = np.radians([5.0, 6.0, 7.0, 30.0, 4.0])
    rays = np.column_stack([np.zeros(5), np.sin(angles), np.cos(angles)])
    assert abs(topview.view_depression_deg(up, 3.0, rays) - 6.0) < 1e-6


def _low_camera_observations(height_m: float) -> observe.Observations:
    """A fixed camera at the near sideline `height_m` above the floor, looking at the court
    centre: court lines as segments and twelve standing players per frame."""
    from handball_vision.motion import CameraMotion

    k, _ = _camera(0.0)
    centre = np.array([20.0, -6.0, height_m])
    look = np.array([20.0, 10.0, 0.0]) - centre
    z = look / np.linalg.norm(look)
    x = np.cross(z, [0, 0, 1.0])
    x /= np.linalg.norm(x)
    rot = np.vstack([x, np.cross(z, x), z])

    def px(p: np.ndarray) -> np.ndarray:
        q = k @ (rot @ (p - centre))
        return np.asarray(q[:2] / q[2])

    rng = np.random.default_rng(2)
    segs = []
    for y in (0.0, 20.0):
        for x0 in np.arange(0, 40, 2.0):
            segs.append([*px(np.array([x0, y, 0])), *px(np.array([x0 + 1.8, y, 0]))])
    for xg in (0.0, 20.0, 40.0):
        for y0 in np.arange(0, 20, 2.0):
            segs.append([*px(np.array([xg, y0, 0])), *px(np.array([xg, y0 + 1.8, 0]))])
    frames = []
    for i in range(30):
        people = []
        for _ in range(12):
            foot = np.array([rng.uniform(4, 36), rng.uniform(2, 18), 0.0])
            (fx, fy), (_, hy) = px(foot), px(foot + np.array([0.0, 0.0, 1.75]))
            w = (fy - hy) * 0.3
            people.append(Detection(fx - w, hy, fx + w, fy, 0.9))
        frames.append(observe.FrameObservation(i * 3, people, [None] * len(people), []))
    motion = CameraMotion.fixed((1280, 720), 90)
    return observe.Observations(motion, frames, {0: np.array(segs)}, 25.0, 90)


def test_auto_calibration_refuses_a_flat_view_quickly() -> None:
    obs = _low_camera_observations(2.0)
    hall = np.zeros((720, 1280, 3), np.uint8)
    with pytest.raises(CalibrationError, match="too flatly") as exc:
        observe.auto_calibrate(obs, hall)
    assert exc.value.reason == "flat_view"


def _fixed_camera_observations(focal: float, centre: np.ndarray) -> observe.Observations:
    """A fixed camera with focal length `focal` at `centre` looking at the court centre, square
    onto the sidelines (they run nearly parallel in the image): the court lines (outline, centre
    line, goal-area fronts) as segments and twelve standing players per frame."""
    from handball_vision.motion import CameraMotion

    k = np.array([[focal, 0, 640], [0, focal, 360], [0, 0, 1.0]])
    look = np.array([20.0, 10.0, 0.0]) - centre
    z = look / np.linalg.norm(look)
    x = np.cross(z, [0, 0, 1.0])
    x /= np.linalg.norm(x)
    rot = np.vstack([x, np.cross(z, x), z])

    def px(p: np.ndarray) -> np.ndarray:
        q = k @ (rot @ (p - centre))
        return np.asarray(q[:2] / q[2])

    segs = []
    for y in (0.0, 20.0):
        for x0 in np.arange(0, 40, 2.0):
            segs.append([*px(np.array([x0, y, 0])), *px(np.array([x0 + 1.8, y, 0]))])
    for xg, y_from, y_to in ((0, 0, 20), (20, 0, 20), (40, 0, 20), (6, 7, 13), (34, 7, 13)):
        for y0 in np.arange(y_from, y_to, 1.0):
            segs.append([*px(np.array([xg, y0, 0])), *px(np.array([xg, y0 + 0.9, 0]))])
    arr = np.array(segs)
    inside = (arr[:, [0, 2]] > 0).all(1) & (arr[:, [0, 2]] < 1280).all(1)
    inside &= (arr[:, [1, 3]] > 0).all(1) & (arr[:, [1, 3]] < 720).all(1)
    rng = np.random.default_rng(2)
    frames = []
    for i in range(30):
        people = []
        for _ in range(12):
            foot = np.array([rng.uniform(4, 36), rng.uniform(2, 18), 0.0])
            (fx, fy), (_, hy) = px(foot), px(foot + np.array([0.0, 0.0, 1.75]))
            w = (fy - hy) * 0.3
            people.append(Detection(fx - w, hy, fx + w, fy, 0.9))
        frames.append(observe.FrameObservation(i * 3, people, [None] * len(people), []))
    motion = CameraMotion.fixed((1280, 720), 90)
    return observe.Observations(motion, frames, {0: arr[inside]}, 25.0, 90)


@pytest.mark.parametrize("focal", [700.0, 1000.0])
def test_a_fixed_camera_keeps_every_focal_length_the_lines_allow(focal: float) -> None:
    """Square onto the sidelines the markings cannot tell a long lens tilted a little from a
    wide one tilted more: the best line fit alone was off by a factor of up to three (stream
    cameras looked flat). The true focal length is among the few candidates kept."""
    obs = _fixed_camera_observations(focal, np.array([20.0, -8.0, 6.0]))
    found = observe._fixed_focals(obs)
    assert 1 <= len(found) <= 4
    assert any(abs(f / focal - 1) < 0.15 for f in found)
    assert all(max(a / b, b / a) >= 1.25 for a in found for b in found if a != b)


def test_lost_camera_motion_fails_with_its_reason() -> None:
    from dataclasses import replace

    from handball_vision.motion import CameraMotion

    base = CameraMotion.fixed((1280, 720), 90)
    lost = replace(base, moving=True, stats={"focal_px": 5100.0, "zoom_ratio": 1.1})
    obs = observe.Observations(lost, [], {}, 25.0, 90)
    with pytest.raises(CalibrationError, match="camera motion could not be followed") as lost_exc:
        observe.auto_calibrate(obs, np.zeros((720, 1280, 3), np.uint8))
    assert lost_exc.value.reason == "camera_motion"
    zoom = replace(base, moving=True, stats={"focal_px": 1100.0, "zoom_ratio": 4.0})
    with pytest.raises(CalibrationError, match=r"zoom x4\.0"):
        observe.check_motion(zoom)
    observe.check_motion(replace(base, moving=True, stats={"focal_px": 1100.0, "zoom_ratio": 1.2}))
    observe.check_motion(base)  # a fixed camera has no motion to lose


def test_stream_overlays_are_not_floor_markings() -> None:
    """A score bug stays at the same frame pixels while a panning camera moves the hall's lines
    through the frame: its edges are masked and segments on it dropped."""
    frames = []
    for i in range(12):
        f = np.zeros((120, 200, 3), np.uint8)
        cv2.line(f, (10 + 12 * i, 110), (60 + 12 * i, 40), (255, 255, 255), 2)  # a floor line
        cv2.rectangle(f, (140, 5), (190, 25), (0, 0, 255), -1)  # the score bug
        cv2.putText(f, "12:9", (145, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        frames.append(f)
    static = observe.static_edges(frames)
    assert static is not None and static[15, 165] > 0 and static[80, 40] == 0
    segs = np.array([[142.0, 6.0, 188.0, 6.0], [20.0, 100.0, 60.0, 50.0]])
    assert observe.drop_static(segs, static).tolist() == [[20.0, 100.0, 60.0, 50.0]]
    assert observe.static_edges(frames[:5]) is None


def test_a_slightly_wrong_camera_motion_still_shows_the_floor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A zooming wide stream camera: its motion is a degree or two off between frames, so the
    lines of different frames agree on the floor only loosely (real halls: 24 to 33 % of the
    line length within 1 degree, 50 to 57 % within 2; one frame alone 50 to 60 %). A moving
    camera then gets the loose tolerance when it explains enough; a fixed one never needs it."""
    from dataclasses import replace

    obs = _fixed_camera_observations(1280.0, np.array([20.0, -8.0, 6.0]))
    real = topview.orientation_from_normals
    tolerances: list[float] = []

    def shaky(
        m: np.ndarray, length: np.ndarray, tol_deg: float = 1.0
    ) -> tuple[float, float, float, float]:
        tolerances.append(tol_deg)
        alpha, beta, yaw, _ = real(m, length, tol_deg)
        return alpha, beta, yaw, 0.3 if tol_deg == 1.0 else loose_fit

    monkeypatch.setattr(topview, "orientation_from_normals", shaky)
    moving = replace(obs, motion=replace(obs.motion, moving=True, stats={"focal_px": 1280.0}))
    hall = np.zeros((720, 1280, 3), np.uint8)
    loose_fit = 0.5
    with pytest.raises(CalibrationError) as exc:
        observe.auto_calibrate(moving, hall)
    assert exc.value.reason != "no_floor" and tolerances == [1.0, 2.0]
    loose_fit = 0.4  # not enough even within 2 degrees
    with pytest.raises(CalibrationError, match="do not show a clear floor") as exc:
        observe.auto_calibrate(moving, hall)
    assert exc.value.reason == "no_floor"


def test_same_court_compares_corners() -> None:
    t = np.array([[10.0, 0, 50], [0, 10.0, 40], [0, 0, 1]])
    shifted = t.copy()
    shifted[0, 2] += 1.5
    assert topview.same_court(t, shifted, 2.0)
    assert not topview.same_court(t, shifted, 1.0)


def test_orientation_is_normalised_to_the_near_side() -> None:
    k, _ = _camera(20.0)
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


def test_teams_are_labelled_relative_to_the_match_colours() -> None:
    from handball_vision.teams import bgr_to_lab, relabel_by_clusters

    rng = np.random.default_rng(5)
    colours: dict[int, tuple[np.ndarray, int]] = {}
    # white shirts look grey and black ones dark grey in a dim hall; two referees in green
    for tid in range(8):
        colours[tid] = (np.array([125.0, 129.0, 130.0]) + rng.normal(0, 4, 3), 200)
    for tid in range(8, 16):
        colours[tid] = (np.array([55.0, 130.0, 127.0]) + rng.normal(0, 4, 3), 200)
    for tid in (16, 17):
        colours[tid] = (np.array([120.0, 100.0, 150.0]), 150)
    kits = {"home": bgr_to_lab((240, 240, 240)), "away": bgr_to_lab((32, 32, 32))}
    labels = relabel_by_clusters(colours, kits)
    assert all(labels[t] == "home" for t in range(8))
    assert all(labels[t] == "away" for t in range(8, 16))
    assert labels[16] == labels[17] == "referee"


def test_goalkeepers_by_position_and_defending_team() -> None:
    from handball_vision.events import assign_goalkeepers

    pts: list[tuple[int, int, float, float]] = []
    teams = {1: "home", 2: "away"}
    for t in range(0, 60_000, 500):
        pts.append((t, 99, 1.5, 10.0))  # someone who never leaves the left goal area
        for k in range(4):  # home defends left: home players near their goal, away further out
            pts.append((t, 10 + k, 6.5 + k * 0.3, 6 + 2.5 * k))
            pts.append((t, 20 + k, 10.0 + k * 0.3, 6 + 2.5 * k))
            teams[10 + k], teams[20 + k] = "home", "away"
    labels = assign_goalkeepers(pts, {**teams, 99: "away"})
    assert labels == {99: "home_gk"}
