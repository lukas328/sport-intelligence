"""Where goals were scored from (BRIEF 7.2 stages 9/10, without the ball).

The overlay says when a goal fell, for which team and, after the goal, who scored ("7 Lisa
ZIMMERLI", scoreboard.py). The tracks know where every player was. So the shot position of a goal
is where the scorer was closest to the attacked goal in the seconds before the overlay changed:

- with the scorer's shirt number and a track carrying that number (numbers.py, reid.py): that
  track; method "number";
- otherwise the attacker who came closest to the attacked goal in that window; method "nearest",
  a rough estimate.

Positions are normalised like all shot positions: attacked goal at x = 40.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import numpy as np

from handball_vision.tracking import TrackPoint

WINDOW_MS = 10_000
LENGTH, WIDTH = 40.0, 20.0


def _goal_distance(x: float, y: float, gx: float) -> float:
    gy = min(max(y, 8.5), 11.5)
    return float(np.hypot(x - gx, y - gy))


def locate_goal_shots(
    points: list[TrackPoint],
    teams: dict[int, dict[str, Any]],
    fps: float,
    goals: list[dict[str, Any]],
    own_is_home: bool,
) -> list[dict[str, Any]]:
    """Copies of the overlay goals with a "shot" entry where a position could be found."""
    by_frame: dict[int, list[TrackPoint]] = defaultdict(list)
    for p in points:
        if p.observed:
            by_frame[p.frame].append(p)
    out = []
    for g in goals:
        g = dict(g)
        team = "home" if (g.get("side") == "left") == own_is_home else "away"
        t1 = int(g["t_ms"] * fps / 1000)
        t0 = t1 - int(WINDOW_MS * fps / 1000)
        window = [p for f in range(t0, t1 + 1) for p in by_frame.get(f, [])]
        attackers = [p for p in window if teams.get(p.track_id, {}).get("label") == team]
        if not attackers:
            out.append(g)
            continue
        gx = LENGTH if np.mean([p.x for p in attackers]) > LENGTH / 2 else 0.0
        number = (g.get("scorer") or {}).get("number")
        scorer = (
            [p for p in attackers if teams[p.track_id].get("number") == number]
            if number is not None
            else []
        )
        pool, method = (scorer, "number") if scorer else (attackers, "nearest")
        best = min(pool, key=lambda p: _goal_distance(p.x, p.y, gx))
        x, y = (best.x, best.y) if gx == LENGTH else (LENGTH - best.x, WIDTH - best.y)
        g["shot"] = {
            "t_ms": round(best.frame * 1000 / fps),
            "x": round(float(x), 2),
            "y": round(float(y), 2),
            "track_id": best.track_id,
            "method": method,
            "distance_m": round(_goal_distance(best.x, best.y, gx), 1),
        }
        out.append(g)
    return out
