"""Device clock to video time for courtside marks (addendum 01, 5.3).

A coach taps buttons on a phone during the match; the phone stores its own clock time. To place the
marks in the video we need `offset_ms` with `video_ms = device_ms + offset_ms`.

1. Prior from metadata: the camera writes its recording start (`recorded_at`). If both clocks were
   right, `offset = -recorded_at`. Camera clocks are often off by seconds to minutes, so this is
   only a prior with a search window.
2. Refinement from anchors: goals in the video (detected from throw-offs, tagged, imported) are
   matched against the coach's goal taps. Every pair inside the window proposes an offset; the
   proposal that explains most taps wins, and the median of its matched pairs is the estimate.
   Coaches tap a moment after the goal; `REACTION_MS` corrects that typical delay.

Without anchors the prior is used with low confidence; without both, nothing is synced.
"""

from __future__ import annotations

import bisect
import statistics
from dataclasses import dataclass

REACTION_MS = 2000  # typical delay between the goal and the tap
MATCH_TOLERANCE_MS = 3000
PRIOR_WINDOW_MS = 180_000  # camera clocks off by up to 3 minutes
MIN_MATCHES = 2


@dataclass(frozen=True)
class SyncResult:
    offset_ms: int | None
    confidence: float
    source: str  # events, metadata, none
    matched: int


def _score(marks: list[int], anchors: list[int], offset: int) -> list[tuple[int, int]]:
    """Pairs (mark, anchor) within the tolerance for this offset; each anchor used once.
    `anchors` must be sorted."""
    used: set[int] = set()
    pairs = []
    for m in marks:
        target = m + offset
        lo = bisect.bisect_left(anchors, target - MATCH_TOLERANCE_MS)
        best: tuple[int, int] | None = None
        for i in range(lo, len(anchors)):
            a = anchors[i]
            if a > target + MATCH_TOLERANCE_MS:
                break
            if i not in used and (best is None or abs(a - target) < best[0]):
                best = (abs(a - target), i)
        if best is not None:
            used.add(best[1])
            pairs.append((m, anchors[best[1]]))
    return pairs


def estimate_offset(
    goal_marks_ms: list[int],
    goal_anchors_ms: list[int],
    prior_offset_ms: int | None = None,
    window_ms: int = PRIOR_WINDOW_MS,
) -> SyncResult:
    """`goal_marks_ms`: device times (epoch ms) of goal taps; `goal_anchors_ms`: goal times in the
    video (ms); `prior_offset_ms`: from the camera's recording start, if known."""
    marks = sorted(m - REACTION_MS for m in goal_marks_ms)
    anchors = sorted(goal_anchors_ms)
    if marks and anchors:
        candidates = {
            a - m
            for m in marks
            for a in anchors
            if prior_offset_ms is None or abs((a - m) - prior_offset_ms) <= window_ms
        }
        best: tuple[int, int, list[tuple[int, int]]] | None = None
        for c in candidates:
            pairs = _score(marks, anchors, c)
            closeness = -abs(c - prior_offset_ms) if prior_offset_ms is not None else 0
            key = (len(pairs), closeness)
            if best is None or key > best[:2]:
                best = (len(pairs), closeness, pairs)
        if best is not None and best[0] >= MIN_MATCHES:
            pairs = best[2]
            offset = round(statistics.median(a - m for m, a in pairs))
            confidence = round(min(1.0, len(pairs) / max(4, len(marks))) * 0.95, 2)
            return SyncResult(offset, confidence, "events", len(pairs))
    if prior_offset_ms is not None:
        return SyncResult(prior_offset_ms, 0.3, "metadata", 0)
    return SyncResult(None, 0.0, "none", 0)
