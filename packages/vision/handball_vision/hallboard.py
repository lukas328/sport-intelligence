"""Goals from the hall's own scoreboard (BRIEF 7.2 stage 10, complements ADR 026).

Raw amateur recordings rarely carry a score overlay, but the hall scoreboard is often in the picture:
a panning camera shows it now and then, a fixed camera sometimes all the time. It moves with the
camera, so the overlay finder (stable pixels) cannot find it; the text recogniser of the shirt
numbers (PP-OCR) reads it instead.

Reading: text boxes on a sampled frame; a match clock (`mm:ss`) anchors the board; the numbers on the
same line left and right of it (within a few clock widths) are the home and away scores. A board cut
by the frame edge gives one side only, so scores are cleaned per side: a value counts once it is read
twice in a row, and may only go up by one (a bigger jump must hold for four readings and adds at
most three goals, as in `scoreboard.goals_from_scores`). A goal is placed at the first reading of the
new value; with a panning camera that is late by the time the board was out of view, so the API
moves it to the end of the scoring side's attack (as for the overlay).
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray

CLOCK = re.compile(r"^(\d{1,2})[:.](\d{2})")
NUMBER = re.compile(r"^\d{1,2}$")


@dataclass(frozen=True)
class Token:
    text: str
    x1: float
    y1: float
    x2: float
    y2: float
    score: float = 1.0

    @property
    def cy(self) -> float:
        return (self.y1 + self.y2) / 2

    @property
    def h(self) -> float:
        return self.y2 - self.y1


@dataclass(frozen=True)
class BoardReading:
    t_ms: int
    home: int | None
    away: int | None
    clock_s: int | None


def parse_board(tokens: Sequence[Token], t_ms: int = 0, reach: float = 4.0) -> BoardReading | None:
    """Home score, clock and away score from the text on one frame, or None without a clock."""
    clocks = []
    for tk in tokens:
        m = CLOCK.match(tk.text.strip())
        if m and int(m.group(2)) < 60 and int(m.group(1)) <= 70:
            clocks.append((tk, int(m.group(1)) * 60 + int(m.group(2))))
    if not clocks:
        return None
    clock, clock_s = max(clocks, key=lambda c: c[0].score * c[0].h)
    width = clock.x2 - clock.x1
    left: list[tuple[float, int]] = []
    right: list[tuple[float, int]] = []
    for tk in tokens:
        if tk is clock or not NUMBER.match(tk.text.strip()):
            continue
        if abs(tk.cy - clock.cy) > 0.8 * max(clock.h, tk.h):
            continue
        cx = (tk.x1 + tk.x2) / 2  # boxes of neighbouring digits may overlap the clock's box a bit
        if clock.x1 - reach * width <= tk.x1 and cx < clock.x1 + 0.3 * width:
            left.append((clock.x1 - cx, int(tk.text)))
        elif tk.x2 <= clock.x2 + reach * width and cx > clock.x2 - 0.3 * width:
            right.append((cx - clock.x2, int(tk.text)))
    home = min(left)[1] if left else None
    away = min(right)[1] if right else None
    return BoardReading(t_ms, home, away, clock_s)


def _side_goals(reads: Sequence[tuple[int, int]], confirm: int = 2) -> list[tuple[int, int, int]]:
    """(t_ms, new value, last time the old value was seen) per goal on one side, from noisy
    readings of its score."""
    out: list[tuple[int, int, int]] = []
    current: int | None = None
    seen_old = 0
    run: list[tuple[int, int]] = []
    for t, v in reads:
        if run and run[-1][1] != v:
            run = []
        run.append((t, v))
        if current is None:
            if len(run) >= confirm:
                current, seen_old = v, t
            continue
        step = v - current
        if step == 0:
            seen_old = t
            continue
        need = confirm if step == 1 else 4
        if step >= 1 and len(run) >= need:
            for k in range(min(step, 3)):
                out.append((run[0][0], current + k + 1, seen_old))
            current, seen_old = v, t
    return out


def goals_from_board(readings: Sequence[BoardReading]) -> list[dict[str, Any]]:
    """Goals per side, sorted by time: {t_ms, side ("left" = home), score_side, window_ms (how far
    back the goal can lie: since the board last showed the old score), score [home, away] where the
    other side is known}."""
    out = []
    for side, key in (("left", "home"), ("right", "away")):
        reads = [(r.t_ms, getattr(r, key)) for r in readings if getattr(r, key) is not None]
        for t, v, old in _side_goals(reads):
            other = "away" if key == "home" else "home"
            known = [
                getattr(r, other) for r in readings if r.t_ms <= t and getattr(r, other) is not None
            ]
            pair = None
            if known:
                pair = [v, known[-1]] if key == "home" else [known[-1], v]
            out.append(
                {"t_ms": t, "side": side, "score_side": v, "window_ms": t - old, "score": pair}
            )
    return sorted(out, key=lambda g: g["t_ms"])


class HallBoardReader:
    """Reads the hall scoreboard every `every_s` seconds from decoded frames (`add`)."""

    def __init__(self, ocr: Any, fps: float, every_s: float = 2.0) -> None:
        self.ocr = ocr  # handball_vision.numbers.NumberReader (detect + recognise)
        self.fps = fps
        self.step = max(1, round(every_s * fps))
        self.readings: list[BoardReading] = []
        self.calls = 0

    def add(self, index: int, frame: NDArray[Any]) -> None:
        if index % self.step:
            return
        self.calls += 1
        boxes = self.ocr.detect(frame)
        crops, kept = [], []
        for b in boxes:
            x1, y1 = np.asarray(b).min(axis=0)
            x2, y2 = np.asarray(b).max(axis=0)
            if y2 - y1 < 8:
                continue
            crops.append(
                frame[max(0, int(y1) - 2) : int(y2) + 2, max(0, int(x1) - 2) : int(x2) + 2]
            )
            kept.append((float(x1), float(y1), float(x2), float(y2)))
        tokens = [
            Token(t, *bx, s)
            for (t, s), bx in zip(self.ocr.recognise(crops), kept, strict=True)
            if s >= 0.6
        ]
        r = parse_board(tokens, round(index * 1000 / self.fps))
        if r is not None:
            self.readings.append(r)

    def summary(self) -> dict[str, Any]:
        return {
            "source": "hall_scoreboard",
            "readings": len(self.readings),
            "calls": self.calls,
            "goals": goals_from_board(self.readings),
            "board_clock": [[r.t_ms, r.clock_s] for r in self.readings if r.clock_s is not None][
                :2000
            ],
        }
