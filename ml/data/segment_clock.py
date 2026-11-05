"""Match clock inside the ingest's 3-minute segments, and official game logs as segment labels.

The official logs (ml/data/official/<name>.json: every goal, shot, save, suspension with the match
clock) become labels on the segments of ml/data/ingest_drive.py once the clock shown in each segment
is known. Same sources as ml/eval/align_official.py (score overlay first, else the hall board),
made cheap enough for the ingest (well under a minute of CPU per segment, a few seconds when there
is no clock):

- frames are decoded without the non-reference frames (skip_frame NONREF, about half the decode
  work) and scaled to at most 1280 wide; the overlay finder and the probes use the key frames;
- the reader is `hallboard`'s (PP-OCR, data/models/ch_PP-OCRv4_*.onnx; not Tesseract, whose
  clock field merged score and clock on the SG Waedenswil/Horgen overlay): text split into fields
  (`split_token`), a field with letters or spaces around the colon is a score, never the clock
  ("SGW 19 : 16 GOS", "16:00 Uhr" on a pre-match graphic), the clock is the field under the score
  (not a penalty timer beside it), and of two bare `mm:ss` fields stacked on a stream graphic the
  one that keeps changing is the clock (`StackedVotes`, voted over the whole segment; until it is
  decided such a frame gives no clock). `HallBoardReader` reads every 2 s: text detection until a
  clock is in view, then the board is locked (template matching) and only a window around it is
  read, recognition alone while it stands still; a lost board is probed for every 0.5 s;
- overlay: `scoreboard.find_overlay` (stable, textured boxes in the top or bottom band; each band
  on its own, so a logo in the other band does not blow up the crop); the band counts when its
  clock fields change between six key frames; then the reader runs on that window;
- hall board: first a probe on six key frames (no clock field there: return None), then the
  reader on the whole frame from the probe before the first one with a clock (pre-match graphics
  and tables come first), with text detection on the whole frame at most every 10 s while the
  board is lost. A fixed camera hides an overlay from `find_overlay` (everything is stable); its
  clock is then found here and called "hall_board".

Readings that disagree with both neighbours are dropped (`align_official._clean`, then runs of up
to two readings that disagree with the runs on both sides); fewer than two
readings left, or readings that move but never run at 1 s/s for 10 s in total (not a match clock),
mean no clock.

    # clock of single segments (JSON per line; what the ingest calls in a subprocess)
    python ml/data/segment_clock.py SEG.mp4 [SEG.mp4 ...]
    # games of the ingest state without clock data of the current reader (CLOCK_READER) whose
    # segments are local (WORKDIR/batch_NN, or --search DIR/batch_NN, DIR)
    python ml/data/segment_clock.py --fill [--workdir W] [--search DIR ...] [--batch batch_NN ...]
        [--write-state]
    # official log entries inside the segments -> ml/data/segment_labels/<name>.json
    python ml/data/segment_clock.py --labels [--workdir W]

`--fill` writes WORKDIR/clocks.json (a running ingest owns state.json and would overwrite it; the
ingest merges clocks.json into its state when it starts and before every poll). `--write-state`
also merges into state.json: only while the ingest is stopped. Clock data carries the version of
its reader ("reader"); data of a newer reader replaces older data wherever the two are merged
(`--labels` reads state.json with clocks.json merged in this way).

Labels: per segment its own readings, the half from the readings of the whole game (a drop of the
clock between or inside segments starts the second half; readings at 30:00 and above are a
continuing second half). Each entry: the official entry (match_s, kind, team, number, name, score,
...) plus segment file, segment_ms, video_ms (in the full video: start_s + segment_ms) and
anchor_gap_s (match seconds to the reading it was counted from). Entries at the clock value the
segment starts with while that clock stands still are left out (they happened when it stopped,
possibly before the segment); segments[k]["skipped_at_stopped_start"] counts them.
"""

