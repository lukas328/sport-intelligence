"""Shot zones (BRIEF 4.3) from spec/zones.json. Mirrors src/zones.ts (shared test vectors)."""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path
from typing import Any

from handball_court.geometry import COURT, distance_to_attacked_goal

_HERE = Path(__file__).resolve().parent
_CANDIDATES = (_HERE / "zones.json", _HERE.parent / "spec" / "zones.json")


@cache
def spec() -> dict[str, Any]:
    for p in _CANDIDATES:
        if p.exists():
            data: dict[str, Any] = json.loads(p.read_text())
            return data
    raise FileNotFoundError("zones.json not found")


def shot_zone(x: float, y: float, *, penalty: bool = False, fast_break: bool = False) -> str:
    """Zone of a shot from its normalised position (attacked goal at x = 40)."""
    s = spec()
    if penalty:
        return "penalty"
    if fast_break:
        return "fast_break"
    d = distance_to_attacked_goal(x, y)
    if d > s["long_range_m"]:
        return "long_range"
    dy = y - COURT.width / 2
    side = "left" if dy > 0 else "right"
    wing = s["wing"]
    if x >= wing["min_x"] and abs(dy) >= wing["min_abs_dy"] and d <= wing["max_distance_m"]:
        return f"wing_{side}"
    half_width = s["centre_half_width_m"]
    if d <= s["circle_max_m"]:
        band = "circle"
    elif d <= s["back_min_m"]:
        band = "half"
    else:
        band = "back"
    if abs(dy) < half_width[band]:
        return f"{band}_centre"
    return f"{band}_{side}"


GOAL_ZONES = ("TL", "TC", "TR", "ML", "MC", "MR", "BL", "BC", "BR")


def mirror_goal_zone(zone: str) -> str:
    """Shooter's view <-> goalkeeper's view (BRIEF 4.4): left and right swap."""
    if zone not in GOAL_ZONES:
        raise ValueError(f"unknown goal zone {zone}")
    return zone[0] + {"L": "R", "R": "L", "C": "C"}[zone[1]]
