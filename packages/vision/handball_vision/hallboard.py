"""Goals from the hall's own scoreboard (BRIEF 7.2 stage 10, complements ADR 026).

Raw amateur recordings rarely carry a score overlay, but the hall scoreboard is often in the picture:
a panning camera shows it now and then, a fixed camera sometimes all the time. It moves with the
camera, so the overlay finder (stable pixels) cannot find it; the text recogniser of the shirt
numbers (PP-OCR) reads it instead. A club stream's own score graphic on a fixed camera looks the
same to the overlay finder (everything is stable) and is read here as well.

Reading (`parse_board`): text boxes on a sampled frame; a match clock (`mm:ss`) anchors the board.
Two layouts:
- in line: the numbers left and right of the clock on its line (within a few clock widths) are the
  home and away scores ("16 32:10 11", a hall board);
- stacked: a score field `a:b` above or below the clock ("SGW 27:30 EMM" over "51:09", a stream
  graphic). A field with team codes glued to it ("SGW27:30") is a score; two bare `mm:ss` fields one
  above the other are told apart over the whole video (`HallBoardReader`): the clock changes from
  one sample to the next, the score rarely.
Fields that OCR merged into one box are split first ("32:10 11", "32:1011").

Finding the board (`HallBoardReader.add`): the first reading comes from text detection on the whole
frame. Then the board region is locked: a grey template of it is matched at its last position
(fixed camera, a few ms) or over the whole frame at reduced size and three scales (panning camera),
and only a window around it is read, enlarged when the board's text is small (a far board on a
720p proxy is 6 to 8 px tall). While the board is out of view the template is tried every
`probe_every_s`, so a pan across it is caught between two regular reads; the whole frame is read
again at most every `full_every_s`.

Goals (`goals_from_board`): per side the most likely score sequence that never goes down: each
reading that disagrees costs one, each goal costs 1.5 (so a new value needs two more readings for it
than against it), several goals at once cost more. With the official running score (`sequence`)
the decoding follows that sequence instead, both sides at once. A goal is placed at the first
reading of the new value; with a panning camera that is late by the time the board was out of view
(`window_ms`), so the API moves it to the end of the scoring side's attack (as for the overlay).
"""

from __future__ import annotations

import itertools
import math
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

import cv2
import numpy as np
from numpy.typing import NDArray

CLOCK = re.compile(r"^(\d{1,2})[:.](\d{2})")
NUMBER = re.compile(r"^\d{1,2}$")
PAIR = re.compile(r"(?<!\d)(\d{1,2}) ?[:\-] ?(\d{1,2})(?!\d)")
LETTER = re.compile(r"[A-Za-z]")

Stacked = Literal["above", "below"]

MISREAD_COST = 1.0
GOAL_COST = 1.5
EXTRA_GOAL_COST = 1.0  # each further goal between two readings


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
    def cx(self) -> float:
        return (self.x1 + self.x2) / 2

    @property
    def h(self) -> float:
        return self.y2 - self.y1

    @property
    def w(self) -> float:
        return self.x2 - self.x1


@dataclass(frozen=True)
class BoardReading:
    t_ms: int
    home: int | None
    away: int | None
    clock_s: int | None


def _clock_s(text: str) -> int | None:
    m = CLOCK.match(text.strip())
    if m and int(m.group(2)) < 60 and int(m.group(1)) <= 70:
        return int(m.group(1)) * 60 + int(m.group(2))
    return None


def _sub(tk: Token, start: int, end: int, n: int, text: str) -> Token:
    """The part of a merged box holding characters start..end of its n characters."""
    return Token(text, tk.x1 + tk.w * start / n, tk.y1, tk.x1 + tk.w * end / n, tk.y2, tk.score)


MERGED = re.compile(r"^(\d{1,4})[:.](\d{2,4})$")  # "1631:2010": home, clock and away in one box
BARE8 = re.compile(r"^\d{8}$")
# the recogniser's dictionary also has full-width punctuation: full-width colon, ratio sign and
# full-width full stop
FULLWIDTH = "\uff1a\u2236\uff0e"
FULLWIDTH_MAP = str.maketrans({"\uff1a": ":", "\u2236": ":", "\uff0e": "."})


