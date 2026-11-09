"""Shot positions of overlay goals from the tracks."""

from __future__ import annotations

from typing import Any

from handball_vision.shots import locate_goal_shots
from handball_vision.tracking import TrackPoint

FPS = 10.0


def _run(track: int, xs: list[float], y: float, start: int) -> list[TrackPoint]:
    return [TrackPoint(track, start + k, x, y, 0.0, 0.0, True, 0) for k, x in enumerate(xs)]


def test_the_scorer_by_number_else_the_nearest_attacker() -> None:
    # attack on the goal at x = 0: #7 runs in to 6 m, a teammate goes deeper (4 m)
    pts = _run(1, [14 - 0.1 * k for k in range(80)], 12.0, 0) + _run(
        2, [12 - 0.1 * k for k in range(80)], 6.0, 0
    )
    teams: dict[int, dict[str, Any]] = {1: {"label": "away", "number": 7}, 2: {"label": "away"}}
    goal = {"t_ms": 9000, "side": "right", "scorer": {"number": 7, "name": "Amy H"}}
    (g,) = locate_goal_shots(pts, teams, FPS, [goal], own_is_home=True)
    shot = g["shot"]
    assert shot["method"] == "number" and shot["track_id"] == 1
    # mirrored to the goal at x = 40: 14 - 7.9 = 6.1 m out, y mirrored too
    assert abs(shot["x"] - (40 - 6.1)) < 0.01 and shot["y"] == 8.0
    unnamed = {"t_ms": 9000, "side": "right"}
    (g2,) = locate_goal_shots(pts, teams, FPS, [unnamed], own_is_home=True)
    assert g2["shot"]["method"] == "nearest" and g2["shot"]["track_id"] == 2


def test_no_attackers_no_position() -> None:
    (g,) = locate_goal_shots([], {}, FPS, [{"t_ms": 5000, "side": "left"}], own_is_home=False)
    assert "shot" not in g
