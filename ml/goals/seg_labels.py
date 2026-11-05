"""Goal labels for the cached ingest segments (`seg_extract.py`), from two free sources.

1. Official game log (ml/data/official/<game>.json) mapped into the segment through its match clock
   (`segment_clock.game_labels`, the same code as `segment_clock.py --labels`). Ingest names with a
   suffix ("..._2023-09-23.f298", a second copy of the video) use the official log of the base name.
2. Score changes read from the picture during the heavy pass: the score overlay (PP-OCR every
   0.5 s, `scoreboard.goals_from_scores`) or, without an overlay, the hall scoreboard
   (`hallboard.goals_from_board`). These need no clock and no log, so they label every segment that
   shows a score. Reference only: the detector never sees them.

Writes LABELS.json {segment stem: {game, segment, duration_s, clock_source, log_goals [{t, score,
kind, anchor_gap_s}], log_other [{t, kind, team}], overlay_goals [{t, score}], board_goals
[{t, score_side, side, window_s}], first_score}} with t in seconds from the segment start.

usage: uv run --project packages/vision python ml/goals/seg_labels.py CACHE_DIR LABELS.json
       [--workdir <scratch>/ingest]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages/vision"))
sys.path.insert(0, str(ROOT / "ml/data"))
from handball_vision import hallboard, scoreboard  # noqa: E402
from segment_clock import OFFICIAL, SCRATCH, all_games, game_labels, load_json  # noqa: E402

GOAL_KINDS = ("goal", "penalty_goal")


def base_name(name: str) -> str:
    return re.sub(r"\.f\d+$", "", name)


def log_labels(workdir: Path) -> dict[str, dict]:
    """Segment file stem -> {log goals, other log entries, clock source} for every game of the
    ingest state with an official log."""
    out: dict[str, dict] = {}
    for name, game in sorted(all_games(workdir).items()):
        official = load_json(OFFICIAL / f"{base_name(name)}.json", {})
        segs = game.get("segments") or []
        info = {Path(s["file"]).stem: {"game": base_name(name), "clock_source": (s.get("clock") or {}).get("source"),
                                       "log_goals": [], "log_other": [], "has_log": bool(official.get("log"))}
                for s in segs}
        if official.get("log") and any((s.get("clock") or {}).get("source") for s in segs):
            res = game_labels(base_name(name), game, official)
            for e in res["entries"]:
                row = {"t": e["segment_ms"] / 1000, "kind": e["kind"], "team": e.get("team"),
                       "score": e.get("score"), "anchor_gap_s": e.get("anchor_gap_s")}
                key = "log_goals" if e["kind"] in GOAL_KINDS else "log_other"
                info[Path(e["segment"]).stem][key].append(row)
        out.update(info)
    return out


def picture_goals(z: np.lib.npyio.NpzFile) -> tuple[list[dict], list[dict], list[int] | None]:
    reads = [(int(t), (int(a), int(b))) for t, a, b in z["score_reads"]]
    overlay = [{"t": g.t_ms / 1000, "score": list(g.score), "side": g.side}
               for g in scoreboard.goals_from_scores(reads)]
    first = scoreboard.first_score(reads)
    board = []
    if "board_reads" in z and len(z["board_reads"]):
        rd = [hallboard.BoardReading(int(t), None if a < 0 else int(a), None if b < 0 else int(b), 0)
              for t, a, b in z["board_reads"]]
        board = [{"t": g["t_ms"] / 1000, "score_side": g["score_side"], "side": g["side"],
                  "window_s": g["window_ms"] / 1000} for g in hallboard.goals_from_board(rd)]
    return overlay, board, list(first) if first else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cache", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--workdir", type=Path, default=SCRATCH / "ingest")
    a = ap.parse_args()
    logs = log_labels(a.workdir)
    out = {}
    for f in sorted(a.cache.glob("*.npz")):
        z = np.load(f)
        if "t" not in z:
            continue
        overlay, board, first = picture_goals(z)
        info = logs.get(f.stem, {"game": base_name(f.stem.rsplit("_s", 1)[0]), "clock_source": None,
                                 "log_goals": [], "log_other": [], "has_log": False})
        out[f.stem] = {**info, "segment": f.stem, "duration_s": float(z["t"][-1]),
                       "overlay_goals": overlay, "board_goals": board, "first_score": first,
                       "score_reads": int(len(z["score_reads"])),
                       "overlay": bool(len(z["overlay_boxes"]))}
        print(f"{f.stem}: log goals {[round(g['t']) for g in info['log_goals']]}, "
              f"overlay {[(round(g['t']), g['score']) for g in overlay]}, board {[round(g['t']) for g in board]}")
    a.out.write_text(json.dumps(out, indent=1))
    print(f"{len(out)} segments -> {a.out}")


if __name__ == "__main__":
    main()
