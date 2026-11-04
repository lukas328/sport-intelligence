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
    banner_reads: list[tuple[int, str, str]] = field(default_factory=list)  # (t_ms, side, text)
    _thumb: U8 | None = None
    _hue: float | None = None  # colour of the overlay boxes (name banners share it)
    _banner_since: int = -(10**9)
    _banner_reads_now: int = 0
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
        self._banner(t_ms, frame)

    def _banner(self, t_ms: int, frame: U8) -> None:
        """Name banners ("7 Amy HOCHREUTENER") pop up after goals in the overlay's colour, left
        for the home team, right for the away team: read a few times while one is shown."""
        score = next((f for f in self.fields if f.kind == "score"), None)
        if score is None:
            return
        if self._hue is None:
            self._hue = _box_hue(frame, score.box)
            if self._hue is None:
                self._hue = -1.0  # white or grey overlay: no coloured banners to look for
        if self._hue < 0:
            return
        found = _find_banner(frame, self._hue, self.fields)
        if found is None:
            self._banner_reads_now = 0
            return
        x0, y0, x1, y1 = found
        if t_ms - self._banner_since > 3000:
            self._banner_reads_now = 0
        self._banner_since = t_ms
        if self._banner_reads_now >= 4:
            return
        self._banner_reads_now += 1
        self.calls += 1
        crop = frame[y0:y1, x0:x1]
        big = cv2.resize(crop, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
        grey = 255 - cv2.cvtColor(big, cv2.COLOR_BGR2GRAY)  # light text on the banner colour
        text = " ".join(_tesseract(np.asarray(grey), 7).split())
        centre = score.box[0] + score.box[2] / 2
        self.banner_reads.append((t_ms, "left" if (x0 + x1) / 2 < centre else "right", text))


def _box_hue(frame: U8, box: Box) -> float | None:
    """Dominant saturated hue (OpenCV 0..180) inside an overlay box, or None."""
    x, y, w, h = box
    hsv = cv2.cvtColor(frame[max(0, y) : y + h, max(0, x) : x + w], cv2.COLOR_BGR2HSV)
    sat = hsv[..., 1] > 120
    if sat.mean() < 0.3:
        return None
    hue = hsv[..., 0][sat].astype(np.float64)
    ang = hue / 180 * 2 * np.pi  # circular mean (red wraps around 0)
    return float(
        (np.arctan2(np.sin(ang).mean(), np.cos(ang).mean()) % (2 * np.pi)) / (2 * np.pi) * 180
    )


def _find_banner(frame: U8, hue: float, fields: list[Field]) -> tuple[int, int, int, int] | None:
    """A wide bar in the overlay colour outside the score bug: (x0, y0, x1, y1) or None."""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    d = np.abs(hsv[..., 0].astype(np.int16) - round(hue)) % 180
    mask = (np.minimum(d, 180 - d) < 10) & (hsv[..., 1] > 140) & (hsv[..., 2] > 100)
    for f in fields:  # the score bug itself, generously
        x, y, w, h = f.box
        mask[max(0, y - 60) : y + h + 60, max(0, x - 60) : x + w + 60] = False
    cols = mask.sum(axis=0) > 15
    if cols.sum() < 150:
        return None
    xs = np.nonzero(cols)[0]
    # the widest run of banner columns
    runs = np.split(xs, np.nonzero(np.diff(xs) > 8)[0] + 1)
    run = max(runs, key=len)
    if len(run) < 150:
        return None
    x0, x1 = int(run[0]), int(run[-1]) + 1
    rows = np.nonzero(mask[:, x0:x1].sum(axis=1) > 0.5 * (x1 - x0))[0]
    if len(rows) < 10 or rows[-1] - rows[0] > 80:
        return None
    return x0, int(rows[0]), x1, int(rows[-1]) + 1


BANNER_RE = re.compile(
    r"(\d{1,2})[\s.,:]*([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ'\-]+(?:\s*[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ'\-]+)+)"
)


def parse_banner(text: str) -> tuple[int, str] | None:
    """'| 7 Amy HOCHREUTENER |' -> (7, 'Amy HOCHREUTENER'); '33DeniseSCHWAIGER' works too."""
    t = re.sub(r"(?<=[a-zà-ÿ])(?=[A-ZÀ-Þ]{2})", " ", text)  # DeniseSCHWAIGER -> Denise SCHWAIGER
    m = BANNER_RE.search(t)
    if not m:
        return None
    words = [w for w in m.group(2).split() if len(w) >= 2]
    caps = [k for k, w in enumerate(words) if w.isupper()]
    if caps:  # surnames in capitals: what follows the last one is OCR noise ("ZIMMERLI ton")
        words = words[: caps[-1] + 1]
    if len(words) < 2:
        return None
    return int(m.group(1)), " ".join(words[:3])


def _name_key(name: str) -> str:
    return re.sub(r"[^a-z]", "", name.lower())


def banners(reads: list[tuple[int, str, str]], gap_ms: int = 2500) -> list[dict[str, Any]]:
    """Banner appearances with one number and name each. A name keeps one number all match, so the
    number is voted over all appearances of that name (OCR reads 11 as 44 now and then)."""
    groups: list[list[tuple[int, str, tuple[int, str]]]] = []
    for t, side, text in reads:
        parsed = parse_banner(text)
        if parsed is None:
            continue
        if groups and groups[-1][-1][1] == side and t - groups[-1][-1][0] <= gap_ms:
            groups[-1].append((t, side, parsed))
        else:
            groups.append([(t, side, parsed)])
    by_name: dict[str, list[int]] = {}
    names: dict[str, str] = {}
    for g in groups:
        for _, _, (n, name) in g:
            by_name.setdefault(_name_key(name), []).append(n)
            names.setdefault(_name_key(name), name)
    out = []
    for g in groups:
        keys = [_name_key(name) for _, _, (_, name) in g]
        key = max(set(keys), key=keys.count)
        numbers = by_name[key]
        out.append(
            {
                "t_ms": g[0][0],
                "side": g[0][1],
                "number": max(set(numbers), key=numbers.count),
                "name": names[key],
            }
        )
    return out


def attach_scorers(
    goals: list[Goal], shown: list[dict[str, Any]], window_ms: int = 20000
) -> list[dict[str, Any]]:
    """Each goal with the first banner on its side within `window_ms` after it (or just before:
    the overlay score can lag behind the banner)."""
    out = []
    used: set[int] = set()
    for g in goals:
        cand = [
            (k, b)
            for k, b in enumerate(shown)
            if k not in used and b["side"] == g.side and -3000 <= b["t_ms"] - g.t_ms <= window_ms
        ]
        entry: dict[str, Any] = {"t_ms": g.t_ms, "side": g.side, "score": list(g.score)}
        if cand:
            k, b = min(cand, key=lambda kb: kb[1]["t_ms"])
            used.add(k)
            entry["scorer"] = {"number": b["number"], "name": b["name"]}
        out.append(entry)
    return out


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
    shown = banners(reader.banner_reads)
    return {
        "fields": [{"kind": f.kind, "box": list(f.box)} for f in reader.fields],
        "first_score": first_score(reader.scores),
        "last_score": goals[-1].score if goals else first_score(reader.scores),
        "goals": attach_scorers(goals, shown),
        "banners": shown,
        "clock": clock_segments(reader.clocks),
        "ocr_calls": reader.calls,
    }
