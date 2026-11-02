import subprocess
import sys
from pathlib import Path

import pytest

from handball_court import COURT, distance_to_attacked_goal, in_goal_area, normalize_to_attack

ROOT = Path(__file__).resolve().parent.parent


def test_dimensions() -> None:
    assert COURT.length == 40.0
    assert COURT.width == 20.0
    assert COURT.center == (20.0, 10.0)
    assert COURT.keypoints["post_right_low"] == (40.0, 8.5)
    assert COURT.keypoints["post_right_high"] == (40.0, 11.5)


def test_normalize_attack_right_is_identity() -> None:
    assert normalize_to_attack(12.0, 3.0, attacking_right=True) == (12.0, 3.0)


def test_normalize_attack_left_rotates() -> None:
    assert normalize_to_attack(5.0, 3.0, attacking_right=False) == (35.0, 17.0)


@pytest.mark.parametrize(
    ("x", "y", "expected"),
    [
        (33.0, 10.0, 7.0),  # penalty mark
        (40.0, 2.5, 6.0),  # goal area line meets goal line
        (34.0, 8.5, 6.0),  # straight part of goal area line
    ],
)
def test_distance_to_goal(x: float, y: float, expected: float) -> None:
    assert distance_to_attacked_goal(x, y) == pytest.approx(expected)


def test_goal_area_lines_have_radius() -> None:
    for x, y in COURT.lines["goal_area_right"]:
        assert distance_to_attacked_goal(x, y) == pytest.approx(6.0, abs=1e-3)


def test_in_goal_area() -> None:
    assert in_goal_area(36.0, 10.0)
    assert not in_goal_area(31.0, 10.0)


def test_generated_file_is_fresh() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "generate.py"), "--check"], check=False
    )
    assert result.returncode == 0
