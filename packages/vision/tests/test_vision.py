from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow.parquet as pq
import pytest

from handball_vision import geometry
from handball_vision.calibration import (
    Calibration,
    CalibrationError,
    calibrate_frames,
    calibrate_points,
    court_error_m,
    plausible,
)
from handball_vision.detection import (
    BackgroundDetector,
    Detection,
    OnnxDetector,
    court_mask,
    foot_positions,
)
from handball_vision.metrics import detection_scores, majority_gt, team_accuracy, tracking_scores
from handball_vision.pipeline import analyse_video, sample_frames
from handball_vision.synthetic import SyntheticConfig, SyntheticMatch
from handball_vision.teams import TeamAssigner, hex_to_bgr
from handball_vision.tracking import CourtTracker, TrackPoint, stitch

FFMPEG = shutil.which("ffmpeg")
Clip = tuple[SyntheticMatch, list[Any], list[Any]]


@pytest.fixture(scope="module")
def clip() -> Clip:
    m = SyntheticMatch(SyntheticConfig(seconds=6, fps=25))
    frames, truth = [], []
    for f, g in m.frames():
        frames.append(f)
        truth.append(g)
    return m, frames, truth


def test_geometry_roundtrip() -> None:
    p = geometry.look_at_camera((20, -12, 10), (20, 8, 0), 470, (1280, 720))
    h = geometry.ground_homography(p)
    pts = np.array([[0, 0], [40, 20], [20, 10]])
    img = geometry.apply(h, pts)
    assert np.allclose(geometry.apply(geometry.invert(h), img), pts)
    assert np.allclose(geometry.project(p, np.c_[pts, np.zeros(3)]), img)


def test_synthetic_ground_truth(clip: Clip) -> None:
    m, frames, truth = clip
    assert len(frames) == 150 and frames[0].shape == (720, 1280, 3)
    labels = sorted(o.label for o in truth[0].objects)
    assert labels.count("home") == 6 and labels.count("away") == 6 and labels.count("referee") == 2
    corners = geometry.apply(m.h, np.array([[0, 0], [40, 0], [40, 20], [0, 20]]))
    assert (corners[:, 0] > 0).all() and (corners[:, 0] < 1280).all()  # whole court in view


def test_calibration_auto(clip: Clip) -> None:
    m, frames, _ = clip
    calib = calibrate_frames(frames[::15])
    assert calib.source == "heuristic"
    assert calib.confidence > 0.7
    assert court_error_m(calib, m.h) < 0.5
    restored = Calibration.from_dict(calib.to_dict())
    assert np.allclose(restored.homography, calib.homography, atol=1e-6)


def test_calibration_fails_loudly_without_court() -> None:
    blank = [np.full((720, 1280, 3), 90, np.uint8) for _ in range(3)]
    with pytest.raises(CalibrationError):
        calibrate_frames(blank)
    with pytest.raises(CalibrationError):
        calibrate_frames([])


def test_calibration_manual(clip: Clip) -> None:
    m = clip[0]
    court: list[tuple[float, float]] = [(0, 0), (40, 0), (40, 20), (0, 20), (20, 10)]
    img = [tuple(p) for p in geometry.apply(m.h, np.array(court))]
    calib = calibrate_points(img, court, (1280, 720))
    assert calib.source == "user_correction"
    assert court_error_m(calib, m.h) < 0.01
    assert plausible(calib.homography, (1280, 720))
    with pytest.raises(CalibrationError):
        calibrate_points(img[:3], court[:3], (1280, 720))


def test_background_detector_finds_players(clip: Clip) -> None:
    _m, frames, truth = clip
    calib = calibrate_frames(frames[::15])
    det = BackgroundDetector(calib)
    det.warm_up(frames[::10])
    assert court_mask(calib).any()
    preds = [foot_positions(calib, d) for d in det.detect(frames[100:])]
    truths = [np.array([[o.x, o.y] for o in g.objects if o.label != "ball"]) for g in truth[100:]]
    scores = detection_scores(preds, truths)
    assert scores.precision > 0.6 and scores.recall > 0.5


def test_tracker_follows_two_crossing_players() -> None:
    tr = CourtTracker(fps=25)
    out: list[TrackPoint] = []
    for i in range(75):
        t = i / 25
        a, b = [5 + 4 * t, 10.0], [17 - 4 * t, 11.5]  # cross at t = 1.5 s, 1.5 m apart
        out += tr.step(np.array([a, b]), np.array([0.9, 0.9]), labels=["home", "away"])
    ids = {p.track_id for p in out}
    assert len(ids) == 2
    first = {p.track_id: p.y for p in out if p.frame == 10}
    last = {p.track_id: p.y for p in out if p.frame == 74}
    for tid in ids:
        assert abs(first[tid] - last[tid]) < 0.5  # nobody swapped lanes


def test_tracker_bridges_short_occlusion_and_stitching() -> None:
    tr = CourtTracker(fps=25, max_age_s=0.4)
    out: list[TrackPoint] = []
    for i in range(100):
        visible = not (30 <= i < 60)  # 1.2 s gap, longer than max_age
        pos = np.array([[10 + 0.1 * i, 5.0]]) if visible else np.zeros((0, 2))
        out += tr.step(pos, np.array([0.9] if visible else []))
    assert len({p.track_id for p in out}) == 2
    stitched, mapping = stitch(out, 25)
    assert len({p.track_id for p in stitched}) == 1
    assert len(set(mapping.values())) == 1