from __future__ import annotations

import argparse
import json
import re
import os
import resource
import sys
import time
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "ml" / "eval"))

from align_official import (  # noqa: E402
    HALF_S,
    RESET_DROP_S,
    _clean,
    _consistent,
    anchors,
    locate,
    official_entries,
)

SCRATCH = Path(os.environ.get(
    "HANDBALL_SCRATCH",
    "/tmp/claude-0/-home-user/3dc450e2-2499-5e21-b252-1c4e366c6b5a/scratchpad",
))
MODELS = REPO / "data" / "models"
OFFICIAL = REPO / "ml" / "data" / "official"
LABELS = REPO / "ml" / "data" / "segment_labels"
SIDECAR = "clocks.json"

MAX_WIDTH = 1280  # the ingest's segments are 1280 wide; larger test videos are scaled to it
OVERLAY_EVERY_S = 2.0
BOARD_EVERY_S = 2.0
BOARD_FULL_EVERY_S = 10.0  # full-frame text detection while the board is out of view
BOARD_PROBES = 6
BOARD_GIVE_UP_S = 60.0  # under two board readings in the first minute: give up
MAX_CPU_S = 90.0  # stop reading (keep what was read) beyond this
SEGMENT_S = 180.0
FEED_MS = 250  # frames handed to the board reader; it reads those due and probes in between
PROBE_EVERY_S = 0.5  # template probes for a locked board that is out of view
# version of the clock reading: clock data of an older reader is read again by --fill and
# replaced on merge (1: `parse_board` per frame without layout; 2: `HallBoardReader`, layout voted)
CLOCK_READER = 2

Sample = tuple[int, float]


def cpu_s() -> float:
    a = resource.getrusage(resource.RUSAGE_SELF)
    b = resource.getrusage(resource.RUSAGE_CHILDREN)  # tesseract
    return a.ru_utime + a.ru_stime + b.ru_utime + b.ru_stime


# --- frames ---------------------------------------------------------------------------------


def _open(path: Path, skip: str) -> tuple[Any, Any, float, tuple[int, int]]:
    import av

    container = av.open(str(path))
    stream = container.streams.video[0]
    stream.thread_type = "AUTO"
    stream.codec_context.thread_count = 2
    stream.codec_context.skip_frame = skip  # type: ignore[assignment]  # av checks the name
    start = float(stream.start_time * stream.time_base) if stream.start_time is not None else 0.0
    w, h = stream.codec_context.width, stream.codec_context.height
    if w > MAX_WIDTH:
        w, h = MAX_WIDTH, round(h * MAX_WIDTH / w / 2) * 2
    return container, stream, start, (w, h)


def frames(path: Path, every_ms: int = 0, skip: str = "NONREF") -> Iterator[tuple[int, Any]]:
    """(ms from the segment start, BGR frame at most 1280 wide): the first decoded frame at or
    after every multiple of `every_ms` (0: every decoded frame, e.g. all key frames)."""
    container, stream, start, (w, h) = _open(path, skip)
    due = 0
    try:
        for frame in container.decode(stream):
            if frame.time is None:
                continue
            t = round((float(frame.time) - start) * 1000)
            if t < due - 20:
                continue
            yield t, frame.to_ndarray(format="bgr24", width=w, height=h)
            if every_ms:
                while due <= t + 20:  # a frame just before `due` stood in for it
                    due += every_ms
    finally:
        container.close()


def duration_ms(path: Path) -> int:
    import av

    with av.open(str(path)) as c:
        s = c.streams.video[0]
        if s.duration is not None:
            return round(float(s.duration * s.time_base) * 1000)
        return round((c.duration or 0) / 1000)


# --- clock text (PP-OCR, `hallboard`) ------------------------------------------------------

Window = tuple[int, int, int, int]  # x0, y0, x1, y1