def split_token(tk: Token) -> list[Token]:
    """Fields OCR merged into one box, each with its share of the box: words ("16 32:10 11") and
    a clock with two-digit scores glued on ("1632:1011" is 16, 32:10, 11; "632:10" and "32:101"
    are the clock 32:10 alone, the rest may be a score cut off). A score field with team codes
    ("SGW22:25HSK") stays one token."""
    text = tk.text.strip()
    if text != tk.text or any(c in text for c in FULLWIDTH):
        text = text.translate(FULLWIDTH_MAP)
        tk = Token(text, tk.x1, tk.y1, tk.x2, tk.y2, tk.score)
    if " " in text and not LETTER.search(text) and not PAIR.fullmatch(text):
        out, pos = [], 0
        words = text.split()
        for k, word in enumerate(words):
            start = text.index(word, pos)
            pos = start + len(word)
            part = _sub(tk, start, pos, len(text), word)
            # "18 3326 13": a clock that lost its colon between the two scores
            if (
                re.fullmatch(r"\d{4}", word)
                and 0 < k < len(words) - 1
                and NUMBER.match(words[k - 1])
                and NUMBER.match(words[k + 1])
            ):
                part = Token(
                    f"{word[:2]}:{word[2:]}", part.x1, part.y1, part.x2, part.y2, part.score
                )
            out.extend(split_token(part))
        return out
    if BARE8.match(text):  # colon lost: "18333013" is 18, 33:30, 13
        clock = f"{text[2:4]}:{text[4:6]}"
        if _clock_s(clock) is None:
            return [tk]
        return [_sub(tk, 0, 2, 8, text[:2]), _sub(tk, 2, 6, 8, clock), _sub(tk, 6, 8, 8, text[6:])]
    m = MERGED.match(text)
    # one digit glued on behind the seconds may be the rest of a score cut off by the frame edge
    if m is None or len(m.group(1)) <= 2 and len(m.group(2)) != 4:
        return [tk]
    pre, post = m.group(1), m.group(2)
    n = len(text)
    c0 = max(0, len(pre) - 2)  # first character of the clock
    c1 = len(pre) + 3  # one past the clock's last character
    out = []
    if len(pre) == 4:
        out.append(_sub(tk, 0, 2, n, pre[:2]))
    out.append(_sub(tk, c0, c1, n, text[c0:c1]))
    if len(post) == 4:
        out.append(_sub(tk, c1, n, n, post[2:]))
    return out if _clock_s(text[c0:c1]) is not None else [tk]


def _pair(tk: Token) -> tuple[int, int] | None:
    """A field that can only be a score: team codes glued to it ("SGW27:30EMM"), spaces around
    the colon ("27 : 30"), a dash ("27-30") or one digit after the colon ("0:0"). A bare "27:30"
    may be a clock as well."""
    text = tk.text.strip()
    m = PAIR.search(text)
    if m is None:
        return None
    if LETTER.search(text) or m.group(0) != f"{m.group(1)}:{m.group(2)}" or len(m.group(2)) == 1:
        return int(m.group(1)), int(m.group(2))
    return None


def _stacked_with(a: Token, b: Token) -> bool:
    """`a` directly above or below `b` (overlapping columns, the next line or the one after)."""
    overlap = min(a.x2, b.x2) - max(a.x1, b.x1)
    h = max(a.h, b.h)
    return overlap >= 0.4 * min(a.w, b.w) and 0.6 * h <= abs(a.cy - b.cy) <= 3.0 * h


def _row_numbers(
    tokens: Sequence[Token], clock: Token, reach: float, dy: float = 0.0
) -> tuple[int | None, int | None]:
    """Nearest numbers left and right of the clock on its line (dy = 0) or on a line dy above
    (dy < 0) or below it, within `reach` clock widths."""
    width = clock.w
    cy = clock.cy + dy
    left: list[tuple[float, int]] = []
    right: list[tuple[float, int]] = []
    for tk in tokens:
        if tk is clock or not NUMBER.match(tk.text.strip()):
            continue
        if abs(tk.cy - cy) > 0.8 * max(clock.h, tk.h):
            continue
        cx = tk.cx  # boxes of neighbouring digits may overlap the clock's box a bit
        if dy:  # a score line above or below: split at the clock's centre
            if clock.cx - reach * width <= tk.x1 and cx < clock.cx:
                left.append((clock.cx - cx, int(tk.text)))
            elif tk.x2 <= clock.cx + reach * width and cx > clock.cx:
                right.append((cx - clock.cx, int(tk.text)))
        elif clock.x1 - reach * width <= tk.x1 and cx < clock.x1 + 0.3 * width:
            left.append((clock.x1 - cx, int(tk.text)))
        elif tk.x2 <= clock.x2 + reach * width and cx > clock.x2 - 0.3 * width:
            right.append((cx - clock.x2, int(tk.text)))
    return (min(left)[1] if left else None, min(right)[1] if right else None)


