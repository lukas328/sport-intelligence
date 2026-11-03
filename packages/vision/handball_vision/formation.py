"""Defence formation from court positions (BRIEF 8.3 "Abwehrsystem erkennen", M6).

Rule-based baseline, no training data needed. Every 2 s window (sampled at 5 Hz) and team:

1. Which goal does the team defend? The goal its goalkeeper track is closest to; without a goalkeeper
   track, the goal most of its field players are close to.
2. Is the defence set? At least 5 field players within 12 m of that goal and at least 4 opponents in
   that half. Otherwise the window is "transition" and not classified.
3. Depth of every defender = distance from the goal line. With `A` = players deeper than 8 m (advanced)
   and `D` = deeper than 10.5 m:
   - A == 0: 6-0, A == 1: 5-1, A == 2: 4-2,
   - A >= 3 with at least one D and at most 3 advanced: 3-2-1, otherwise 3-3,
   - 4 or more players deeper than 10.5 m: "open" (man-to-man or very offensive).

Consecutive windows with the same label merge into segments; segments shorter than 4 s are dropped.
The result is labelled `heuristic` and shown as an estimate.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np

WINDOW_MS = 2000
STEP_MS = 200
MIN_SEGMENT_MS = 4000
NEAR_GOAL_M = 12.0
ADVANCED_M = 8.0
DEEP_M = 10.5
LENGTH = 40.0


@dataclass(frozen=True)
class Sample:
    t_ms: int
    track: int
    team: str  # home, home_gk, away, away_gk, referee
    x: float
    y: float


@dataclass(frozen=True)
class Segment:
    team: str  # home or away
    formation: str
    start_ms: int
    end_ms: int
    confidence: float

    def to_dict(self) -> dict[str, object]:
        return {
            "team": self.team,
            "formation": self.formation,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "confidence": round(self.confidence, 2),
        }


def classify(depths: list[float]) -> str:
    deep = sum(d > DEEP_M for d in depths)
    adv = sum(d > ADVANCED_M for d in depths)
    if deep >= 4:
        return "open"
    if adv == 0:
        return "6-0"
    if adv == 1:
        return "5-1"
    if adv == 2:
        return "4-2"
    if deep >= 1 and adv <= 3:
        return "3-2-1"
    return "3-3"


def _window_label(samples: list[Sample], team: str) -> str | None:
    other = "away" if team == "home" else "home"
    field = _mean_by_track([s for s in samples if s.team == team])
    keepers = _mean_by_track([s for s in samples if s.team == f"{team}_gk"])
    attackers = _mean_by_track([s for s in samples if s.team == other])
    if len(field) < 5:
        return None
    if keepers:
        gx = float(np.mean([p[0] for p in keepers.values()]))
        goal = 0.0 if gx < LENGTH / 2 else LENGTH
    else:
        near_left = sum(_dist_goal(p, 0.0) < NEAR_GOAL_M for p in field.values())
        near_right = sum(_dist_goal(p, LENGTH) < NEAR_GOAL_M for p in field.values())
        goal = 0.0 if near_left >= near_right else LENGTH
    near = [p for p in field.values() if _dist_goal(p, goal) < NEAR_GOAL_M + 3]
    set_defence = sum(_dist_goal(p, goal) < NEAR_GOAL_M for p in field.values()) >= 5
    opp_in_half = sum((p[0] < LENGTH / 2) == (goal == 0.0) for p in attackers.values())
    if not set_defence or opp_in_half < 4:
        return None
    # the six defenders closest to the goal
    near.sort(key=lambda p: _dist_goal(p, goal))
    return classify([abs(p[0] - goal) for p in near[:6]])


def _dist_goal(p: tuple[float, float], goal_x: float) -> float:
    return float(np.hypot(p[0] - goal_x, max(0.0, abs(p[1] - 10.0) - 1.5)))


def _mean_by_track(samples: Iterable[Sample]) -> dict[int, tuple[float, float]]:
    acc: dict[int, list[tuple[float, float]]] = {}
    for s in samples:
        acc.setdefault(s.track, []).append((s.x, s.y))
    return {
        k: (float(np.mean([p[0] for p in v])), float(np.mean([p[1] for p in v])))
        for k, v in acc.items()
    }


def detect(samples: list[Sample]) -> list[Segment]:
    """Formation segments for both teams from position samples (any order)."""
    if not samples:
        return []
    ordered = sorted(samples, key=lambda s: s.t_ms)
    times = np.array([s.t_ms for s in ordered])
    end = int(times[-1])
    out: list[Segment] = []
    for team in ("home", "away"):
        labels: list[tuple[int, str | None]] = []
        for start in range(int(times[0]), end - WINDOW_MS + 1, WINDOW_MS):
            lo, hi = np.searchsorted(times, [start, start + WINDOW_MS])
            # 5 Hz is plenty for formations: keep one frame per 200 ms of 25 fps data
            window = [s for s in ordered[lo:hi] if s.t_ms % STEP_MS < 40]
            labels.append((start, _window_label(window, team)))
        out.extend(_segments(team, labels))
    return sorted(out, key=lambda s: (s.start_ms, s.team))


def _segments(team: str, labels: list[tuple[int, str | None]]) -> list[Segment]:
    segs: list[Segment] = []
    i = 0
    while i < len(labels):
        start, lab = labels[i]
        if lab is None:
            i += 1
            continue
        j = i
        votes: Counter[str] = Counter()
        # allow single deviating windows inside a segment (noise), stop at two in a row
        while j < len(labels):
            cur = labels[j][1]
            nxt = labels[j + 1][1] if j + 1 < len(labels) else None
            if cur != lab and nxt != lab:
                break
            if cur is not None:
                votes[cur] += 1
            j += 1
        end = labels[j - 1][0] + WINDOW_MS
        if end - start >= MIN_SEGMENT_MS:
            total = sum(votes.values())
            segs.append(Segment(team, lab, start, end, votes[lab] / total if total else 0.0))
        i = j
    return segs


def summary(segments: list[Segment]) -> dict[str, dict[str, int]]:
    """Milliseconds per formation and team."""
    out: dict[str, dict[str, int]] = {}
    for s in segments:
        out.setdefault(s.team, {})
        out[s.team][s.formation] = out[s.team].get(s.formation, 0) + s.end_ms - s.start_ms
    return out