def ocr_reader(models: Path, threads: int = 2) -> Any:
    """The PP-OCR text detector and recogniser of `hallboard` (data/models/ch_PP-OCRv4_*)."""
    from handball_vision.numbers import NumberReader

    return NumberReader(
        models / "ch_PP-OCRv4_det_infer.onnx",
        models / "ch_PP-OCRv4_rec_infer.onnx",
        threads=threads,
    )


def clock_values(ocr: Any, frame: Any, win: Window | None = None) -> frozenset[int]:
    """Values of the fields in `win` of the frame (None: all of it) that may be a clock
    (`hallboard.clock_fields`: `mm:ss`, no certain score)."""
    from handball_vision.hallboard import clock_fields, read_tokens

    tokens, _ = read_tokens(ocr, frame, win)
    return frozenset(c for _, c in clock_fields(tokens))


def board_clock(reader: Any) -> list[Sample]:
    """Clock readings of a `hallboard.HallBoardReader`: each sample parsed with the layout voted
    over all samples (`parse_board` with `stacked`), samples whose clock the layout leaves open
    left out."""
    return [(r.t_ms, float(r.clock_s)) for r in reader.readings if r.clock_s is not None]


def _crop(frame: Any, win: Window | None) -> Any:
    if win is None:
        return frame
    x0, y0, x1, y1 = win
    return frame[y0:y1, x0:x1]


def _blank(frame: Any, hide: Window | None) -> Any:
    if hide is not None:
        x0, y0, x1, y1 = hide
        frame[y0:y1, x0:x1] = 0
    return frame


def read_clock(
    path: Path,
    ocr: Any,
    every_s: float,
    budget_s: float,
    win: Window | None = None,
    hide: Window | None = None,
    full_every_s: float = BOARD_FULL_EVERY_S,
    give_up: bool = False,
    start_ms: int = 0,
) -> tuple[list[Sample], Any]:
    """(clock readings, reader): `hallboard.HallBoardReader` over the segment, on `win` of each
    frame (None: the whole frame; `hide` blanked). It reads every `every_s`: text detection until
    a clock is in view, then the board locked by template matching and only a window around it
    read (recognition alone while it stands still); between reads it probes for a lost board.
    Frames go to it every FEED_MS from `start_ms` on. `give_up`: stop when under two readings
    came in the first BOARD_GIVE_UP_S, or the readings after twice that are still no match
    clock."""
    from handball_vision.hallboard import HallBoardReader

    reader = HallBoardReader(
        ocr, fps=1000.0, every_s=every_s, full_every_s=full_every_s, probe_every_s=PROBE_EVERY_S
    )
    checked = 0
    for t, frame in frames(path, FEED_MS):
        if t < start_ms:
            continue
        reader.add(t, _crop(_blank(frame, hide), win))  # fps 1000: the frame index is its ms
        if cpu_s() > budget_s:
            break
        if not give_up:
            continue
        if len(reader.samples) != checked:
            checked = len(reader.samples)
            if t - start_ms > 2 * BOARD_GIVE_UP_S * 1000 and not plausible(
                clean(board_clock(reader))
            ):
                break  # two minutes of readings and still no match clock
        if len(reader.samples) < 2 and t - start_ms > BOARD_GIVE_UP_S * 1000:
            break
    return board_clock(reader), reader


# --- overlay --------------------------------------------------------------------------------


def overlay_windows(keys: Sequence[tuple[int, Any]]) -> list[Window]:
    """Score overlay candidates (`scoreboard.find_overlay`: stable, textured boxes in the top or
    bottom band while the camera pans), one window per band, the larger first."""
    from handball_vision import scoreboard

    if len(keys) < 8:
        return []
    spread = [f for _, f in keys]
    boxes = scoreboard.find_overlay(spread)
    h, w = spread[0].shape[:2]
    bands = [
        [b for b in boxes if b[1] + b[3] / 2 < h / 2],
        [b for b in boxes if b[1] + b[3] / 2 >= h / 2],
    ]
    out = []
    for band in sorted((b for b in bands if b), key=lambda b: -sum(x[2] * x[3] for x in b)):
        x, y, bw, bh = scoreboard._union(band, 10, (w, h))
        out.append((x, y, x + bw, y + bh))
    return out


