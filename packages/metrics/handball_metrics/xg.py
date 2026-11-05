"""Expected goals (BRIEF 4.8). v1: a logistic prior, an estimate to be refitted on own data.

logit p = b0 + b_d * distance + b_a * |angle| + type and situation terms

Coefficients are set so the model reproduces typical conversion rates reported for handball
(7 m roughly 75 %, wing roughly 50 %, 6 m centre roughly 65 %, 9 m backcourt roughly 35 %, fast
break roughly 80 %, empty net long shots very high). They are a prior, not a fitted model; the
`version` is stored with every figure so later models can be compared.

A shot needs its position (penalties excepted): goals without one (official report, score
overlay) have no xG, and sums cover only the shots that have it (see `xg_coverage` in stats).
"""

from __future__ import annotations

import math

from handball_court import distance_to_attacked_goal

VERSION = "prior-1"
B0, B_DIST, B_ANGLE = 2.15, -0.235, -0.45
TYPE_TERMS = {"fast_break": 1.6, "empty_net": 5.0, "pivot": 0.2, "wing": 0.0}
PENALTY = 0.75


def expected_goal(
    x: float | None, y: float | None, shot_type: str | None = None, *, defenders_close: int = 0
) -> float | None:
    """Goal probability of a shot, None when its position is unknown (no estimate)."""
    if shot_type == "penalty":
        return PENALTY
    if x is None or y is None:
        return None
    d = distance_to_attacked_goal(x, y)
    angle = abs(math.atan2(y - 10.0, max(0.1, 40.0 - x)))  # 0 = central, pi/2 = from the goal line
    logit = (
        B0
        + B_DIST * d
        + B_ANGLE * angle * angle
        + TYPE_TERMS.get(shot_type or "", 0.0)
        - 0.35 * defenders_close
    )
    return round(1 / (1 + math.exp(-logit)), 4)
