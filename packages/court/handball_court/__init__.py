"""Handball court geometry shared by API, worker and ML.

The geometry is generated from ``packages/court/spec/court.json``. Coordinates are in
metres: x = 0 at the left goal line to 40, y = 0 at the bottom sideline to 20.
"""

from handball_court.geometry import (
    COURT,
    Court,
    distance_to_attacked_goal,
    in_goal_area,
    normalize_to_attack,
)

__all__ = ["COURT", "Court", "distance_to_attacked_goal", "in_goal_area", "normalize_to_attack"]