def test_team_assigner() -> None:
    kits = {"home": hex_to_bgr("#2828c8"), "away": hex_to_bgr("#ebe6e6"), "referee": (25, 25, 25)}
    ta = TeamAssigner(kits)
    frame = np.zeros((100, 100, 3), np.uint8)
    frame[:, :50] = kits["home"]
    frame[:, 50:] = kits["away"]
    for _ in range(4):
        ta.add(1, frame, Detection(5, 0, 45, 100, 1))
        ta.add(2, frame, Detection(55, 0, 95, 100, 1))
    r1, r2 = ta.result(1), ta.result(2)
    assert r1 is not None and r1.label == "home" and r1.confidence > 0.5
    assert r2 is not None and r2.label == "away"
    assert ta.result(3) is None


def test_metrics_perfect_and_switch() -> None:
    gt = np.array([[1.0, 1.0], [5.0, 5.0]])
    perfect = [([1, 2], gt, [10, 20], gt)] * 5
    s = tracking_scores(perfect)
    assert s.mota == 1.0 and s.idf1 == 1.0 and s.id_switches == 0
    swapped = perfect[:2] + [([2, 1], gt, [10, 20], gt)] * 3
    assert tracking_scores(swapped).id_switches == 2
    assert majority_gt(perfect) == {1: 10, 2: 20}
    assert team_accuracy({1: "home", 2: "away"}, {1: 10, 2: 20}, {10: "home", 20: "home"}) == 0.5
    d = detection_scores([gt, np.zeros((0, 2))], [gt, gt])
    assert d.precision == 1.0 and d.recall == 0.5


def test_onnx_detector_plumbing(tmp_path: Path) -> None:
    onnx = pytest.importorskip("onnx")
    from onnx import TensorProto, helper

    # tiny model: ignores the image and returns one fixed box per batch item (tests letterbox maths)
    box = np.array([[[100, 200, 140, 300, 0.9, 0], [0, 0, 1, 1, 0.1, 0]]], np.float32)
    const = helper.make_tensor("box", TensorProto.FLOAT, box.shape, box.ravel())
    graph = helper.make_graph(
        [
            helper.make_node("Shape", ["images"], ["s"]),
            helper.make_node("Slice", ["s", "zero", "one"], ["b"]),
            helper.make_node("Concat", ["b", "tail"], ["shape"], axis=0),
            helper.make_node("Expand", ["box", "shape"], ["out"]),
        ],
        "fixed",
        [helper.make_tensor_value_info("images", TensorProto.FLOAT, ["n", 3, 640, 640])],
        [helper.make_tensor_value_info("out", TensorProto.FLOAT, ["n", 2, 6])],
        initializer=[
            const,
            helper.make_tensor("zero", TensorProto.INT64, [1], [0]),
            helper.make_tensor("one", TensorProto.INT64, [1], [1]),
            helper.make_tensor("tail", TensorProto.INT64, [2], [2, 6]),
        ],
    )
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 17)], ir_version=9)
    path = tmp_path / "fixed.onnx"
    onnx.save(model, path)
    det = OnnxDetector(path, batch=2)
    frames = [np.zeros((720, 1280, 3), np.uint8)] * 3
    out = det.detect(frames)
    assert [len(d) for d in out] == [1, 1, 1]
    d = out[0][0]
    # 1280x720 letterboxed to 640: scale 0.5, top padding 140
    assert (d.x1, d.y1, d.x2, d.y2) == pytest.approx((200, 120, 280, 320))
    assert d.cls == "person" and det.source == "model"


@pytest.mark.skipif(FFMPEG is None, reason="ffmpeg not installed")
def test_pipeline_end_to_end(tmp_path: Path) -> None:
    m = SyntheticMatch(SyntheticConfig(seconds=8))
    video = tmp_path / "m.mp4"
    m.write(video)
    assert len(sample_frames(video, 4)) == 4
    k = m.cfg.kits
    seen: list[str] = []
    res = analyse_video(
        video,
        {
            "home": k.home,
            "home_gk": k.home_gk,
            "away": k.away,
            "away_gk": k.away_gk,
            "referee": k.referee,
        },
        progress=lambda s, f: seen.append(s),
    )
    assert res.frames == 200
    assert court_error_m(res.calibration, m.h) < 0.5
    assert 10 <= len(res.teams) <= 40
    assert {"calibration", "detection", "tracking"} <= set(res.timings_s)
    labels = {v["label"] for v in res.teams.values()}
    assert {"home", "away"} <= labels
    res.write_parquet(tmp_path / "t.parquet")
    table = pq.read_table(tmp_path / "t.parquet")
    assert table.num_rows == len(res.points)
    assert table.schema.metadata[b"detector"] == b"heuristic"
    summary = res.summary()
    assert summary[0]["first_ms"] >= 0 and "team" in summary[0]
    assert "calibration" in seen