def stacked_pairs(tokens: Sequence[Token]) -> list[tuple[Token, Token]]:
    """(upper, lower) pairs of bare `mm:ss` fields one directly above the other."""
    clocks = [tk for tk in tokens if _clock_s(tk.text) is not None and _pair(tk) is None]
    out = []
    for a in clocks:
        for b in clocks:
            if a is not b and a.cy < b.cy and _stacked_with(a, b):
                out.append((a, b))
    return out


def parse_board(
    tokens: Sequence[Token],
    t_ms: int = 0,
    reach: float = 4.0,
    stacked: Stacked | None = None,
) -> BoardReading | None:
    """Home score, clock and away score from the text on one frame, or None without a clock.

    `stacked`: where the score field sits relative to the clock when two bare `mm:ss` fields are
    stacked ("above": the upper one is the score). Unknown (None), such a frame gives the clock
    as before (the most confident, tallest `mm:ss`) and no score."""
    toks = [s for tk in tokens for s in split_token(tk)]
    clocks = [(tk, c) for tk in toks if (c := _clock_s(tk.text)) is not None and _pair(tk) is None]
    if not clocks:
        return None
    # a score field with team codes stacked with a clock
    for tk in toks:
        pair = _pair(tk)
        if pair is None:
            continue
        near = [(c, s) for c, s in clocks if _stacked_with(tk, c)]
        if near:
            clock, clock_s = max(near, key=lambda c: c[0].score * c[0].h)
            return BoardReading(t_ms, pair[0], pair[1], clock_s)
    # two bare mm:ss fields one above the other: one is the score
    pairs = stacked_pairs(toks)
    if pairs:
        if stacked is None:
            clock, clock_s = max(clocks, key=lambda c: c[0].score * c[0].h)
            return BoardReading(t_ms, None, None, clock_s)
        # the score field is the outermost line (penalty timers may stack under the clock)
        if stacked == "above":
            score_tk, clock = min(pairs, key=lambda p: p[0].cy)
        else:
            clock, score_tk = max(pairs, key=lambda p: p[1].cy)
        m = PAIR.search(score_tk.text)
        home, away = (int(m.group(1)), int(m.group(2))) if m else (None, None)
        return BoardReading(t_ms, home, away, _clock_s(clock.text))
    clock, clock_s = max(clocks, key=lambda c: c[0].score * c[0].h)
    home, away = _row_numbers(toks, clock, reach)
    if home is None and away is None and stacked is not None:
        # a stacked board whose score field came out as separate numbers ("27", "30")
        dy = -1.2 * clock.h if stacked == "above" else 1.2 * clock.h
        home, away = _row_numbers(toks, clock, reach, dy)
    return BoardReading(t_ms, home, away, clock_s)


class StackedVotes:
    """Where the score field sits in a stacked board, voted over the samples (`add` each in
    turn): a score field with team codes says it directly; of two bare `mm:ss` fields one above
    the other, the one that changes between samples a few seconds apart is the clock."""

    def __init__(self) -> None:
        self.votes = {"above": 0.0, "below": 0.0}
        self._prev: tuple[int, str, str] | None = None

    def add(self, t_ms: int, tokens: Sequence[Token]) -> None:
        toks = [s for tk in tokens for s in split_token(tk)]
        clocks = [tk for tk in toks if _clock_s(tk.text) is not None and _pair(tk) is None]
        for tk in toks:
            if _pair(tk) is not None:
                for c in clocks:
                    if _stacked_with(tk, c):
                        self.votes["above" if tk.cy < c.cy else "below"] += 1
        pairs = stacked_pairs(toks)
        if not pairs:
            return
        upper, lower = pairs[0]
        cur = (t_ms, upper.text.strip(), lower.text.strip())
        prev = self._prev
        if prev is not None and 0 < t_ms - prev[0] <= 6000:
            up_changed, low_changed = cur[1] != prev[1], cur[2] != prev[2]
            if low_changed and not up_changed:
                self.votes["above"] += 0.5
            elif up_changed and not low_changed:
                self.votes["below"] += 0.5
        self._prev = cur

    def result(self) -> Stacked | None:
        """None while nothing tells (no stacked board, or a tie)."""
        above, below = self.votes["above"], self.votes["below"]
        if max(above, below) < 2 or above == below:
            return None
        return "above" if above > below else "below"