def find_overlay_clock(
    ocr: Any, keys: Sequence[tuple[int, Any]], probes: int = BOARD_PROBES
) -> Window | None:
    """The overlay window whose clock fields change between the probe key frames (a running
    clock), or None."""
    picks = _spread(keys, probes)
    for win in overlay_windows(keys):
        seen = {v for _, f in picks if (v := clock_values(ocr, f, win))}
        if len(seen) >= 2:
            return win
    return None


# --- one segment ----------------------------------------------------------------------------


def clean(samples: Sequence[Sample], max_run: int = 2) -> list[Sample]:
    """`align_official._clean` (drops readings that agree with neither neighbour), then runs of
    at most `max_run` readings (consecutive readings that agree) that agree with neither the run
    before nor the run after: a misread twice in a row ("39:50" for "37:50"). A drop by more
    than RESET_DROP_S to at most 05:00 is a new half, not a disagreement."""
    s = _clean(samples)

    def fits(a: Sample, b: Sample) -> bool:
        # a restarted half reads low: inside a 3-minute segment at most a few minutes
        return _consistent(a, b) or (b[1] < a[1] - RESET_DROP_S and b[1] <= 300)

    runs: list[list[Sample]] = []
    for x in s:
        if runs and _consistent(runs[-1][-1], x):
            runs[-1].append(x)
        else:
            runs.append([x])
    out: list[Sample] = []
    for k, run in enumerate(runs):
        if len(run) <= max_run and len(runs) > 1:
            before = k > 0 and fits(runs[k - 1][-1], run[0])
            after = k + 1 < len(runs) and fits(run[-1], runs[k + 1][0])
            if not before and not after:
                continue
        out.extend(run)
    return out


def plausible(samples: Sequence[Sample], min_running_s: float = 10.0) -> bool:
    """A match clock either runs at 1 s/s or stands still. Readings that never run for
    `min_running_s` in total but do move (a wall clock, a counter, a misread field) are not one;
    a clock that stands still throughout (time-out, half time) is kept."""
    if len(samples) < 2:
        return False
    running, moved = 0.0, False
    for (v0, c0), (v1, c1) in zip(samples, samples[1:], strict=False):
        dv, dc = (v1 - v0) / 1000, c1 - c0
        if dc:
            moved = True
        if dc > 0 and abs(dc - dv) <= max(1.5, 0.15 * dv):
            running += dv
    return running >= min_running_s or not moved


def _spread(items: Sequence[Any], n: int) -> list[Any]:
    if len(items) <= n:
        return list(items)
    return [items[round(k * (len(items) - 1) / (n - 1))] for k in range(n)]


