"""Holder, possessions, passes and turnovers from a ball path and player boxes."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

from handball_vision import ballpossession as bp
from handball_vision.detection import Detection

FPS = 25.0
TEAMS = {1: "home", 2: "home", 3: "away", 4: "home_gk"}


def _box(tid: int, x: float, y: float = 300.0) -> bp.Box:
    return (tid, x - 20, y - 90, x + 20, y)


def test_holder_prefers_upper_body_and_ignores_far_balls() -> None:
    boxes = [_box(1, 100), _box(3, 130)]
    assert bp.holder((100, 240), boxes) == 1
    assert bp.holder((128, 230), boxes) == 3
    assert bp.holder((100, 196), boxes) == 1  # overhead
    assert bp.holder((400, 240), boxes) is None


def test_pass_then_interception() -> None:
    ball: dict[int, tuple[float, float]] = {}
    boxes: dict[int, list[bp.Box]] = {}
    for f in range(0, 150):
        boxes[f] = [_box(1, 100), _box(2, 500), _box(3, 800)]
        if f < 30:
            ball[f] = (100, 240)  # player 1 holds
        elif f < 45:
            ball[f] = (100 + (f - 30) * 26, 150)  # in flight above the boxes
        elif f < 90:
            ball[f] = (500, 240)  # player 2 holds
        elif f < 100:
            ball[f] = (500 + (f - 90) * 30, 150)
        else:
            ball[f] = (800, 240)  # opponent 3 has it
        if f == 60:
            ball[f] = (100, 240)  # one wrong frame: not a possession
    by = bp.holders(ball, boxes)
    pos = bp.possessions(by, TEAMS, FPS)
    assert [(p.track_id, p.first, p.last) for p in pos] == [(1, 0, 29), (2, 45, 89), (3, 100, 149)]
    moves = bp.transfers(pos, FPS)
    assert [(m.kind, m.from_track, m.to_track) for m in moves] == [
        ("pass", 1, 2),
        ("turnover", 2, 3),
    ]
    s = bp.summary(pos, moves, FPS)
    assert s["passes"] == {"home": 1} and s["turnovers"] == {"home": 1}
    assert s["ball_time_s"] == {"home": 3.0, "away": 2.0}


def test_goalkeeper_pass_counts_for_the_team() -> None:
    pos = [bp.Possession(4, "home_gk", 0, 20), bp.Possession(1, "home", 40, 60)]
    assert [m.kind for m in bp.transfers(pos, FPS)] == ["pass"]


def test_long_loss_is_not_a_pass() -> None:
    pos = [bp.Possession(1, "home", 0, 20), bp.Possession(2, "home", 200, 260)]
    assert bp.transfers(pos, FPS) == []


def _observed() -> tuple[Any, Any]:
    """12 s at 25 fps: player 1 runs with the ball for 6 s, then the clock stands; from 8 s on
    player 3 plays with a warm-up ball. Fixed camera (canvas = frame)."""
    eye = np.eye(3)
    motion = SimpleNamespace(
        frame_size=(1280, 720),
        frame_to_canvas=lambda f: eye,
        canvas_to_frame=lambda f: eye,
    )
    frames, points = [], []
    for f in range(300):
        x1, x3 = 100 + 2 * f, 1100 - 2 * f
        people = [
            Detection(x1 - 20, 210, x1 + 20, 300, 0.9),
            Detection(x3 - 20, 210, x3 + 20, 300, 0.9),
        ]
        bx = x1 if f < 150 else x3
        balls = [] if 150 <= f < 200 else [Detection(bx - 4, 236, bx + 4, 244, 0.9, "ball")]
        frames.append(SimpleNamespace(index=f, people=people, balls=balls))
        points += [
            SimpleNamespace(track_id=1, frame=f, det_index=0),
            SimpleNamespace(track_id=3, frame=f, det_index=1),
        ]
    obs = SimpleNamespace(motion=motion, frames=frames, fps=FPS)
    result = SimpleNamespace(points=points, teams={1: {"label": "home"}, 3: {"label": "away"}})
    return obs, result


@pytest.mark.parametrize("play", [None, []])
def test_without_clock_every_ball_counts(play: list[tuple[int, int]] | None) -> None:
    obs, result = _observed()
    out = bp.from_observations(obs, result, play=play)
    assert out is not None and out["ball_gated_by_clock"] is False and out["in_play_s"] is None
    assert {p["track_id"] for p in out["possessions"]} == {1, 3}


def test_balls_while_the_clock_stands_are_ignored() -> None:
    obs, result = _observed()
    out = bp.from_observations(obs, result, play=[(0, 6000)])
    assert out is not None and out["ball_gated_by_clock"] is True and out["in_play_s"] == 6.0
    assert {p["track_id"] for p in out["possessions"]} == {1}
    assert out["summary"]["ball_time_s"].keys() == {"home"}
    # the clock never ran while a ball was seen: no ball time at all, but said so
    out = bp.from_observations(obs, result, play=[(20_000, 30_000)])
    assert out is not None and out["ball_gated_by_clock"] is True and out["possessions"] == []