def stacked_vote(samples: Sequence[tuple[int, Sequence[Token]]]) -> Stacked | None:
    """`StackedVotes` over all samples at once."""
    votes = StackedVotes()
    for t, tokens in samples:
        votes.add(t, tokens)
    return votes.result()


# --- goals --------------------------------------------------------------------------------------


def _decode(
    obs: Sequence[tuple[int, Sequence[int | None]]],
    states: Sequence[Sequence[int]],
) -> list[int]:
    """Index into `states` (ordered, never going back) per observation that explains the readings
    best: a reading that disagrees costs MISREAD_COST, each step forward GOAL_COST (plus
    EXTRA_GOAL_COST per further step taken between two readings)."""
    n, m = len(obs), len(states)
    if not n or not m:
        return []
    inf = math.inf
    cost = [0.0] * m
    back: list[list[int]] = []

    def emit(values: Sequence[int | None], k: int) -> float:
        return sum(
            MISREAD_COST for v, s in zip(values, states[k], strict=True) if v is not None and v != s
        )

    cost = [emit(obs[0][1], k) for k in range(m)]
    for i in range(1, n):
        best_prev = [0] * m
        new = [inf] * m
        # cheapest way to arrive at k: stay, or come from j < k
        run_best, run_arg = inf, 0
        for k in range(m):
            # candidates j < k: cost[j] + GOAL_COST + EXTRA_GOAL_COST * (k - j - 1)
            # = (cost[j] - EXTRA * j) + GOAL - EXTRA + EXTRA * (k - 1) ... kept as a running min
            if k > 0:
                cand = cost[k - 1] - EXTRA_GOAL_COST * (k - 1)
                if cand < run_best:
                    run_best, run_arg = cand, k - 1
            stay = cost[k]
            move = run_best + GOAL_COST + EXTRA_GOAL_COST * (k - 1) if k > 0 else inf
            if stay <= move:
                new[k], best_prev[k] = stay, k
            else:
                new[k], best_prev[k] = move, run_arg
            new[k] += emit(obs[i][1], k)
        back.append(best_prev)
        cost = new
    k = min(range(m), key=lambda j: (cost[j], j))
    path = [k]
    for bp in reversed(back):
        k = bp[k]
        path.append(k)
    return path[::-1]


def _goal_events(
    obs: Sequence[tuple[int, Sequence[int | None]]],
    states: Sequence[Sequence[int]],
    path: Sequence[int],
    side_of: Sequence[int],
) -> list[tuple[int, int, int, int, int]]:
    """(t_ms, side index, new value, window_ms, state index after it) per step forward."""
    out = []
    for i in range(1, len(path)):
        if path[i] == path[i - 1]:
            continue
        t = obs[i][0]
        before = states[path[i - 1]]
        for k in range(path[i - 1] + 1, path[i] + 1):
            side = side_of[k]
            # since the board last showed this side's score from before the step(s)
            seen = [o[0] for o in obs[:i] if o[1][side] == before[side]]
            last = seen[-1] if seen else obs[i - 1][0]
            out.append((t, side, states[k][side], t - last, k))
    return out


def goals_from_board(
    readings: Sequence[BoardReading],
    sequence: Sequence[Sequence[int]] | None = None,
) -> list[dict[str, Any]]:
    """Goals per side, sorted by time: {t_ms, side ("left" = home), score_side, window_ms (how far
    back the goal can lie: since the board last showed the old score), score [home, away] where the
    other side is known}.

    `sequence`: the official running score ([home, away] after each goal, in order), when known:
    the readings are then matched to it, both sides at once, and every goal of it that falls
    between two readings is placed there."""
    rows = sorted(
        (r for r in readings if r.home is not None or r.away is not None), key=lambda r: r.t_ms
    )
    if not rows:
        return []
    out: list[dict[str, Any]] = []
    if sequence:
        states = [tuple(int(v) for v in s) for s in sequence]
        if states[0] != (0, 0):
            states.insert(0, (0, 0))
        side_of = [0] + [0 if b[0] > a[0] else 1 for a, b in itertools.pairwise(states)]
        obs = [(r.t_ms, (r.home, r.away)) for r in rows]
        path = _decode(obs, states)
        for t, side, v, window, k in _goal_events(obs, states, path, side_of):
            out.append(
                {
                    "t_ms": t,
                    "side": "left" if side == 0 else "right",
                    "score_side": v,
                    "window_ms": window,
                    "score": list(states[k]),
                }
            )
        return out
    decoded: list[list[tuple[int, int]]] = []  # per side: (t_ms, decoded value) per reading
    events = []
    for side, key in enumerate(("home", "away")):
        side_obs = [(r.t_ms, (getattr(r, key),)) for r in rows if getattr(r, key) is not None]
        values = sorted({o[1][0] for o in side_obs})
        if not values:
            decoded.append([])
            continue
        # states: every value from the lowest to the highest reading (a goal may go unseen)
        side_states = [(v,) for v in range(values[0], values[-1] + 1)]
        path = _decode(side_obs, side_states)
        decoded.append([(o[0], side_states[k][0]) for o, k in zip(side_obs, path, strict=True)])
        for t, _, v, window, _k in _goal_events(
            side_obs, side_states, path, [0] * len(side_states)
        ):
            events.append((t, side, v, window))
    for t, side, v, window in events:
        other = [val for tt, val in decoded[1 - side] if tt <= t]
        pair = None
        if other:
            pair = [v, other[-1]] if side == 0 else [other[-1], v]
        out.append(
            {
                "t_ms": t,
                "side": "left" if side == 0 else "right",
                "score_side": v,
                "window_ms": window,
                "score": pair,
            }
        )
    return sorted(out, key=lambda g: (g["t_ms"], g["side"]))


