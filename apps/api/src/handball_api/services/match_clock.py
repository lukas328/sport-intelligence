"""Video time of a match-clock time (an official report entry), with how far off it can be.

The plain mapping (`events.video_from_clock`) counts from the throw-off of the half and ignores
every stop of the clock: after a time-out an entry lands a minute early, at the end of a half
often several minutes. Shots of the report are then useless next to the video candidates, which
are a few seconds apart. Anchors, pairs of a clock time and the video time it was shown at:
- the overlay clock read by the analysis (`scoreboard.clock` of the video: runs in which the
  shown clock counts): exact inside a run, and both ends of each run are anchors;
- report events whose video time is known (`attributes.video.t_ms`: a goal read from the overlay,
  or a shot or goal the coach confirmed on a candidate): each confirmation helps the next ones;
- the throw-off of each half (`match.kickoff_ms`), in a half without an overlay clock.
Between the anchors before and after a time the clock stood still for
(t_after - t_before) - (clock_after - clock_before): the time is counted from the nearer anchor
and that stop is its uncertainty. With an anchor on one side only the stop is unknown (None).
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass, field
from typing import Any

from handball_api.models import Event, Match

MAX_RUN_GAP_S = 2.0  # an overlay run must cover the clock time within this (reads every 2 s)


@dataclass(frozen=True)
class Anchor:
    clock_s: float
    t_ms: int


@dataclass
class ClockMap:
    period_s: int
    runs: list[tuple[int, int, float]] = field(default_factory=list)  # start_ms, end_ms, clock
    anchors: dict[int, list[Anchor]] = field(default_factory=dict)  # per half

    def period_of(self, clock_s: float) -> int:
        return 1 if clock_s < self.period_s else 2

    def add(self, period: int, clock_s: float, t_ms: int) -> None:
        row = self.anchors.setdefault(period, [])
        bisect.insort(row, Anchor(float(clock_s), int(t_ms)), key=lambda a: (a.clock_s, a.t_ms))

    def video_ms(self, period: int, clock_s: float) -> tuple[int | None, int | None]:
        """(video time, uncertainty in ms; 0 exact, None unknown); (None, None) without any
        anchor in the half."""
        for start, end, c0 in self.runs:
            if self.period_of(c0) != period:
                continue
            c1 = c0 + (end - start) / 1000
            if c0 - MAX_RUN_GAP_S <= clock_s <= c1 + MAX_RUN_GAP_S:
                return round(start + (clock_s - c0) * 1000), 0
        row = self.anchors.get(period) or []
        if not row:
            return None, None
        i = bisect.bisect_right([a.clock_s for a in row], clock_s)
        before = row[i - 1] if i > 0 else None
        after = row[i] if i < len(row) else None
        if before is not None and after is not None:
            stop = max(
                0, (after.t_ms - before.t_ms) - round((after.clock_s - before.clock_s) * 1000)
            )
            if clock_s - before.clock_s <= after.clock_s - clock_s:
                return round(before.t_ms + (clock_s - before.clock_s) * 1000), stop
            return round(after.t_ms - (after.clock_s - clock_s) * 1000), stop
        a = before or after
        assert a is not None
        return round(a.t_ms + (clock_s - a.clock_s) * 1000), None


def _video(e: Event) -> dict[str, Any] | None:
    v = (e.attributes or {}).get("video")
    return v if isinstance(v, dict) and v.get("t_ms") is not None else None


def build(match: Match, analysis: dict[str, Any] | None, official: list[Event]) -> ClockMap:
    """The anchors of a match: the overlay clock of the analysed video (`analysis` of the
    video asset), report events with a known video time and the throw-offs."""
    cm = ClockMap(int(match.period_s))
    board = (analysis or {}).get("scoreboard")
    clock = board.get("clock") if isinstance(board, dict) else None
    for run in clock or []:
        try:
            start, end, c0 = int(run["start_ms"]), int(run["end_ms"]), float(run["start_clock_s"])
        except (KeyError, TypeError, ValueError):
            continue
        cm.runs.append((start, max(start, end), c0))
        p = cm.period_of(c0)
        cm.add(p, c0, start)
        cm.add(p, c0 + (max(start, end) - start) / 1000, max(start, end))
    for e in official:
        v = _video(e)
        if v is not None and e.clock_s is not None and e.period in (1, 2):
            cm.add(e.period, float(e.clock_s), int(v["t_ms"]))
    overlay_halves = {cm.period_of(c0) for _, _, c0 in cm.runs}
    for half, start in (match.kickoff_ms or {}).items():
        # a throw-off found by the position heuristics is less exact than the overlay clock
        if str(half) in ("1", "2") and int(half) not in overlay_halves:
            cm.add(int(half), (int(half) - 1) * match.period_s, int(start))
    return cm


def video_time(cm: ClockMap, e: Event) -> tuple[int | None, int | None]:
    """Where a report event lies in the video: its confirmed video time (uncertainty 0), else
    the clock map's estimate, else the stored time (uncertainty unknown)."""
    v = _video(e)
    if v is not None:
        return int(v["t_ms"]), 0
    if e.clock_s is not None and e.period in (1, 2):
        t, unc = cm.video_ms(e.period, float(e.clock_s))
        if t is not None:
            return t, unc
    return e.t_ms, None
