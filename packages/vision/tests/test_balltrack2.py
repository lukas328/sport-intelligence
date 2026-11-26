"""Ball tracker v2 (product port of ml/gold/tracker.py): same path as the research tracker on a gold
clip, a flight kept against clutter and a static spot, windows over long videos."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from handball_vision import balltrack2 as bt2

DATA = Path(__file__).parent / "data" / "balltrack2_g10.json"


def test_same_path_as_research_tracker_on_gold_clip() -> None:
    d = json.loads(DATA.read_text())
    peaks = [[tuple(v) for v in row] for row in d["peaks"]]
    out, conf = bt2.track(peaks, d["fps"], d["w"])
    assert len(out) == len(d["path"])
    for q, ref, c, cref in zip(out, d["path"], conf, d["conf"], strict=True):
        if ref is None:
            assert q is None
        else:
            assert q is not None
            assert math.hypot(q[0] - ref[0], q[1] - ref[1]) < 1e-2
            assert abs(c - cref) < 1e-4


def _scene(
    n: int = 300, fps: float = 25.0, seed: int = 0
) -> tuple[list[list[tuple[float, float, float]]], dict[int, tuple[float, float]]]:
    rng = np.random.default_rng(seed)
    truth: dict[int, tuple[float, float]] = {}
    peaks: list[list[tuple[float, float, float]]] = []
    for f in range(n):
        row: list[tuple[float, float, float]] = []
        # a pass from left to right and back, seen in 80 % of frames
        t = f / fps
        x = 200 + 600 * abs(math.sin(t * 0.8))
        y = 400 - 150 * abs(math.sin(t * 1.6))
        truth[f] = (x, y)
        if rng.random() < 0.8:
            row.append((x + rng.normal(0, 1.0), y + rng.normal(0, 1.0), 0.6))
        # a lamp: same spot, every frame, weaker than the ball (the no-OWLv2 rescoring gives the
        # static flag weight 0, so a still spot only loses through its missing motion support)
        row.append((1000 + rng.normal(0, 0.5), 80 + rng.normal(0, 0.5), 0.35))
        # clutter
        for _ in range(rng.poisson(1.5)):
            row.append((rng.uniform(0, 1280), rng.uniform(0, 720), rng.uniform(0.1, 0.4)))
        peaks.append(row)
    return peaks, truth


def _hit_rate(
    out: list[tuple[float, float] | None], truth: dict[int, tuple[float, float]]
) -> float:
    hits = 0
    for f, (x, y) in truth.items():
        q = out[f]
        hits += q is not None and math.hypot(q[0] - x, q[1] - y) <= 12
    return hits / len(truth)


def test_flight_kept_against_lamp_and_clutter() -> None:
    peaks, truth = _scene()
    out, conf = bt2.track(peaks, 25.0)
    assert _hit_rate(out, truth) > 0.9
    on_lamp = sum(1 for q in out if q is not None and math.hypot(q[0] - 1000, q[1] - 80) < 12)
    assert on_lamp < 10
    assert all(0.0 <= c <= 1.0 for c in conf)
    assert all(c == 0.0 for q, c in zip(out, conf, strict=True) if q is None)


def test_windows_over_long_video() -> None:
    peaks, truth = _scene(n=1000, seed=1)
    out, conf = bt2.track_windows(peaks, 25.0)
    assert len(out) == len(conf) == 1000
    assert _hit_rate(out, truth) > 0.85


def test_windows_equal_track_on_short_input() -> None:
    peaks, _ = _scene(n=150, seed=2)
    assert bt2.track_windows(peaks, 25.0) == bt2.track(peaks, 25.0)


def test_empty_and_no_candidates() -> None:
    assert bt2.track([], 25.0) == ([], [])
    out, conf = bt2.track([[], [], []], 25.0)
    assert out == [None, None, None]
    assert conf == [0.0, 0.0, 0.0]


def test_merge_candidates() -> None:
    a = [(100.0, 100.0, 0.8), (500.0, 300.0, 0.2)]
    b = [(104.0, 103.0, 0.6), (900.0, 50.0, 0.4)]
    m = bt2.merge_candidates([a, b])
    assert m[0] == (100.0, 100.0, 0.7)  # merged within 8 px, mean score
    assert (900.0, 50.0, 0.2) in m
    assert (500.0, 300.0, 0.1) in m
    assert len(bt2.merge_candidates([a * 5, b * 5], top=5)) <= 5


def test_a_spot_still_on_the_canvas_loses_its_reward() -> None:
    # the camera pans 4 px per frame: a spare ball at the bench moves through the picture but
    # stands still on the canvas, with a strong score; the game ball moves on the canvas, weaker
    n = 150
    peaks, world = [], []
    for k in range(n):
        bx, by = 200 + 3 * k, 300 + 40 * math.sin(k / 9)  # on the canvas
        peaks.append([(900.0 - 4 * k, 600.0, 0.9), (bx - 4 * k, by, 0.35)])
        world.append([(900.0, 600.0), (bx, by)])

    def on_spare(out: list[tuple[float, float] | None]) -> int:
        return sum(
            1
            for k, q in enumerate(out)
            if q is not None and math.hypot(q[0] - (900 - 4 * k), q[1] - 600) < 12
        )

    plain, _ = bt2.track(peaks, 25.0)
    assert on_spare(plain) > 100  # without the canvas the spare ball wins
    out, _ = bt2.track(peaks, 25.0, world=world)
    assert on_spare(out) == 0
    assert sum(1 for q in out if q is not None) > 100  # the game ball is followed instead
    assert bt2.track_windows(peaks, 25.0, world=world) == bt2.track(peaks, 25.0, world=world)