# --- reader -------------------------------------------------------------------------------------

NCC_MIN = 0.8  # template match of the locked board anywhere in the frame
NCC_NEAR = 0.75  # ... where it was last seen
TEXT_MIN_PX = 28.0  # board text smaller than this (in frame px) is enlarged before reading
MAX_ZOOM = 4.0
SEARCH_PX = 24.0  # the global template search runs at a size where the template is this tall
SCALES = (0.79, 0.89, 1.0, 1.12, 1.26)  # zoom the global template search covers
FAST_NCC = 0.9  # the board stands where it stood: recognition alone on the last text boxes


@dataclass
class _Lock:
    box: tuple[float, float, float, float]  # board text (clock and scores), px from the patch
    text_h: float
    patch: NDArray[np.uint8]  # grey template: the box with a margin
    at: tuple[int, int]  # patch's top-left corner in the frame where it was last seen
    boxes: list[tuple[float, float, float, float]] = field(default_factory=list)  # text, ditto


@dataclass
class _Stats:
    full: int = 0
    window: int = 0
    boxes: int = 0
    probes: int = 0
    found: int = 0


def board_rect(
    gray: NDArray[np.uint8], text: tuple[float, float, float, float], text_h: float
) -> tuple[int, int, int, int] | None:
    """The scoreboard around its text: the dark panel that holds the text with a margin for its
    frame, or None when there is none (bright background, a panel that runs on far beyond the
    text)."""
    h, w = gray.shape[:2]
    x1, y1, x2, y2 = text
    tw = x2 - x1
    rx0, ry0 = int(max(0, x1 - 1.5 * tw)), int(max(0, y1 - 4 * text_h))
    rx1, ry1 = int(min(w, x2 + 1.5 * tw)), int(min(h, y2 + 8 * text_h))
    region = gray[ry0:ry1, rx0:rx1]
    if region.size == 0:
        return None
    inner = gray[int(y1) : int(y2) + 1, int(x1) : int(x2) + 1]
    if inner.size == 0:
        return None
    # the panel: pixels about as dark as the darker part of the text's own box (mostly panel);
    # the bright digits leave holes, which do not change its bounding box
    level = float(np.percentile(inner, 35)) + 12.0
    dark = cv2.morphologyEx(
        (region < level).astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)
    )
    _, labels, stats, _ = cv2.connectedComponentsWithStats(dark, connectivity=4)
    ix0, iy0 = int(x1) - rx0, int(y1) - ry0
    near = labels[max(0, iy0) : iy0 + int(text_h) + 1, max(0, ix0) : ix0 + int(tw) + 1]
    labs = [int(v) for v in np.unique(near) if v]
    if not labs:
        return None
    lab = max(labs, key=lambda v: int(stats[v, 4]))
    bx, by, bw, bh, area = (int(v) for v in stats[lab])
    touches = bx == 0 or by == 0 or bx + bw >= region.shape[1] or by + bh >= region.shape[0]
    if touches or bw < 0.6 * tw or bw > 3.5 * tw or bh > 12 * text_h or area < 0.3 * bw * bh:
        return None
    # its frame and a little of what is around it
    mx, my = max(2, int(0.15 * bw)), max(2, int(0.15 * bh))
    return (
        max(0, rx0 + bx - mx),
        max(0, ry0 + by - my),
        min(w, rx0 + bx + bw + mx),
        min(h, ry0 + by + bh + my),
    )


