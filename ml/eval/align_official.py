"""Official game logs (match clock) -> video time: every logged goal and shot points to a moment.

Federations publish a log of every goal, shot, save and suspension with the match clock
(ml/eval/official/). The video shows the same clock, on a broadcast overlay
(`handball_vision.scoreboard`) or on the hall scoreboard (`handball_vision.hallboard`). Clock
readings (video_ms, clock_s) are the bridge: `match_to_video` turns a match second into a video
millisecond, so public match data becomes labels without anybody clicking.

Clock rules: the clock counts up within a half and stops during time-outs. The second half either
continues at 30:00 (30-60) or restarts at 00:00; which one is decided from the readings (a drop of
the clock starts a new half; a half whose readings sit at 30:00 and above is a continuing second
half). Between two readings the clock is assumed to run at 1 s/s from the nearer reading, which is
exact unless the clock stopped in between; beyond the first or last reading of a half it
extrapolates at most `MAX_EXTRAPOLATE_S`.

    uv run --project packages/vision python ml/eval/align_official.py VIDEO OFFICIAL.json OUT.json
        [--start-half 2] [--video-offset-s 1835.5]

Output: {"video", "official", "clock_source", "clock_samples", "entries": [...]} where each entry
is the log entry in one shape (match_s, kind, team, number, name, score, ...) plus "video_ms"
(null when the moment is not in this video) and "anchor_gap_s" (match seconds to the nearest clock
reading: small means exact, large means a stopped clock in between could shift it). Mülheim-style
files that carry video timestamps already are only normalised (`--video-offset-s` when VIDEO is a
piece of the full video).
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

HALF_S = 1800
MAX_EXTRAPOLATE_S = 60.0
RESET_DROP_S = 60  # the clock falling by more than this starts a new half
NOISE_S = 2.0  # reading jitter tolerated when checking two readings against each other
RUN_TOL_S = 1.5  # readings whose clock - video time differ by less are one run of the clock

KINDS = {
    "Tor": "goal",
    "7m Tor": "penalty_goal",
    "Wurf Parade": "shot_saved",
    "Wurf Fehler": "shot_missed",
    "7m Parade": "penalty_saved",
    "7m Fehlwurf": "penalty_missed",
    "Techn. Fehler": "turnover",
    "Zeitstrafe": "suspension",
    "Verwarnung": "warning",
    "Team Time-Out": "timeout",
    "Empty Goal": "empty_goal",
    "Goalie in": "goalkeeper_in",
}


@dataclass(frozen=True)
class Anchor:
    video_ms: int
    match_s: float  # absolute match second, 0..3600


# --- alignment ------------------------------------------------------------------------------


def _consistent(a: tuple[int, float], b: tuple[int, float]) -> bool:
    """b follows a on a clock that runs at most at 1 s/s and never goes back."""
    dv = (b[0] - a[0]) / 1000
    dc = b[1] - a[1]
    return -NOISE_S <= dc <= dv + NOISE_S


def _clean(samples: Sequence[tuple[int, float]]) -> list[tuple[int, float]]:
    """Sorted readings that agree with at least one neighbour (an isolated misread is dropped).
    A lone reading is kept: there is nothing to check it against."""
    s = sorted((int(v), float(c)) for v, c in samples)
    if len(s) < 2:
        return s
    keep = []
    for i, cur in enumerate(s):
        prev_ok = i > 0 and _consistent(s[i - 1], cur)
        next_ok = i + 1 < len(s) and _consistent(cur, s[i + 1])
        # a half restart is inconsistent with the previous reading, but agrees with the next
        if prev_ok or next_ok:
            keep.append(cur)
    return keep


def anchors(clock_samples: Iterable[tuple[int, float]], start_half: int = 1) -> list[Anchor]:
    """Clock readings as absolute match seconds. A drop of the clock starts the next half; a run of
    readings at 30:00 and above is a continuing second half (30-60) whatever `start_half` says.
    `start_half` only matters for a restarting clock with no drop in view (a clip of the second
    half that shows 05:00): the clock alone cannot tell it from the first half."""
    groups: list[list[tuple[int, float]]] = []
    for v, c in _clean(list(clock_samples)):
        if groups and c < groups[-1][-1][1] - RESET_DROP_S:
            groups.append([])
        if not groups:
            groups.append([])
        groups[-1].append((v, c))
    out: list[Anchor] = []
    half = start_half
    for k, g in enumerate(groups):
        if k:
            half += 1
        if half > 2:  # extra time: not supported (logs of the games here end at 60:00)
            break
        continuing = statistics.median(c for _, c in g) >= HALF_S
        offset = HALF_S if half == 2 and not continuing else 0
        out.extend(Anchor(v, c + offset) for v, c in g)
    return _smooth(out)


def _smooth(points: list[Anchor]) -> list[Anchor]:
    """A whole-second clock read at some video time is up to a second off (when in that second the
    frame was taken). Along a run of the clock (clock - video time constant within `RUN_TOL_S`) the
    median offset of all its readings replaces each single one."""
    out: list[Anchor] = []
    run: list[Anchor] = []

    def flush() -> None:
        if run:
            off = statistics.median(a.match_s - a.video_ms / 1000 for a in run)
            out.extend(Anchor(round((a.match_s - off) * 1000), a.match_s) for a in run)
            run.clear()

    for a in points:
        if run:
            prev = run[-1]
            d_off = (a.match_s - a.video_ms / 1000) - (prev.match_s - prev.video_ms / 1000)
            if abs(d_off) > RUN_TOL_S or a.match_s < prev.match_s:
                flush()
        run.append(a)
    flush()
    return out


def _in_half(m: float, half: int) -> bool:
    # 30:00 belongs to both halves: the end of the first and the start of the second
    return m <= HALF_S if half == 1 else m >= HALF_S


def locate(
    clock_samples: Iterable[tuple[int, float]], match_s: float, start_half: int = 1
) -> tuple[int, float] | None:
    """(video_ms, anchor_gap_s) for a match second, or None when it cannot be placed.
    anchor_gap_s is the clock distance to the reading the time was counted from."""
    half = 1 if match_s <= HALF_S else 2
    pts = [a for a in anchors(clock_samples, start_half) if _in_half(a.match_s, half)]
    if not pts:
        return None
    below = [a for a in pts if a.match_s <= match_s]
    above = [a for a in pts if a.match_s >= match_s]
    lo = hi = None
    if below:
        m = max(a.match_s for a in below)
        ties = [a.video_ms for a in below if a.match_s == m]
        # exact hit: the clock reached this value at its first reading (it may then stand still);
        # otherwise count on from the last reading before the clock moved on
        lo = Anchor(min(ties) if m == match_s else max(ties), m)
    if above:
        m = min(a.match_s for a in above)
        hi = Anchor(min(a.video_ms for a in above if a.match_s == m), m)
    if lo is not None and hi is not None:
        d_lo, d_hi = match_s - lo.match_s, hi.match_s - match_s
        if d_lo <= d_hi:
            v = lo.video_ms + d_lo * 1000
            gap = d_lo
        else:
            v = hi.video_ms - d_hi * 1000
            gap = d_hi
        # a stopped clock only ever makes the moment later than counted from below and earlier
        # than counted back from above: stay inside the bracket
        return round(min(max(v, lo.video_ms), hi.video_ms)), gap
    if lo is not None:
        d = match_s - lo.match_s
        return (round(lo.video_ms + d * 1000), d) if d <= MAX_EXTRAPOLATE_S else None
    assert hi is not None
    d = hi.match_s - match_s
    if d > MAX_EXTRAPOLATE_S:
        return None
    return round(hi.video_ms - d * 1000), d


def match_to_video(
    clock_samples: Iterable[tuple[int, float]], match_s: float, start_half: int = 1
) -> int | None:
    """Video millisecond at which the match clock showed `match_s` (absolute, 0..3600), or None.

    `clock_samples` are (video_ms, clock_s) readings of the clock as shown (second half 30-60 or
    restarting at 0, see `anchors`). The nearest readings on either side within the same half are
    used, counting at 1 s/s from the nearer one; outside the read range at most 60 s are
    extrapolated."""
    found = locate(clock_samples, match_s, start_half)
    return found[0] if found else None


def samples_from_overlay(
    segments: Sequence[dict[str, Any]], step_ms: int = 5000
) -> list[tuple[int, float]]:
    """Clock segments of `scoreboard.read_overlay_summary` (a stored analysis result) as readings.
    A segment is a run checked by its reads (clock - video time constant), so points every
    `step_ms` inside it are as good as readings."""
    out: list[tuple[int, float]] = []
    for s in segments:
        start, end, c = int(s["start_ms"]), int(s["end_ms"]), float(s["start_clock_s"])
        out.extend((t, c + (t - start) / 1000) for t in range(start, end, step_ms))
        out.append((end, c + (end - start) / 1000))
    return out


# --- official logs in one shape -------------------------------------------------------------


def _score(result: Any) -> list[int] | None:
    if isinstance(result, list) and len(result) == 2:
        return [int(result[0]), int(result[1])]
    if isinstance(result, str) and ":" in result:
        h, a = result.split(":", 1)
        if h.strip().isdigit() and a.strip().isdigit():
            return [int(h), int(a)]
    return None


def _num(text: Any) -> int | None:
    if isinstance(text, int):
        return text
    return int(text) if isinstance(text, str) and text.strip().isdigit() else None


def _handball_ch(data: dict[str, Any]) -> list[dict[str, Any]]:
    keepers = {
        ("home" if p.get("isHome") else "away", p.get("dressNr"))
        for p in data.get("players", [])
        if p.get("function") == "goalkeeper"
    }
    out = []
    for e in data["log"]:
        people = {
            side: {
                "number": _num(e.get(f"{side}TeamPlayerStaffNrDesc")),
                "name": e.get(f"{side}TeamPlayerStaffName") or None,
            }
            for side in ("home", "away")
        }
        sides = [s for s in ("home", "away") if people[s]["name"]]
        kind = KINDS.get(e["actionText"], "other")
        team, goalkeeper = (sides[0] if len(sides) == 1 else None), None
        if len(sides) == 2:  # a save names shooter and goalkeeper
            gk = [s for s in sides if (s, people[s]["number"]) in keepers]
            if len(gk) == 1:
                team = "away" if gk[0] == "home" else "home"
                goalkeeper = people[gk[0]]
        player = people[team] if team else {"number": None, "name": None}
        row: dict[str, Any] = {
            "match_s": e["timeInt"],
            "time": e.get("timeString"),
            "action": e["actionText"],
            "kind": kind,
            "team": team,
            "number": player["number"],
            "name": player["name"],
            "score": _score(e.get("result")),
        }
        if goalkeeper:
            row["goalkeeper"] = goalkeeper
        out.append(row)
    return out


def _dhb(data: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "match_s": e["timeInt"],
            "time": e.get("timeString"),
            "action": e["actionText"],
            "kind": KINDS.get(e["actionText"], "other"),
            "team": e.get("team"),
            "number": _num(e.get("number")),
            "name": e.get("name"),
            "score": _score(e.get("result")),
        }
        for e in data["log"]
    ]


def _with_video(data: dict[str, Any], offset_s: float, duration_ms: int) -> list[dict[str, Any]]:
    """Files whose entries carry video seconds of the full video already (Mülheim)."""

    def at(video_s: float) -> int | None:
        ms = round((video_s - offset_s) * 1000)
        return ms if 0 <= ms <= duration_ms else None

    out: list[dict[str, Any]] = []
    for g in data.get("goals", []):
        out.append(
            {
                "match_s": None,
                "match_minute": g.get("match_minute"),
                "action": "7m Tor" if g.get("penalty") else "Tor",
                "kind": "penalty_goal" if g.get("penalty") else "goal",
                "team": g.get("team"),
                "number": None,
                "name": g.get("player"),
                "score": _score(g.get("score")),
                "video_ms": at(g["video_s"]),
                "anchor_gap_s": 0.0,
            }
        )
    for e in data.get("missed_7m", []):
        out.append(
            {
                "match_s": None,
                "action": e.get("text"),
                "kind": "penalty_missed",
                "team": None,
                "number": None,
                "name": None,
                "score": None,
                "video_ms": at(e["video_s"]),
                "anchor_gap_s": 0.0,
            }
        )
    for e in data.get("disallowed", []):
        out.append(
            {
                "match_s": None,
                "action": "disallowed",
                "kind": "goal_disallowed",
                "team": None,
                "number": None,
                "name": e.get("player"),
                "score": _score(str(e.get("score", "")).replace("-", ":")),
                "video_ms": at(e["video_s"]),
                "anchor_gap_s": 0.0,
            }
        )
    for e in data.get("halves", []):
        out.append(
            {
                "match_s": None,
                "action": e.get("text"),
                "kind": "half_boundary",
                "team": None,
                "number": None,
                "name": None,
                "score": None,
                "video_ms": at(e["video_s"]),
                "anchor_gap_s": 0.0,
            }
        )
    return sorted(out, key=lambda r: (r["video_ms"] is None, r["video_ms"] or 0))


def official_entries(data: dict[str, Any]) -> list[dict[str, Any]]:
    """The log of a handball.ch or DHB file in one shape (no video time yet)."""
    log = data.get("log") or []
    if log and "actionGroup" in log[0]:
        return _handball_ch(data)
    return _dhb(data)


# --- reading the clock from a video ---------------------------------------------------------


def _video_info(video: Path) -> tuple[float, int]:
    from handball_vision.pipeline import _open

    container, _, fps, total = _open(video)
    container.close()
    return fps, round(total * 1000 / fps) if fps else 0


def read_clock(video: Path, models: Path) -> tuple[str, list[tuple[int, float]], dict[str, Any]]:
    """(source, readings, summary): the overlay clock if the video has one, else the hall board."""
    from handball_vision import scoreboard
    from handball_vision.pipeline import _open, sample_frames

    fps, duration_ms = _video_info(video)
    spread = sample_frames(video, 36)
    reader: Any = None
    if scoreboard.available() and spread:
        boxes = scoreboard.find_overlay(spread)
        if boxes:
            h, w = spread[0].shape[:2]
            x, y, bw, bh = scoreboard._union(boxes, 6, (w, h))
            n = len(spread)
            crops = [
                (duration_ms / 1000 * (k + 0.5) / n, spread[k][y : y + bh, x : x + bw])
                for k in range(0, n, max(1, n // 8))
            ]
            fields = scoreboard.find_fields(crops, (x, y))
            if any(f.kind == "clock" for f in fields):
                reader = scoreboard.Reader(fields, fps, clock_every_s=5)
    source = "score_overlay"
    if reader is None:
        from handball_vision.hallboard import HallBoardReader
        from handball_vision.numbers import NumberReader

        ocr = NumberReader(
            models / "ch_PP-OCRv4_det_infer.onnx", models / "ch_PP-OCRv4_rec_infer.onnx"
        )
        reader = HallBoardReader(ocr, fps, every_s=2.0)
        source = "hall_scoreboard"
    step = max(1, round(fps * (reader.look_every_s if source == "score_overlay" else 2.0)))
    container, stream, _, _ = _open(video)
    try:
        for i, frame in enumerate(container.decode(stream)):
            if i % step == 0:
                reader.add(i, frame.to_ndarray(format="bgr24"))
    finally:
        container.close()
    if source == "score_overlay":
        # the raw clock reads (every 5 s), not the segments: a stopped clock read once is kept
        summary = scoreboard.read_overlay_summary(reader)
        return source, [(int(t), float(c)) for t, c in reader.clocks], summary
    summary = reader.summary()
    return source, [(int(t), float(c)) for t, c in summary["board_clock"]], summary


def align(
    entries: list[dict[str, Any]],
    samples: Sequence[tuple[int, float]],
    duration_ms: int,
    start_half: int = 1,
) -> list[dict[str, Any]]:
    out = []
    for e in entries:
        found = locate(samples, e["match_s"], start_half) if e["match_s"] is not None else None
        inside = found is not None and 0 <= found[0] <= duration_ms
        out.append(
            {
                **e,
                "video_ms": found[0] if found and inside else None,
                "anchor_gap_s": found[1] if found and inside else None,
            }
        )
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("video", type=Path)
    ap.add_argument("official", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--start-half", type=int, default=1, choices=(1, 2))
    ap.add_argument(
        "--video-offset-s",
        type=float,
        default=0.0,
        help="start of VIDEO within the full video (files with video timestamps)",
    )
    ap.add_argument("--models", type=Path, default=Path("data/models"))
    args = ap.parse_args()

    data = json.loads(args.official.read_text(encoding="utf-8"))
    _, duration_ms = _video_info(args.video)
    result: dict[str, Any] = {"video": str(args.video), "official": str(args.official)}
    if "goals" in data and "log" not in data:
        result |= {"clock_source": "official_video_timestamps", "clock_samples": []}
        result["entries"] = _with_video(data, args.video_offset_s, duration_ms)
    else:
        source, samples, summary = read_clock(args.video, args.models)
        result |= {
            "clock_source": source,
            "clock_samples": [list(s) for s in samples],
            "reader_goals": summary.get("goals", []),
        }
        result["entries"] = align(official_entries(data), samples, duration_ms, args.start_half)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    placed = [e for e in result["entries"] if e["video_ms"] is not None]
    print(f"{result['clock_source']}: {len(placed)}/{len(result['entries'])} entries in the video")
    for e in placed:
        if e["kind"] in ("goal", "penalty_goal"):
            ms = e["video_ms"]
            print(
                f"  {e.get('time') or '':>5}  {e['kind']:<12} {e['score']}  video "
                f"{ms // 60000}:{ms // 1000 % 60:02d}.{ms % 1000 // 100}"
            )


if __name__ == "__main__":
    main()