def read_segment_clock(
    path: Path | str,
    models: Path = MODELS,
    overlay_every_s: float = OVERLAY_EVERY_S,
    board_every_s: float = BOARD_EVERY_S,
    max_cpu_s: float = MAX_CPU_S,
) -> dict[str, Any]:
    """{"source": "overlay" | "hall_board" | None, "samples": [[segment_ms, clock_s], ...],
    "reader": CLOCK_READER, "stacked", "duration_ms", "cpu_s", "wall_s"}. Samples are the clock as
    shown (a second half may restart at 0 or continue at 30:00), misreads dropped."""
    import cv2

    cv2.setNumThreads(2)
    path = Path(path)
    c0, w0 = cpu_s(), time.time()
    budget = c0 + max_cpu_s
    result: dict[str, Any] = {
        "source": None, "samples": [], "reader": CLOCK_READER, "duration_ms": duration_ms(path)
    }
    keys = _spread(list(frames(path, 0, skip="NONKEY")), 48)
    if len(keys) < 12:  # long GOP: spread frames by seeking instead
        from handball_vision.pipeline import sample_frames

        n, dur = 24, result["duration_ms"]
        keys = [
            (round(dur * (k + 0.5) / n), _fit(f)) for k, f in enumerate(sample_frames(path, n))
        ]
    ocr = ocr_reader(models)
    readers: list[Any] = []
    win = find_overlay_clock(ocr, keys)
    hide: Window | None = None
    if win is not None:
        got, reader = read_clock(path, ocr, overlay_every_s, budget, win, full_every_s=0)
        readers.append(reader)
        samples = clean(got)
        if plausible(samples):
            result |= {"source": "overlay", "samples": [list(s) for s in samples]}
            result["stacked"] = reader.stacked
        else:  # a frozen overlay clock: hide it from the board reader
            hide = win
    if result["source"] is None and keys and cpu_s() < budget:
        probes = _spread(keys, BOARD_PROBES)
        hits = [k for k, (_, f) in enumerate(probes) if clock_values(ocr, _blank(f.copy(), hide))]
        if hits:
            # the clock may come into view after the start (a pre-match graphic, a table): read
            # from the probe before the first one that showed it
            start = probes[hits[0] - 1][0] if hits[0] else 0
            got, reader = read_clock(
                path, ocr, board_every_s, budget, hide=hide, give_up=True, start_ms=start
            )
            readers.append(reader)
            samples = clean(got)
            if plausible(samples):
                result |= {"source": "hall_board", "samples": [list(s) for s in samples]}
                result["stacked"] = reader.stacked
    result["ocr_calls"] = {
        k: sum(getattr(r.stats, k) for r in readers)
        for k in ("full", "window", "boxes", "probes", "found")
    }
    result["cpu_s"] = round(cpu_s() - c0, 1)
    result["wall_s"] = round(time.time() - w0, 1)
    if cpu_s() >= budget:
        result["truncated"] = True
    return result


def _fit(frame: Any) -> Any:
    import cv2

    h, w = frame.shape[:2]
    if w <= MAX_WIDTH:
        return frame
    return cv2.resize(frame, (MAX_WIDTH, round(h * MAX_WIDTH / w / 2) * 2))


