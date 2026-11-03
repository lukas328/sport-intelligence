"""Track identity: jersey numbers to roster players (BRIEF 7.2 stage 6, M5).

Two parts:
- `JerseyReader`: reads a jersey number from player crops. `OnnxJerseyReader` runs any exported digit
  classifier with outputs [batch, 101] (class 100 = "not readable"); weights come from the model registry
  (ADR 003). Without a model nothing is read and identities stay manual.
- `assign_numbers`: turns noisy per-crop readings into one number per track. Greedy assignment in order of
  evidence (summed reading confidence), with the constraints that matter on a handball court:
  * a number belongs to one team (tracks only compete within their team),
  * two tracks that are on court at the same time cannot carry the same number,
  * tracks that never overlap in time (fragments of the same player) may share a number.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import numpy as np
from numpy.typing import NDArray

UNREADABLE = 100


@dataclass(frozen=True)
class Reading:
    track_id: int
    number: int  # 0..99
    confidence: float  # 0..1


@dataclass(frozen=True)
class TrackSpan:
    track_id: int
    team: str | None
    first_ms: int
    last_ms: int


@dataclass(frozen=True)
class Assignment:
    track_id: int
    number: int
    confidence: float
    votes: int


class JerseyReader(Protocol):
    def read(self, crops: list[NDArray[Any]]) -> list[tuple[int, float] | None]: ...


class OnnxJerseyReader:
    """Generic ONNX digit classifier: input [b, 3, h, w] RGB 0..1, output [b, 101] logits."""

    def __init__(self, model_path: Path, size: tuple[int, int] = (64, 64), min_conf: float = 0.5):
        import onnxruntime as ort

        providers = [
            p
            for p in ("CUDAExecutionProvider", "CPUExecutionProvider")
            if p in ort.get_available_providers()
        ]
        self.session = ort.InferenceSession(str(model_path), providers=providers)
        self.input_name = self.session.get_inputs()[0].name
        self.size = size
        self.min_conf = min_conf

    def read(self, crops: list[NDArray[Any]]) -> list[tuple[int, float] | None]:
        import cv2

        if not crops:
            return []
        batch = np.stack(
            [
                cv2.cvtColor(cv2.resize(c, self.size), cv2.COLOR_BGR2RGB)
                .astype(np.float32)
                .transpose(2, 0, 1)
                / 255.0
                for c in crops
            ]
        )
        (logits,) = self.session.run(None, {self.input_name: batch})[:1]
        e = np.exp(logits - logits.max(axis=1, keepdims=True))
        probs = e / e.sum(axis=1, keepdims=True)
        out: list[tuple[int, float] | None] = []
        for p in probs:
            k = int(p.argmax())
            out.append(None if k == UNREADABLE or p[k] < self.min_conf else (k, float(p[k])))
        return out


def _overlap(a: TrackSpan, b: TrackSpan) -> bool:
    return a.first_ms < b.last_ms and b.first_ms < a.last_ms


def assign_numbers(
    spans: list[TrackSpan], readings: list[Reading], min_votes: int = 3
) -> list[Assignment]:
    """One number per track from noisy readings, respecting team and time-overlap constraints."""
    by_track: dict[int, Counter[int]] = defaultdict(Counter)
    weight: dict[int, dict[int, float]] = defaultdict(lambda: defaultdict(float))
    for r in readings:
        by_track[r.track_id][r.number] += 1
        weight[r.track_id][r.number] += r.confidence
    teams: dict[str | None, list[TrackSpan]] = defaultdict(list)
    for s in spans:
        if sum(by_track[s.track_id].values()) >= min_votes:
            teams[s.team].append(s)

    result: list[Assignment] = []
    for members in teams.values():
        # strongest evidence first: (track, number) pairs ordered by summed confidence. A pair is
        # taken unless the track already has a number or the number is worn by an overlapping track.
        pairs = sorted(
            ((w, s.track_id, n) for s in members for n, w in weight[s.track_id].items()),
            key=lambda p: (-p[0], p[1], p[2]),
        )
        holders: dict[int, list[TrackSpan]] = defaultdict(list)
        done: set[int] = set()
        span = {s.track_id: s for s in members}
        for w, tid, n in pairs:
            if tid in done or any(_overlap(span[tid], o) for o in holders[n]):
                continue
            holders[n].append(span[tid])
            done.add(tid)
            total = sum(weight[tid].values())
            result.append(Assignment(tid, n, round(w / total, 3), by_track[tid][n]))
    result.sort(key=lambda a: a.track_id)
    return result


def to_roster(
    assignments: list[Assignment], roster: dict[int, str], team: Mapping[int, str | None], own: str
) -> dict[int, tuple[str, float]]:
    """Map own-team track numbers to roster player ids: {track_id: (player_id, confidence)}."""
    out = {}
    for a in assignments:
        if team.get(a.track_id) in (own, f"{own}_gk") and a.number in roster:
            out[a.track_id] = (roster[a.number], a.confidence)
    return out
