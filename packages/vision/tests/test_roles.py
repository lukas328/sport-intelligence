"""Role votes combined with kit colours, overlap in time and goal presence."""

from __future__ import annotations

import numpy as np

from handball_vision import roles as rl

HOME = [40.0, 10.0, 10.0]  # dark kit (Lab)
AWAY = [90.0, 0.0, 0.0]  # white kit
REF = [60.0, 60.0, 60.0]  # pink referee shirt


def _team(label: str, lab: list[float]) -> dict[str, object]:
    return {"label": label, "lab": lab, "confidence": 0.8, "samples": 20}


def test_referee_needs_its_own_colour_and_at_most_two_at_a_time() -> None:
    team_out = {
        1: _team("home", HOME),
        2: _team("home", HOME),
        3: _team("away", AWAY),
        4: _team("away", AWAY),
        5: _team("home", HOME),
        6: _team("away", REF),
        7: _team("home", REF),
        8: _team("away", REF),
    }
    roles = {
        5: np.array([0.2, 0.0, 0.8]),  # dark player that looks like a referee: same colour as home
        6: np.array([0.1, 0.0, 0.9]),
        7: np.array([0.2, 0.1, 0.7]),
        8: np.array([0.3, 0.0, 0.65]),  # third referee at the same time: the least certain loses
    }
    spans = {5: (0, 100), 6: (0, 100), 7: (0, 100), 8: (0, 100)}
    changes = rl.apply_roles(team_out, roles, spans, {}, {})
    assert changes == {6: "referee", 7: "referee"}


def test_short_goalkeeper_track_joins_the_defending_team() -> None:
    team_out = {
        1: _team("home", HOME),
        2: _team("home", HOME),
        3: _team("away", AWAY),
        4: _team("away", AWAY),
        9: _team("away", [70.0, -40.0, 50.0]),
    }
    roles = {9: np.array([0.1, 0.8, 0.1])}
    changes = rl.apply_roles(team_out, roles, {9: (0, 50)}, {9: 0.9}, {9: "home"})
    assert changes == {9: "home_gk"}
    # away from the goal it stays as it is
    assert rl.apply_roles(team_out, roles, {9: (0, 50)}, {9: 0.2}, {9: "home"}) == {}


def test_goal_presence() -> None:
    pts = [(t, 1, 2.0, 10.0) for t in range(10)] + [(t, 2, 20.0, 10.0) for t in range(10)]
    pts += [(t, 3, 38.0, 9.0) for t in range(6)] + [(t, 3, 20.0, 9.0) for t in range(6, 10)]
    share, side = rl.goal_presence(pts)
    assert share[1] == 1.0 and side[1] == "left"
    assert share[2] == 0.0 and 2 not in side
    assert abs(share[3] - 0.6) < 1e-9 and side[3] == "right"


def test_track_roles_needs_enough_looks() -> None:
    out = rl.track_roles({1: [np.array([1.0, 0, 0])] * 3, 2: [np.array([0, 0, 1.0])] * 5})
    assert list(out) == [2]


def test_referee_at_the_goal_line_and_colour_only_referees() -> None:
    team_out = {
        1: _team("home", HOME),
        2: _team("home", HOME),
        3: _team("away", AWAY),
        4: _team("away", AWAY),
        10: _team("away_gk", REF),  # the position rule took a referee at the goal line for a keeper
        11: _team("referee", [42.0, 9.0, 11.0]),  # kit colour said referee, it is a home player
    }
    roles = {10: np.array([0.2, 0.0, 0.8]), 11: np.array([0.95, 0.0, 0.05])}
    changes = rl.apply_roles(team_out, roles, {10: (0, 9), 11: (0, 9)}, {10: 0.9}, {})
    assert changes == {10: "referee", 11: "home"}
