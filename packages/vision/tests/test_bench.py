"""People outside play: bench stretches by court position (handball_vision.bench)."""

from __future__ import annotations

import cv2
import numpy as np

from handball_vision.bench import BenchRule, bench_frames, sideline_margins, split_bench
from handball_vision.calibration import Calibration
from handball_vision.numbers import Reading
from handball_vision.pipeline import _drop_bench
from handball_vision.teams import TeamAssigner
from handball_vision.tracking import TrackPoint

FPS = 10.0


def _calib() -> Calibration:
    """A camera behind the near sideline: the far side is compressed (few pixels per metre)."""
    court = np.array([[0, 0], [40, 0], [40, 20], [0, 20]], np.float32)
    image = np.array([[0, 700], [1280, 700], [1000, 150], [280, 150]], np.float32)
    h = cv2.getPerspectiveTransform(court, image).astype(np.float64)
    return Calibration(h, 1.0, 0.0, "synthetic", (1280, 720))


def _points(tid: int, start: int, xy: list[tuple[float, float]], step: int = 3) -> list[TrackPoint]:
    return [
        TrackPoint(tid, start + k * step, x, y, 0.0, 0.0, True, 0) for k, (x, y) in enumerate(xy)
    ]


def _still(x: float, y: float, seconds: float, jitter: float = 0.1) -> list[tuple[float, float]]:
    rng = np.random.default_rng(1)
    n = round(seconds * FPS / 3)
    return [(x + rng.uniform(-jitter, jitter), y + rng.uniform(-jitter, jitter)) for _ in range(n)]


def _run(x0: float, y0: float, x1: float, y1: float, seconds: float) -> list[tuple[float, float]]:
    n = round(seconds * FPS / 3)
    return [(x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n) for k in range(n)]


def _runs(xy: list[tuple[float, float]], calib: Calibration | None = None) -> list[tuple[int, int]]:
    arr = np.array(xy, np.float64)
    frames = np.arange(len(xy), dtype=np.int64) * 3
    return bench_frames(frames, arr, FPS, sideline_margins(calib, arr[:, 0]))


def test_seated_beside_the_sideline_is_bench() -> None:
    runs = _runs(_still(20, -1.0, 30))
    assert len(runs) == 1
    a, b = runs[0]
    assert a == 0 and b >= 0.9 * 30 * FPS


def test_movement_goal_lines_and_short_stays_are_not_bench() -> None:
    assert _runs(_run(5, -0.8, 35, -0.8, 20)) == []  # a referee walking outside the line
    assert _runs(_still(-1.0, 10, 30)) == []  # goal line: goalkeeper, goal-line referee
    assert _runs(_still(20, -1.0, 4)) == []  # a throw-in
    assert _runs(_still(20, 3.0, 30)) == []  # standing on court


def test_far_side_margin_follows_the_pixels() -> None:
    calib = _calib()
    near, far = sideline_margins(calib, np.array([20.0]), BenchRule())
    assert near[0] >= BenchRule().margin_m
    assert far[0] > 3 * near[0]
    # a wing standing still on the far line, mapped a little beyond it by calibration error
    assert _runs(_still(2, 20.5, 30), calib) == []
    assert _runs(_still(20, -1.0, 30), calib) != []


def test_bench_stretch_is_cut_out_and_the_pieces_become_tracks() -> None:
    xy = (
        _run(10, 10, 25, 2, 10)  # playing
        + _still(25, -1.0, 30)  # substituted, sits on the bench
        + _run(25, 2, 10, 10, 10)  # back on court (often someone else after a tracker swap)
    )
    pts = _points(7, 0, xy) + _points(8, 0, _run(5, 5, 35, 15, 50))
    split = split_bench(pts, FPS, None)
    assert split.removed == set()
    assert len(split.stretches) == 1 and not split.stretches[0].whole_track
    assert set(split.pieces) == {9} and split.pieces[9][0] == 7
    kept = {p.track_id for p in split.points}
    assert kept == {7, 8, 9}
    a, b = split.cut[7][0]
    assert all(not (a <= p.frame <= b) for p in split.points if p.track_id in (7, 9))
    assert split.owner(7, 0) == 7
    assert split.owner(7, (a + b) // 2) is None
    assert split.owner(7, 3 * (len(xy) - 1)) == 9
    assert split.owner(8, 10) == 8


def test_whole_bench_track_is_removed() -> None:
    pts = _points(3, 0, _still(30, -0.8, 60))
    split = split_bench(pts, FPS, None)
    assert split.removed == {3}
    assert split.points == []
    assert split.stretches[0].whole_track
    d = split.stretches[0].to_dict(FPS)
    assert d["track_id"] == 3 and d["whole_track"] and d["y"] < 0


def test_drop_bench_moves_the_looks_with_the_points() -> None:
    xy = _run(10, 10, 25, 2, 10) + _still(25, -1.0, 30) + _run(25, 2, 10, 10, 10)
    pts = _points(7, 0, xy) + _points(3, 0, _still(30, -0.8, 60))
    teams = TeamAssigner({"home": (0, 0, 255), "away": (255, 255, 255)})
    for p in pts:
        teams.add_sample(p.track_id, np.array([50.0, 150.0, 150.0]), p.frame)
    last = pts[len(xy) - 1].frame
    reads = {7: [Reading(5, 0.9, 0), Reading(5, 0.9, 150), Reading(8, 0.9, last)], 3: []}
    looks = {7: [(0, np.zeros(4)), (last, np.ones(4))], 3: [(30, np.zeros(4))]}
    roles = {3: [(30, np.array([0.2, 0.7, 0.1]))]}
    out, info = _drop_bench(pts, FPS, _calib(), teams, reads, looks, roles)
    assert {p.track_id for p in out} == {7, 8}
    assert info["tracks_removed"] == 1 and info["pieces"] == 1 and info["stretches"] == 2
    assert 3 not in teams.samples and 3 not in looks and roles == {}
    assert [r.number for r in reads[7]] == [5] and [r.number for r in reads[8]] == [8]
    assert len(looks[7]) == 1 and len(looks[8]) == 1
    assert len(teams.samples[7]) == len(teams.frames[7]) < len(xy)
    assert all(f < 100 for f in teams.frames[7])
