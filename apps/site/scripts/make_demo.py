"""Fictional demo match for the marketing site (addendum 01, 4.13).

The events are drawn from a seeded random generator, not from a real game; the figures are computed
with the same metrics package as the app, so the demo shows real calculations on invented input.
Run: uv run python apps/site/scripts/make_demo.py [--check]
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path
from typing import Any

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


def build() -> dict[str, Any]:
    rnd = random.Random(2026)  # noqa: S311 (seeded demo data, not security)
    events: list[Event] = []
    for period in (1, 2):
        clock = (period - 1) * 1800.0
        while True:
            clock += rnd.uniform(25, 45)
            if clock >= period * 1800:
                break
            side = Side.OWN if rnd.random() < 0.52 else Side.OPPONENT
            if rnd.random() < 0.18:
                events.append(
                    Event(
                        id=f"e{len(events)}",
                        type=EventType.TURNOVER,
                        side=side,
                        period=period,
                        clock_s=round(clock),
                        turnover_type=rnd.choice(["bad_pass", "steps", "catch_error"]),
                    )
                )
                continue
            kind = rnd.choices(list(SPOTS), weights=[18, 45, 15, 12, 10])[0]
            bx, by = rnd.choice(SPOTS[kind])
            x = round(bx + rnd.uniform(-1, 1), 1)
            y = round(min(19.5, max(0.5, by + rnd.uniform(-1.2, 1.2))), 1)
            if kind == "penalty":
                x, y = 33.0, 10.0
            xg = expected_goal(x, y, TYPES[kind])
            r = rnd.random()
            outcome = "goal" if r < xg else rnd.choice(["save", "save", "miss", "blocked", "post"])
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
                    number=rnd.choice([3, 5, 7, 9, 11, 14, 18, 22]),
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
        "own": "HC Beispiel",
        "opponent": "TV Muster",
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