# --- state, sidecar, fill -------------------------------------------------------------------


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def write_json(path: Path, data: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(path)


def clock_reader(clock: dict[str, Any] | None) -> int:
    """Version of the reader that made clock data (CLOCK_READER): 0 without data, 1 for data
    from before versions were stamped."""
    return int(clock.get("reader", 1)) if clock else 0


def merge_clocks(state: dict[str, Any], sidecar: dict[str, Any]) -> int:
    """Clock data of clocks.json ({name: {file: clock}}) into state entries that have none or
    data of an older reader (`clock_reader`); sets each touched game's has_clock. Returns the
    number of segments filled."""
    n = 0
    for name, segs in sidecar.items():
        g = state.get("games", {}).get(name)
        if not g or not g.get("segments"):
            continue
        for s in g["segments"]:
            side = segs.get(s.get("file"))
            if side is not None and clock_reader(side) > clock_reader(s.get("clock")):
                s["clock"] = side
                n += 1
        if any("clock" in s for s in g["segments"]):
            g["has_clock"] = any((s.get("clock") or {}).get("source") for s in g["segments"])
    return n


def fill(
    workdir: Path,
    search: Sequence[Path],
    write_state: bool,
    models: Path,
    batches: Sequence[str] = (),
) -> None:
    state = load_json(workdir / "state.json", {"games": {}})
    side_path = workdir / SIDECAR
    sidecar: dict[str, dict[str, Any]] = load_json(side_path, {})
    gone: list[str] = []
    for name, g in sorted(state.get("games", {}).items()):
        segs = g.get("segments") or []
        done = sidecar.get(name, {})
        todo = [
            s
            for s in segs
            if max(clock_reader(s.get("clock")), clock_reader(done.get(s["file"]))) < CLOCK_READER
        ]
        if not todo or (batches and g.get("batch") not in batches):
            continue
        dirs = [workdir / g["batch"], *(d / g["batch"] for d in search), *search]
        found = 0
        for s in todo:
            seg = next((d / s["file"] for d in dirs if (d / s["file"]).exists()), None)
            if seg is None:
                continue
            found += 1
            try:
                r = read_segment_clock(seg, models)
                clock = {"source": r["source"], "samples": r["samples"], "reader": r["reader"]}
            except Exception as exc:  # noqa: BLE001 - one bad file must not stop the rest
                if not seg.exists():  # uploaded and deleted meanwhile
                    print(f"{s['file']}: gone while reading", flush=True)
                    continue
                r, clock = {"cpu_s": None}, {"source": None, "samples": [], "error": str(exc)[:200]}
            sidecar.setdefault(name, {})[s["file"]] = clock
            write_json(side_path, sidecar)
            print(f"{s['file']}: {clock['source']} {len(clock['samples'])} readings, "
                  f"{r.get('cpu_s')} s CPU", flush=True)
        if not found:
            gone.append(f"{name} ({g['batch']})")
    if gone:
        print(f"{len(gone)} games without current clock data whose segments are not local "
              "(uploaded):")
        for line in gone:
            print(f"  {line}")
    if write_state:
        n = merge_clocks(state, sidecar)
        write_json(workdir / "state.json", state)
        print(f"state.json: {n} segments filled")


# --- labels ---------------------------------------------------------------------------------


def segment_halves(segments: Sequence[dict[str, Any]]) -> list[tuple[int, bool]]:
    """(half the segment's first reading is in, whether that is certain) per segment, from the
    readings of all segments on the full video's timeline. Certain: in the second half, or a
    second half follows later in the game; a first-half clock with no second half in view could
    be a restarted second half."""
    timeline: list[Sample] = []
    spans = []
    for s in segments:
        start = round(float(s.get("start_s", 0)) * 1000)
        samples = (s.get("clock") or {}).get("samples") or []
        timeline.extend((start + int(v), float(c)) for v, c in samples)
        spans.append((start, start + max((int(v) for v, _ in samples), default=0)))
    game = anchors(timeline)
    out = []
    for lo, hi in spans:
        inside = [a for a in game if lo <= a.video_ms <= hi + 1000]
        if not inside:
            out.append((1, False))
            continue
        half = 2 if inside[0].match_s > HALF_S else 1
        later_second = any(a.match_s > HALF_S for a in game if a.video_ms > hi)
        out.append((half, half == 2 or later_second))
    return out


def game_labels(name: str, game: dict[str, Any], official: dict[str, Any]) -> dict[str, Any]:
    entries = [e for e in official_entries(official) if e.get("match_s") is not None]
    segs = sorted(game.get("segments") or [], key=lambda s: float(s.get("start_s", 0)))
    halves = segment_halves(segs)
    video_ms = round(float(game.get("duration_s") or 0) * 1000)
    seg_out: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    for k, (s, (half, certain)) in enumerate(zip(segs, halves, strict=True)):
        clock = s.get("clock") or {}
        samples = [(int(v), float(c)) for v, c in clock.get("samples") or []]
        start_ms = round(float(s.get("start_s", 0)) * 1000)
        dur = round(SEGMENT_S * 1000)
        if video_ms:
            dur = max(0, min(dur, video_ms - start_ms))
        info: dict[str, Any] = {
            "file": s["file"], "start_s": s.get("start_s"), "clock_source": clock.get("source"),
            "readings": len(samples), "half": half if samples else None,
            "half_certain": certain if samples else None,
        }
        if samples:
            shown = anchors(samples, half)
            if shown:
                info["match_s"] = [shown[0].match_s, shown[-1].match_s]
        n0, skipped = len(rows), 0
        # the clock already stands at its first reading: an entry at that value happened when it
        # stopped, which may be before the segment (or before the clock came into view)
        stopped_at = samples[0][1] if len(samples) >= 2 and samples[1][1] == samples[0][1] else None
        if clock.get("source") and samples:
            for e in entries:
                found = locate(samples, e["match_s"], half)
                if found is None or not 0 <= found[0] <= dur:
                    continue
                shown = e["match_s"] - (HALF_S if half == 2 and samples[0][1] < HALF_S else 0)
                if stopped_at is not None and shown == stopped_at:
                    skipped += 1
                    continue
                rows.append({
                    **e, "segment": s["file"], "segment_index": k, "segment_ms": found[0],
                    "video_ms": start_ms + found[0], "anchor_gap_s": round(found[1], 2),
                    "half_certain": certain,
                })
        info["entries"] = len(rows) - n0
        info["skipped_at_stopped_start"] = skipped
        seg_out.append(info)
    kinds: dict[str, int] = {}
    for e in rows:
        kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
    return {
        "name": name,
        "official": f"ml/data/official/{name}.json",
        "game_id": official.get("game_id"),
        "result": official.get("result"),
        "video": {k: game.get(k) for k in ("width", "height", "fps", "duration_s", "batch")},
        "segments": seg_out,
        "counts": kinds,
        "entries": rows,
    }


def all_games(workdir: Path) -> dict[str, Any]:
    """Games of the ingest state, clock data of clocks.json merged in."""
    state = load_json(workdir / "state.json", {"games": {}})
    merge_clocks(state, load_json(workdir / SIDECAR, {}))
    return dict(state.get("games", {}))


def labels(workdir: Path, out_dir: Path, official_dir: Path = OFFICIAL) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for name, game in sorted(all_games(workdir).items()):
        if not any((s.get("clock") or {}).get("source") for s in game.get("segments") or []):
            continue
        # Drive names can carry a format suffix ("..._2023-09-23.f298"); the logs use the plain name
        official = load_json(official_dir / f"{re.sub(r'[.]f[0-9]+$', '', name)}.json", {})
        if not official.get("log"):
            continue
        result = game_labels(name, game, official)
        path = out_dir / f"{name}.json"
        write_json(path, result)
        written.append(path)
        print(f"{name}: {len(result['entries'])} entries in "
              f"{sum(1 for s in result['segments'] if s['clock_source'])} segments with a clock "
              f"{result['counts']}", flush=True)
    print(f"{len(written)} label files in {out_dir}")
    return written


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("segments", nargs="*", type=Path, help="segments to read (JSON per line)")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--fill", action="store_true", help="clock data for local ingest segments")
    mode.add_argument("--labels", action="store_true", help="write ml/data/segment_labels/")
    ap.add_argument("--workdir", type=Path, default=SCRATCH / "ingest", help="ingest workdir")
    ap.add_argument("--search", type=Path, nargs="*", default=[],
                    help="--fill: more folders holding batch_NN/ or the segments themselves")
    ap.add_argument("--batch", nargs="*", default=[], help="--fill: only these batches (batch_01)")
    ap.add_argument("--write-state", action="store_true",
                    help="--fill: also merge into state.json (only while the ingest is stopped)")
    ap.add_argument("--out", type=Path, default=LABELS)
    ap.add_argument("--models", type=Path, default=MODELS)
    a = ap.parse_args()
    if a.fill:
        fill(a.workdir, a.search, a.write_state, a.models, a.batch)
    elif a.labels:
        labels(a.workdir, a.out)
    elif a.segments:
        for seg in a.segments:
            print(json.dumps({"file": str(seg), **read_segment_clock(seg, a.models)}), flush=True)
    else:
        ap.error("give segments, --fill or --labels")


if __name__ == "__main__":
    main()
