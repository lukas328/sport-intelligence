"""Score and match clock from a broadcast overlay (BRIEF 7.2 stage 10, source `scoreboard_ocr`).

League streams burn a score bug into the picture ("LEI 2 : 1 ARB  03:34"). It is the most reliable
goal source there is: exact score, which side scored, and the match clock. No model needs training;
the text is clean, so Tesseract (Apache-2.0, a system binary) reads it.

1. Find the overlay: on frames spread over the video, overlay pixels stay the same while the panning
   camera changes everything else. Stable, textured blobs in the top or bottom band are the
   candidates. A fixed camera (the whole hall is stable) is skipped: there is no way to tell an
   overlay from the hall, and club recordings rarely have one.
2. Find the fields: Tesseract word boxes on a few candidate crops; a token like `2:1` / `2 : 1` is a
   score, `03:34` a clock. Over time the clock follows the video clock, a score does not.
3. Read while the video streams: a field is read again only when its pixels change (score) or every
   few seconds (clock), so a 60-minute game costs a few hundred Tesseract calls.
4. Clean the readings: a score counts once it is read twice in a row, may only grow by one goal per
   side, and a goal is placed at the first reading of the new score. The clock is turned into a
   mapping video time -> match clock (runs, stops) for the match clock of every event.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Any

import cv2
import numpy as np
from numpy.typing import NDArray

U8 = NDArray[Any]
Box = tuple[int, int, int, int]  # x, y, w, h in full-resolution pixels

SCORE_RE = re.compile(r"^(\d{1,2})\s*[:\-]\s*(\d{1,2})$")
CLOCK_RE = re.compile(r"^(\d{1,2})[:.](\d{2})$")


def available() -> bool:
    return shutil.which("tesseract") is not None


def _prep(crop: U8, scale: float = 3.0) -> U8:
    """Grey, enlarged, binarised, dark text on white (what Tesseract reads best)."""
    grey = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.ndim == 3 else crop
    grey = cv2.resize(grey, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    _, bw = cv2.threshold(grey, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # text is the minority colour of the box
    if (bw > 0).mean() < 0.5:
        bw = 255 - bw
    return np.asarray(cv2.copyMakeBorder(bw, 12, 12, 12, 12, cv2.BORDER_CONSTANT, value=255))


def _tesseract(img: U8, psm: int, whitelist: str | None = None, tsv: bool = False) -> str:
    ok, png = cv2.imencode(".png", img)
    if not ok:
        return ""
    cmd = ["tesseract", "stdin", "stdout", "--psm", str(psm), "-l", "eng"]
    if whitelist:
        cmd += ["-c", f"tessedit_char_whitelist={whitelist}"]
    if tsv:
        cmd += ["tsv"]
    try:
        out = subprocess.run(  # noqa: S603 - fixed binary and arguments, image on stdin
            cmd,
            input=png.tobytes(),
            capture_output=True,
            timeout=20,
            env={"OMP_THREAD_LIMIT": "1", "PATH": "/usr/bin:/bin:/usr/local/bin"},
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return out.stdout.decode(errors="ignore")


def read_text(crop: U8, digits: bool = True) -> str:
    text = _tesseract(_prep(crop), 7, "0123456789:-" if digits else None)
    return " ".join(text.split())


def parse_score(text: str) -> tuple[int, int] | None:
    m = SCORE_RE.match(text.replace(" ", ""))
    if not m:
        return None
    a, b = int(m.group(1)), int(m.group(2))
    return (a, b) if a <= 70 and b <= 70 else None


def parse_clock(text: str) -> int | None:
    m = CLOCK_RE.match(text.replace(" ", ""))
    if not m:
        return None
    mm, ss = int(m.group(1)), int(m.group(2))
    return mm * 60 + ss if ss < 60 and mm <= 80 else None


# --- 1. where is the overlay? ----------------------------------------------------------------


def find_overlay(frames: list[U8], max_share: float = 0.12) -> list[Box]:
    """Boxes of stable, textured regions in the top and bottom quarter (empty: no overlay or a
    fixed camera)."""
    if len(frames) < 8:
        return []
    grey = np.stack([cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32) for f in frames])
    med = np.median(grey, axis=0)
    stable = (np.abs(grey - med) < 8).mean(axis=0) > 0.8
    h, w = med.shape
    if stable.mean() > 0.3:  # fixed camera: the hall itself is stable
        return []
    grad = np.abs(cv2.Sobel(med, cv2.CV_32F, 1, 0)) + np.abs(cv2.Sobel(med, cv2.CV_32F, 0, 1))
    mask = (stable & (grad > 60)).astype(np.uint8)
    band = np.zeros_like(mask)
    band[: h // 4] = 1
    band[3 * h // 4 :] = 1
    mask = np.asarray(
        cv2.morphologyEx(mask * band, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8)), np.uint8
    )
    n, _, stats, _ = cv2.connectedComponentsWithStats(mask)
    boxes = [
        (int(x), int(y), int(bw), int(bh))
        for x, y, bw, bh, area in stats[1:n]
        if area >= 0.0003 * h * w and bw * bh <= max_share * h * w and bh < h // 4
    ]
    return boxes


def _union(boxes: list[Box], pad: int, size: tuple[int, int]) -> Box:
    x0 = max(0, min(b[0] for b in boxes) - pad)
    y0 = max(0, min(b[1] for b in boxes) - pad)
    x1 = min(size[0], max(b[0] + b[2] for b in boxes) + pad)
    y1 = min(size[1], max(b[1] + b[3] for b in boxes) + pad)
    return x0, y0, x1 - x0, y1 - y0


# --- 2. which field is what? -------------------------------------------------------------------


@dataclass
class Field:
    kind: str  # "score" or "clock"
    box: Box
    votes: int = 0
    seen: list[Box] = field(default_factory=list, repr=False)


def _words(crop: U8) -> list[tuple[str, Box]]:
    """Tesseract word boxes on the overlay crop (crop coordinates). Overlays mix light text on
    dark boxes and dark on light, so the crop is read as it is and inverted."""
    scale = 2.0
    grey = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    big = cv2.resize(grey, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    out: list[tuple[str, Box]] = []
    for img in (big, 255 - big):
        for row in _tesseract(img, 11, tsv=True).splitlines()[1:]:
            cols = row.split("\t")
            if len(cols) < 12 or not cols[11].strip():
                continue
            x, y, w, h = (int(int(c) / scale) for c in cols[6:10])
            box = (x, y, w, h)
            if not any(_iou(box, b) > 0.5 for _, b in out):  # read in both polarities
                out.append((cols[11].strip(), box))
    return out


def _merge_tokens(words: list[tuple[str, Box]]) -> list[tuple[str, Box]]:
    """`2` `:` `1` on one line -> `2:1` (scores are often spaced out)."""
    words = sorted(words, key=lambda wb: (wb[1][1] // 12, wb[1][0]))
    out: list[tuple[str, Box]] = []
    i = 0
    while i < len(words):
        text, box = words[i]
        j = i + 1
        while j < len(words) and len(text) < 7:
            nt, nb = words[j]
            same_line = abs((nb[1] + nb[3] / 2) - (box[1] + box[3] / 2)) < max(box[3], nb[3]) * 0.6
            gap = nb[0] - (box[0] + box[2])
            close = -0.3 * max(box[3], nb[3]) < gap < max(box[3], nb[3]) * 1.5
            if not (same_line and close and re.fullmatch(r"[\d:\-]+", nt + text[-1:])):
                break
            x0, y0 = min(box[0], nb[0]), min(box[1], nb[1])
            x1 = max(box[0] + box[2], nb[0] + nb[2])
            y1 = max(box[1] + box[3], nb[1] + nb[3])
            text, box = text + nt, (x0, y0, x1 - x0, y1 - y0)
            j += 1
        out.append((text, box))
        i = j
    return out


def find_fields(crops: list[tuple[float, U8]], origin: tuple[int, int]) -> list[Field]:
    """Score and clock fields from a few overlay crops taken at known video times (seconds)."""
    found: list[tuple[str, Box, float, int]] = []
    for t, crop in crops:
        for text, (x, y, w, h) in _merge_tokens(_words(crop)):
            clock = parse_clock(text)
            score = parse_score(text)
            pad = max(3, h // 5)
            box = (origin[0] + x - pad, origin[1] + y - pad, w + 2 * pad, h + 2 * pad)
            if clock is not None and len(text.replace(" ", "")) >= 4:
                found.append(("clock", box, t, clock))
            elif score is not None:
                found.append(("score", box, t, 0))
    fields: list[Field] = []
    for kind, box, _, _ in found:
        for f in fields:
            if f.kind == kind and _iou(f.box, box) > 0.3:
                f.votes += 1
                f.seen.append(box)
                f.box = tuple(int(v) for v in np.median(np.array(f.seen), axis=0))  # type: ignore[assignment]
                break
        else:
            fields.append(Field(kind, box, 1, [box]))
    # the clock moves with the video; a "clock" reading that does not is a score like 12:10
    clocks = [(t, c) for k, _, t, c in found if k == "clock"]
    keep = []
    for f in fields:
        if f.votes < 2:
            continue
        if f.kind == "clock" and len(clocks) >= 2:
            ts = [c for k, b, t, c in found if k == "clock" and _iou(b, f.box) > 0.3]
            if len(set(ts)) < 2:
                f.kind = "score"
        keep.append(f)
    best: dict[str, Field] = {}
    for f in keep:
        if f.kind not in best or f.votes > best[f.kind].votes:
            best[f.kind] = f
    return list(best.values())


def _iou(a: Box, b: Box) -> float:
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[0] + a[2], b[0] + b[2]), min(a[1] + a[3], b[1] + b[3])
    inter = max(0, x1 - x0) * max(0, y1 - y0)
    return inter / float(a[2] * a[3] + b[2] * b[3] - inter or 1)


# --- 3. read while the video streams -----------------------------------------------------------


@dataclass
class Reader:
    """Feed frames in order with `add`. The score is read when its pixels change and at least every
    `score_every_s`; the clock every `clock_every_s` (it only shows when the clock runs)."""

    fields: list[Field]
    fps: float
    look_every_s: float = 1.0
    score_every_s: float = 15.0
    clock_every_s: float = 15.0
    scores: list[tuple[int, tuple[int, int]]] = field(default_factory=list)  # (t_ms, score)
    clocks: list[tuple[int, int]] = field(default_factory=list)  # (t_ms, clock_s)
    calls: int = 0
    _thumb: U8 | None = None
    _misses: int = 0  # unreadable score readings in a row (retried up to 3 times)
    _score_ms: int = -(10**9)
    _clock_ms: int = -(10**9)

    def add(self, index: int, frame: U8) -> None:
        if index % max(1, round(self.fps * self.look_every_s)):
            return
        t_ms = round(index * 1000 / self.fps)
        for f in self.fields:
            x, y, w, h = f.box
            crop = frame[max(0, y) : y + h, max(0, x) : x + w]
            if crop.size == 0:
                continue
            if f.kind == "score":
                thumb = cv2.resize(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY), (48, 16)).astype(float)
                changed = self._thumb is None or float(np.abs(thumb - self._thumb).mean()) > 6
                retry = 0 < self._misses <= 3
                if not changed and not retry and t_ms - self._score_ms < self.score_every_s * 1000:
                    if self.scores:  # unchanged pixels: the same score again
                        self.scores.append((t_ms, self.scores[-1][1]))
                    continue
                self._thumb, self._score_ms = thumb, t_ms
                self.calls += 1
                score = parse_score(read_text(crop))
                if score is not None:
                    self.scores.append((t_ms, score))
                    self._misses = 0
                else:
                    self._misses += 1
            elif t_ms - self._clock_ms >= self.clock_every_s * 1000:
                self._clock_ms = t_ms
                self.calls += 1
                clock = parse_clock(read_text(crop))
                if clock is not None:
                    self.clocks.append((t_ms, clock))


# --- 4. clean the readings ---------------------------------------------------------------------


@dataclass(frozen=True)
class Goal:
    t_ms: int
    side: str  # "left" or "right" of the overlay
    score: tuple[int, int]


def goals_from_scores(reads: list[tuple[int, tuple[int, int]]], confirm: int = 2) -> list[Goal]:
    """Goals from noisy score readings. A new score counts once it is read `confirm` times in a
    row. It may add one goal; a bigger jump (overlay hidden for a while) is accepted only when it
    stays for `3 * confirm` readings and adds at most three goals. Everything else is a misreading.
    A goal is placed at the first reading of the new score."""
    goals: list[Goal] = []
    current: tuple[int, int] | None = None
    pending: tuple[int, int] | None = None
    first_ms = count = 0
    for t_ms, score in reads:
        if score == current:
            pending = None
            continue
        if score != pending:
            pending, first_ms, count = score, t_ms, 0
        count += 1
        if count < confirm:
            continue
        if current is None:
            current = score
            continue
        da, db = score[0] - current[0], score[1] - current[1]
        single = (da, db) in ((1, 0), (0, 1))
        if single or (da >= 0 and db >= 0 and da + db <= 3 and count >= 3 * confirm):
            goals += [Goal(first_ms, "left", score)] * da + [Goal(first_ms, "right", score)] * db
            current, pending = score, None
    return goals


def first_score(
    reads: list[tuple[int, tuple[int, int]]], confirm: int = 2
) -> tuple[int, int] | None:
    run: tuple[int, int] | None = None
    count = 0
    for _, s in reads:
        count = count + 1 if s == run else 1
        run = s
        if count >= confirm:
            return s
    return None


def clock_segments(reads: list[tuple[int, int]], tol_s: float = 2.5) -> list[dict[str, int]]:
    """Runs of the match clock: stretches where clock - video time is constant. Each segment says
    `clock_s = start_clock_s + (t_ms - start_ms) / 1000` from `start_ms` to `end_ms`."""
    segs: list[dict[str, int]] = []
    for t_ms, c in reads:
        offset = c - t_ms / 1000
        if segs:
            s = segs[-1]
            s_off = s["start_clock_s"] - s["start_ms"] / 1000
            if abs(offset - s_off) <= tol_s:
                s["end_ms"] = t_ms
                s["reads"] += 1
                continue
        segs.append({"start_ms": t_ms, "end_ms": t_ms, "start_clock_s": c, "reads": 1})
    return [s for s in segs if s["reads"] >= 2]


def read_overlay_summary(reader: Reader) -> dict[str, Any]:
    goals = goals_from_scores(reader.scores)
    return {
        "fields": [{"kind": f.kind, "box": list(f.box)} for f in reader.fields],
        "first_score": first_score(reader.scores),
        "last_score": goals[-1].score if goals else first_score(reader.scores),
        "goals": [{"t_ms": g.t_ms, "side": g.side, "score": list(g.score)} for g in goals],
        "clock": clock_segments(reader.clocks),
        "ocr_calls": reader.calls,
    }
