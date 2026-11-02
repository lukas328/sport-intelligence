from __future__ import annotations

import json
import math
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
_CANDIDATES = (
    _HERE / "court_geometry.json",  # installed wheel
    _HERE.parent / "generated" / "court_geometry.json",  # editable / workspace
)

Point = tuple[float, float]


@dataclass(frozen=True, slots=True)
class Court:
    length: float
    width: float
    goal_width: float
    goal_height: float
    goal_area_radius: float
    free_throw_radius: float
    lines: dict[str, list[Point]]
    keypoints: dict[str, Point]

    @property
    def center(self) -> Point:
        return (self.length / 2, self.width / 2)


@cache
def _load() -> dict[str, Any]:
    for path in _CANDIDATES:
        if path.exists():
            data: dict[str, Any] = json.loads(path.read_text())
            return data
    raise FileNotFoundError("court_geometry.json not found, run `make court`")


def load_court() -> Court:
    d = _load()
    return Court(
        length=float(d["length"]),
        width=float(d["width"]),
        goal_width=float(d["goal"]["width"]),
        goal_height=float(d["goal"]["height"]),
        goal_area_radius=float(d["goal_area_radius"]),
        free_throw_radius=float(d["free_throw_radius"]),
        lines={k: [(float(x), float(y)) for x, y in v] for k, v in d["lines"].items()},
        keypoints={k: (float(v[0]), float(v[1])) for k, v in d["keypoints"].items()},
    )


COURT = load_court()


def normalize_to_attack(x: float, y: float, attacking_right: bool, court: Court = COURT) -> Point:
    """Normalise a position so that the attacked goal is always at x = length.

    If the team attacks the left goal, the position is rotated by 180 degrees around the
    centre point (mirrors both x and y, keeping left/right wing semantics consistent).
    """
    if attacking_right:
        return (x, y)
    return (court.length - x, court.width - y)


def distance_to_attacked_goal(x: float, y: float, court: Court = COURT) -> float:
    """Distance (m) from a normalised position to the nearest point of the goal at x = length."""
    half = court.goal_width / 2
    cy = court.width / 2
    gy = min(max(y, cy - half), cy + half)
    return math.hypot(court.length - x, y - gy)


def in_goal_area(x: float, y: float, court: Court = COURT) -> bool:
    """True if the normalised position is inside the 6 m goal area of the goal at x = length."""
    return distance_to_attacked_goal(x, y, court) < court.goal_area_radius
