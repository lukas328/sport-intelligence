"""Fictional demo match for the marketing site (addendum 01, 4.13).

The events are drawn from a seeded random generator, not from a real game; the figures are computed
with the same metrics package as the app, so the demo shows real calculations on invented input.
Run: uv run python apps/site/scripts/make_demo.py [--check]
"""

from __future__ import annotations

import json
import math
import random
import sys
from pathlib import Path
from typing import Any

from handball_court.geometry import COURT, distance_to_attacked_goal
from handball_court.zones import spec as zone_spec
from handball_metrics.model import Event, EventType, Side
from handball_metrics.stats import compute_match_stats
from handball_metrics.xg import expected_goal

OUT = Path(__file__).resolve().parents[1] / "public" / "demo" / "match.json"
SPOTS = {
    "wing": [(38.5, 1.5), (38.5, 18.5)],
    "back": [(30.5, 5.5), (30.0, 10.0), (30.5, 14.5)],
    "pivot": [(33.6, 9.0), (33.6, 11.0)],
    "fast_break": [(34.0, 10.0)],
    "penalty": [(33.0, 10.0)],
}
TYPES = {
    "wing": "wing",
    "back": "jump_shot",
    "pivot": "pivot",
    "fast_break": "fast_break",
    "penalty": "penalty",
}


# where a shot is taken: the take-off spot, outside the goal area (only the goalkeeper stands in it;
# wings and the pivot jump into it, but they take off before the 6 m line)
MIN_SHOT_DISTANCE = COURT.goal_area_radius + 0.3


def outside_goal_area(x: float, y: float) -> tuple[float, float]:
    """Push a spot straight away from the goal until it is at least MIN_SHOT_DISTANCE away."""
    d = distance_to_attacked_goal(x, y)
    if d >= MIN_SHOT_DISTANCE:
        return x, y
    half = COURT.goal_width / 2
    cy = COURT.width / 2
    gx, gy = COURT.length, min(max(y, cy - half), cy + half)
    if d < 1e-6:
        return round(gx - MIN_SHOT_DISTANCE, 1), y
    k = MIN_SHOT_DISTANCE / d
    # round away from the goal so that the rounded spot stays outside as well
    nx = gx + (x - gx) * k
    ny = gy + (y - gy) * k
    nx = math.floor(nx * 10) / 10
    ny = math.ceil(ny * 10) / 10 if ny > gy else math.floor(ny * 10) / 10
    return nx, ny


# The story of the start page (docs/ux-test/livegang/BEFUNDE-2.md, W22, W29, L7): a Saturday home
# game, lost 27:29 (13:15 at half-time), and the opponent scored 11 of its 29 goals over the right
# wing. The plan fixes what the story needs (score, half-time, goals by position); the seeded
# generator places the shots, the times, the misses and the numbers. With the app's rule for the
# three things (apps/web/src/lib/three-things.ts) the match gives all three kinds: 11 of 29 conceded
# over the right wing, 5 conceded after fast breaks, 9 of 27 own goals from the pivot.
SEED = 2100
# the invented demo club and its opponent, as in scripts/seed.py (no real place in a name)
OWN = "HC Tannengrün"
OPPONENT = "TSV Nachtwind"
# goals per half by kind: (own, opponent); the opponent's wing goals all come from its right wing
PLAN: dict[int, dict[str, tuple[int, int]]] = {
    1: {"wing": (3, 5), "back": (4, 4), "pivot": (4, 1), "fast_break": (1, 3), "penalty": (1, 2)},
    2: {"wing": (2, 6), "back": (4, 3), "pivot": (5, 2), "fast_break": (2, 2), "penalty": (1, 1)},
}
# shots that did not go in, per half: (own, opponent)
MISSES = {1: (12, 10), 2: (13, 11)}
# the opponent's right wing: mostly number 7, four times the substitute 22
RIGHT_WING = [7, 7, 22, 7, 7, 7, 22, 7, 22, 7, 22]


# a pivot shot is taken from the circle band just outside the goal area (packages/court zones:
# at most circle_max_m from the goal), so the app counts it «vom Kreis» from its spot alone
CIRCLE_SHOT_DISTANCE = (MIN_SHOT_DISTANCE + zone_spec()["circle_max_m"]) / 2


def in_circle_band(x: float, y: float) -> tuple[float, float]:
    """Pull a spot straight towards the goal until it is CIRCLE_SHOT_DISTANCE away (if farther)."""
    d = distance_to_attacked_goal(x, y)
    if d <= CIRCLE_SHOT_DISTANCE:
        return x, y
    half = COURT.goal_width / 2
    cy = COURT.width / 2
    gx, gy = COURT.length, min(max(y, cy - half), cy + half)
    k = CIRCLE_SHOT_DISTANCE / d
    return round(gx + (x - gx) * k, 1), round(gy + (y - gy) * k, 1)


