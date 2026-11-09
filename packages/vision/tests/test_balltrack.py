"""Ball path from noisy per-frame peaks: real flight kept, wall spot and clutter dropped."""

from __future__ import annotations

import numpy as np

from handball_vision import balltrack as bt

FPS = 25.0


def _scene(seed: int = 0) -> tuple[list[bt.Peak], dict[int, tuple[float, float]]]:
    rng = np.random.default_rng(seed)
    peaks: list[bt.Peak] = []
    truth: dict[int, tuple[float, float]] = {}
    # the ball: a pass, a dribble, a shot; missed in 30 % of frames, absent in between
    for start, end, p0, v in [
        (10, 60, (200.0, 400.0), (300.0, -40.0)),
        (90, 170, (600.0, 300.0), (-120.0, 60.0)),
        (200, 230, (300.0, 380.0), (700.0, -100.0)),
    ]:
        for f in range(start, end):
            t = (f - start) / FPS
            x, y = p0[0] + v[0] * t, p0[1] + v[1] * t
            truth[f] = (x, y)
            if rng.random() < 0.7:
                peaks.append(bt.Peak(f, x + rng.normal(0, 1.5), y + rng.normal(0, 1.5), 0.6))
    for f in range(0, 250):
        # a ball-sized spot on the wall, seen in most frames with a high score
        if rng.random() < 0.6:
            peaks.append(bt.Peak(f, 900 + rng.normal(0, 1), 120 + rng.normal(0, 1), 0.8))
        # clutter: random places, now and then
        for _ in range(rng.poisson(1.0)):
            peaks.append(
                bt.Peak(f, rng.uniform(0, 1280), rng.uniform(0, 720), rng.uniform(0.3, 0.7))
            )
    return peaks, truth


def test_static_spot_is_found() -> None:
    peaks, _ = _scene()
    cells = bt.static_cells(peaks, FPS, cell=16)
    assert (900 // 16, 120 // 16) in cells
    assert len(cells) <= 4


def test_path_follows_the_ball() -> None:
    peaks, truth = _scene()
    path, stats = bt.track(peaks, FPS, max_speed=900.0, radius=8.0, min_score=0.4)
    seen = {p.frame: p for p in path}
    near = [
        f for f, (x, y) in truth.items() if f in seen and np.hypot(seen[f].x - x, seen[f].y - y) < 6
    ]
    wrong = [
        p
        for p in path
        if p.frame not in truth or np.hypot(p.x - truth[p.frame][0], p.y - truth[p.frame][1]) >= 6
    ]
    assert len(near) >= 0.8 * len(truth), stats
    assert len(wrong) <= 0.05 * len(path), stats
    assert not any(abs(p.x - 900) < 10 and abs(p.y - 120) < 10 for p in path)


def test_teleport_is_not_linked() -> None:
    peaks = [bt.Peak(f, 100.0 + 4 * f, 200.0, 0.7) for f in range(10)]
    peaks += [bt.Peak(f, 1000.0 + 4 * f, 600.0, 0.7) for f in range(10, 20)]
    tracklets = bt.link(peaks, FPS, max_speed=900.0, radius=8.0)
    assert sorted(len(t.peaks) for t in tracklets) == [10, 10]
    # one ball: the far piece cannot follow the first within a frame, so it stands alone
    peaks += [bt.Peak(f, 1000.0 + 4 * f, 600.0, 0.9) for f in range(20, 25)]
    path, stats = bt.track(peaks, FPS, max_speed=900.0, radius=8.0)
    assert stats["chosen"] == 1
    assert {p.frame for p in path} == set(range(10, 25))


def test_empty() -> None:
    path, stats = bt.track([], FPS, max_speed=900.0, radius=8.0)
    assert path == [] and stats["chosen"] == 0