def _gray(frame: NDArray[Any]) -> NDArray[np.uint8]:
    if frame.ndim == 2:
        return np.asarray(frame, np.uint8)
    return np.asarray(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), np.uint8)


class HallBoardReader:
    """Reads the hall scoreboard every `every_s` seconds from decoded frames (`add`).

    `full_every_s`: text detection on the whole frame at most this often while the board is not
    in view; `probe_every_s`: template probes for a locked board that is out of view (0: only at
    the regular reads). Frames may come at any spacing: a frame is read once its index reaches
    the next one due."""

    def __init__(
        self,
        ocr: Any,
        fps: float,
        every_s: float = 1.0,
        full_every_s: float = 4.0,
        probe_every_s: float = 0.25,
    ) -> None:
        self.ocr = ocr  # handball_vision.numbers.NumberReader (detect + recognise)
        self.fps = fps
        self.step = max(1, round(every_s * fps))
        self.probe_step = max(1, round(probe_every_s * fps)) if probe_every_s > 0 else self.step
        self.full_ms = round(full_every_s * 1000)
        self.samples: list[tuple[int, list[Token]]] = []
        self.calls = 0
        self.stats = _Stats()
        self._lock: _Lock | None = None
        self._due = 0
        self._last_full = -(10**9)
        self._readings: list[BoardReading] | None = None
        self._stacked: Stacked | None = None
        self._votes = StackedVotes()
        self._raw: list[tuple[float, float, float, float]] = []
        self._full_last = False
        self._last_score: tuple[int | None, int | None] = (None, None)

    # --- text ---------------------------------------------------------------------------------

    def _ocr(
        self, frame: NDArray[Any], win: tuple[int, int, int, int] | None, zoom: float
    ) -> list[Token]:
        h, w = frame.shape[:2]
        x0, y0, x1, y1 = win or (0, 0, w, h)
        img = frame[y0:y1, x0:x1]
        if img.size == 0:
            return []
        if zoom > 1.01:
            img = cv2.resize(img, None, fx=zoom, fy=zoom, interpolation=cv2.INTER_CUBIC)
        boxes = self.ocr.detect(img)
        crops, kept = [], []
        for b in boxes:
            bx1, by1 = np.asarray(b).min(axis=0)
            bx2, by2 = np.asarray(b).max(axis=0)
            if by2 - by1 < 8:
                continue
            crops.append(
                img[max(0, int(by1) - 2) : int(by2) + 2, max(0, int(bx1) - 2) : int(bx2) + 2]
            )
            kept.append(
                (
                    float(bx1) / zoom + x0,
                    float(by1) / zoom + y0,
                    float(bx2) / zoom + x0,
                    float(by2) / zoom + y0,
                )
            )
        out = []
        self._raw = []
        for (text, score), box in zip(self.ocr.recognise(crops), kept, strict=True):
            if score < 0.6 or not any(ch.isdigit() for ch in text):
                continue
            self._raw.append(box)
            touches = box[0] <= 1 or box[2] >= w - 2
            for tk in split_token(Token(text, *box, score)):
                # a number cut by the frame edge ("1" of "11") is no reading
                if touches and NUMBER.match(tk.text.strip()) and (tk.x1 <= 1 or tk.x2 >= w - 2):
                    continue
                out.append(tk)
        return out

    # --- locating -----------------------------------------------------------------------------

    def _make_lock(self, frame: NDArray[Any], tokens: Sequence[Token], r: BoardReading) -> None:
        board = [s for tk in tokens for s in split_token(tk)]
        clock = [tk for tk in board if _clock_s(tk.text) is not None]
        if not clock:
            return
        anchor = max(clock, key=lambda tk: tk.score * tk.h)
        near = [
            tk
            for tk in board
            if abs(tk.cy - anchor.cy) <= 3.2 * anchor.h
            and anchor.x1 - 5 * anchor.w <= tk.x1
            and tk.x2 <= anchor.x2 + 5 * anchor.w
        ]
        x1 = min(tk.x1 for tk in near)
        y1 = min(tk.y1 for tk in near)
        x2 = max(tk.x2 for tk in near)
        y2 = max(tk.y2 for tk in near)
        gray = _gray(frame)
        rect = board_rect(gray, (x1, y1, x2, y2), anchor.h)
        if rect is None:  # no dark board around the text (a stream graphic): text and a margin
            h, w = gray.shape[:2]
            m = 0.6 * anchor.h
            rect = (
                int(max(0, x1 - m)),
                int(max(0, y1 - m)),
                int(min(w, x2 + m)),
                int(min(h, y2 + m)),
            )
        px0, py0, px1, py1 = rect
        if px1 - px0 < 8 or py1 - py0 < 8:
            return
        patch = gray[py0:py1, px0:px1].copy()
        boxes = [(b[0] - px0, b[1] - py0, b[2] - px0, b[3] - py0) for b in self._raw]
        self._lock = _Lock(
            (x1 - px0, y1 - py0, x2 - px0, y2 - py0), anchor.h, patch, (px0, py0), boxes
        )

    def _locate(self, gray: NDArray[np.uint8]) -> tuple[int, int, float, float] | None:
        """Top-left corner of the locked board's patch in this frame, its scale and the match
        score, or None."""
        lock = self._lock
        assert lock is not None
        ph, pw = lock.patch.shape[:2]
        h, w = gray.shape[:2]
        # 1. where it was (fixed camera, slow pan)
        ax, ay = lock.at
        m = max(24, int(0.5 * ph))
        sx0, sy0 = max(0, ax - m), max(0, ay - m)
        sx1, sy1 = min(w, ax + pw + m), min(h, ay + ph + m)
        if sx1 - sx0 >= pw and sy1 - sy0 >= ph:
            res = cv2.matchTemplate(gray[sy0:sy1, sx0:sx1], lock.patch, cv2.TM_CCOEFF_NORMED)
            _, mx, _, loc = cv2.minMaxLoc(res)
            if mx >= NCC_NEAR:
                return sx0 + loc[0], sy0 + loc[1], 1.0, float(mx)
        # 2. anywhere, at a reduced size and three scales (zoom), then checked at full size
        q = min(1.0, SEARCH_PX / ph)
        small = cv2.resize(gray, None, fx=q, fy=q, interpolation=cv2.INTER_AREA) if q < 1 else gray
        best: tuple[float, int, int, float] | None = None
        for s in SCALES:
            tw, th = max(4, round(pw * q * s)), max(4, round(ph * q * s))
            if tw >= small.shape[1] or th >= small.shape[0]:
                continue
            tmpl = cv2.resize(lock.patch, (tw, th), interpolation=cv2.INTER_AREA)
            res = cv2.matchTemplate(small, tmpl, cv2.TM_CCOEFF_NORMED)
            _, mx, _, loc = cv2.minMaxLoc(res)
            if best is None or mx > best[0]:
                best = (mx, loc[0], loc[1], s)
        if best is None or best[0] < NCC_MIN - 0.05:
            return None
        _, lx, ly, s = best
        fx, fy = round(lx / q), round(ly / q)
        tw, th = round(pw * s), round(ph * s)
        tmpl = lock.patch if s == 1.0 else cv2.resize(lock.patch, (tw, th))
        r = max(6, int(2 / q))
        sx0, sy0 = max(0, fx - r), max(0, fy - r)
        sx1, sy1 = min(w, fx + tw + r), min(h, fy + th + r)
        if sx1 - sx0 < tw or sy1 - sy0 < th:
            return None
        res = cv2.matchTemplate(gray[sy0:sy1, sx0:sx1], tmpl, cv2.TM_CCOEFF_NORMED)
        _, mx, _, loc = cv2.minMaxLoc(res)
        if mx < NCC_MIN:
            return None
        return sx0 + loc[0], sy0 + loc[1], s, float(mx)

    def _window(
        self, frame: NDArray[Any], at: tuple[int, int, float, float]
    ) -> tuple[tuple[int, int, int, int], float]:
        """Reading window (the board text with a margin) where the patch was found, and the zoom
        that brings the board's text to TEXT_MIN_PX."""
        lock = self._lock
        assert lock is not None
        x, y, s, _ = at
        bx1, by1, bx2, by2 = lock.box
        rx1, ry1 = bx1 * s + x, by1 * s + y
        rx2, ry2 = bx2 * s + x, by2 * s + y
        th = lock.text_h * s
        h, w = frame.shape[:2]
        mx, my = 1.5 * th + 0.15 * (rx2 - rx1), 1.2 * th
        win = (
            int(max(0, rx1 - mx)),
            int(max(0, ry1 - my)),
            int(min(w, rx2 + mx)),
            int(min(h, ry2 + my)),
        )
        zoom = min(MAX_ZOOM, max(1.0, TEXT_MIN_PX / max(th, 1.0)))
        return win, zoom

    # --- frames -------------------------------------------------------------------------------

    def _read_boxes(self, frame: NDArray[Any], at: tuple[int, int, float, float]) -> list[Token]:
        """Recognition alone on the text boxes of the last reading, moved with the board: enough
        while the board stands where it stood (fixed camera, a still pan)."""
        lock = self._lock
        assert lock is not None
        h, w = frame.shape[:2]
        crops, kept = [], []
        for bx1, by1, bx2, by2 in lock.boxes:
            px, py = 0.08 * (bx2 - bx1) + 2, 0.15 * (by2 - by1) + 1
            x1, y1 = max(0, int(bx1 + at[0] - px)), max(0, int(by1 + at[1] - py))
            x2, y2 = min(w, int(bx2 + at[0] + px)), min(h, int(by2 + at[1] + py))
            if x2 - x1 < 4 or y2 - y1 < 4:
                return []
            crops.append(frame[y1:y2, x1:x2])
            kept.append((bx1 + at[0], by1 + at[1], bx2 + at[0], by2 + at[1]))
        self.stats.boxes += 1
        return [
            Token(text, *box, score)
            for (text, score), box in zip(self.ocr.recognise(crops), kept, strict=True)
            if score >= 0.8
        ]

    def add(self, index: int, frame: NDArray[Any]) -> None:
        if index < self._due:
            return
        t_ms = round(index * 1000 / self.fps)
        seen = False
        if self._lock is not None:
            self.stats.probes += 1
            at = self._locate(_gray(frame))
            if at is not None:
                self.stats.found += 1
                self.calls += 1
                r = None
                if at[2] == 1.0 and at[3] >= FAST_NCC and self._full_last:
                    tokens = self._read_boxes(frame, at)
                    r = parse_board(tokens, t_ms, stacked=self._stacked)
                    # a new score (or a misread of a box that no longer fits) is read in full
                    if r is None or (r.home, r.away) != self._last_score:
                        r = None
                if r is None:
                    win, zoom = self._window(frame, at)
                    self.stats.window += 1
                    tokens = self._ocr(frame, win, zoom)
                    r = parse_board(tokens, t_ms, stacked=self._stacked)
                    if r is not None and r.home is not None and r.away is not None:
                        # the whole board read: lock anew where it is now (follows the zoom)
                        self._make_lock(frame, tokens, r)
                    elif r is not None and at[2] == 1.0:
                        self._lock.at = (at[0], at[1])
                elif self._lock is not None:
                    self._lock.at = (at[0], at[1])
                if r is not None:
                    seen = True
                    self._store(t_ms, tokens)
                    self._note(r)
        if not seen and t_ms - self._last_full >= self.full_ms:
            self._last_full = t_ms
            self.calls += 1
            self.stats.full += 1
            tokens = self._ocr(frame, None, 1.0)
            r = parse_board(tokens, t_ms, stacked=self._stacked)
            if r is not None:
                seen = True
                self._store(t_ms, tokens)
                self._make_lock(frame, tokens, r)
                self._note(r)
        if seen or self._lock is None:
            self._due = index + self.step
        else:  # locked board out of view: probe again soon
            self._due = index + min(self.step, self.probe_step)

    def _note(self, r: BoardReading) -> None:
        self._full_last = r.home is not None and r.away is not None
        if self._full_last:
            self._last_score = (r.home, r.away)

    def _store(self, t_ms: int, tokens: list[Token]) -> None:
        self.samples.append((t_ms, tokens))
        self._readings = None
        self._votes.add(t_ms, tokens)
        self._stacked = self._votes.result()

    @property
    def readings(self) -> list[BoardReading]:
        if self._readings is None:
            stacked = self._stacked
            out = []
            for t, tokens in self.samples:
                r = parse_board(tokens, t, stacked=stacked)
                if r is not None:
                    out.append(r)
            self._readings = out
        return self._readings

    def summary(self, sequence: Sequence[Sequence[int]] | None = None) -> dict[str, Any]:
        readings = self.readings
        return {
            "source": "hall_scoreboard",
            "readings": len(readings),
            "calls": self.calls,
            "ocr": {
                "full": self.stats.full,
                "window": self.stats.window,
                "boxes": self.stats.boxes,
                "probes": self.stats.probes,
                "found": self.stats.found,
            },
            "stacked": self._stacked,
            "goals": goals_from_board(readings, sequence),
            "board_clock": [[r.t_ms, r.clock_s] for r in readings if r.clock_s is not None][:2000],
        }