def spot(rnd: random.Random, kind: str, side: Side) -> tuple[float, float]:
    """A shot spot for a kind; the opponent's wing goals come from its right wing (y near 0)."""
    if kind == "penalty":
        return 33.0, 10.0
    choices = [SPOTS["wing"][0]] if kind == "wing" and side == Side.OPPONENT else SPOTS[kind]
    bx, by = rnd.choice(choices)
    x = round(bx + rnd.uniform(-1, 1), 1)
    y = round(min(19.5, max(0.5, by + rnd.uniform(-1.2, 1.2))), 1)
    x, y = outside_goal_area(x, y)
    return in_circle_band(x, y) if kind == "pivot" else (x, y)


# Our shooters are the seeded squad of Herren 1 (scripts/seed.py SQUAD), by position and only
# players with a consent for video analysis, so the app's demo club shows the same numbers.
OWN_NUMBERS = {
    "pivot": [11, 22, 11],
    "wing_left": [3, 21],
    "wing_right": [5],
    "back_left": [7, 17],
    "back_centre": [9],
    "back_right": [10, 25],
    "fast_break": [5, 3, 21],
    "penalty": [10, 7],
}


def own_number(kind: str, y: float, used: dict[str, int]) -> int:
    """The next shooter of our team for a kind of shot at width y (left is y > 10)."""
    if kind == "wing":
        kind = "wing_left" if y > COURT.width / 2 else "wing_right"
    elif kind == "back":
        kind = "back_left" if y > 13 else "back_right" if y < 7 else "back_centre"
    numbers = OWN_NUMBERS[kind]
    n = used.get(kind, 0)
    used[kind] = n + 1
    return numbers[n % len(numbers)]


def even_out(raw: list[float], start: float) -> list[float]:
    """Shot times of a half, drawn at random but closer to an even pace: pure chance put seven goals
    into the first four minutes, which no coach believes. The order (and so every count) stays."""
    n = len(raw)
    even = [start + 90 + (k + 0.5) * 1690 / n for k in range(n)]
    return [0.3 * r + 0.7 * e for r, e in zip(raw, even, strict=True)]


def build(seed: int = SEED) -> dict[str, Any]:
    rnd = random.Random(seed)  # noqa: S311 (seeded demo data, not security)
    events: list[Event] = []
    wing_numbers = iter(RIGHT_WING)
    shooters: dict[str, int] = {}
    for period in (1, 2):
        shots: list[tuple[Side, str, bool]] = []
        for kind, (own, opp) in PLAN[period].items():
            shots += [(Side.OWN, kind, True)] * own + [(Side.OPPONENT, kind, True)] * opp
        for side, n in zip((Side.OWN, Side.OPPONENT), MISSES[period], strict=True):
            kinds = rnd.choices(["wing", "back", "pivot"], weights=[2, 6, 2], k=n)
            shots += [(side, kind, False) for kind in kinds]
        rnd.shuffle(shots)
        start = (period - 1) * 1800.0
        clocks = even_out(sorted(rnd.uniform(start + 20, start + 1790) for _ in shots), start)
        for clock, (side, kind, goal) in zip(clocks, shots, strict=True):
            x, y = spot(rnd, kind, side)
            number = rnd.choice([3, 5, 9, 11, 14, 18])
            if goal and side == Side.OPPONENT and kind == "wing":
                number = next(wing_numbers)
            if side == Side.OWN:
                number = own_number(kind, y, shooters)
            outcome = "goal" if goal else rnd.choice(["save", "save", "miss", "blocked", "post"])
            events.append(
                Event(
                    id=f"e{len(events)}",
                    type=EventType.SHOT,
                    side=side,
                    period=period,
                    clock_s=round(clock),
                    x=x,
                    y=y,
                    outcome=outcome,
                    shot_type=TYPES[kind],
                    number=number,
                    goal_zone=rnd.choice(["TL", "TR", "BL", "BR", "MC", "BC", "ML", "MR"]),
                )
            )
    stats = compute_match_stats(events)
    out_events = [
        {
            "id": e.id,
            "type": str(e.type),
            "side": str(e.side),
            "period": e.period,
            "clock_s": e.clock_s,
            "x": e.x,
            "y": e.y,
            "outcome": e.outcome,
            "shot_type": e.shot_type,
            "number": e.number,
            "xg": (
                round(expected_goal(e.x, e.y, e.shot_type), 2) if e.type == EventType.SHOT else None
            ),
        }
        for e in events
    ]
    return {
        "fictional": True,
        "own": OWN,
        "opponent": OPPONENT,
        "events": out_events,
        "stats": {k: stats[k] for k in ("own", "opponent", "timeline", "versions")},
    }


def main() -> int:
    text = json.dumps(build(), indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    if "--check" in sys.argv:
        if not OUT.exists() or OUT.read_text() != text:
            print(f"{OUT} is out of date, run make demo", file=sys.stderr)
            return 1
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
