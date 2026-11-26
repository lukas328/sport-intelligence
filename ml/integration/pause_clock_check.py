"""Pausen: Vorbedingung der Regel `goalcandidates.clock_breaks` auf Dev (2026-11-26).

The rule calls a gap of at least 2 min between two runs of the match clock "no play". It works
only if the product's hall-scoreboard reader finds no running clock in the half-time break and
does find one in the halves around it. A countdown on the board in the break would count as a
running clock (`scoreboard.play_intervals` accepts both directions). This runs the product reader
(`hallboard.HallBoardReader`, PP-OCRv4 as in the image, the image's default spacing) on the 11
dev break segments and the segments before and after them (one game each), and reports per
segment the readings and the share of the segment in a clock run.

  uv run --project packages/vision python ml/integration/pause_clock_check.py VIDEOS OCR_DIR --out R.json

VIDEOS: the segment files; OCR_DIR: ch_PP-OCRv4_det_infer.onnx and ch_PP-OCRv4_rec_infer.onnx.
Segments and their kind from ml/integration/results/pause_dev.json (truth from segment_labels).
The end test is never read.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import cv2

from handball_vision import scoreboard
from handball_vision.hallboard import HallBoardReader
from handball_vision.numbers import NumberReader

ROOT = Path(__file__).resolve().parents[2]
PAUSE = ROOT / "ml/integration/results/pause_dev.json"


def read_segment(video: Path, ocr: NumberReader) -> dict[str, Any]:
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS)
    board = HallBoardReader(ocr, fps, every_s=1.0, full_every_s=4.0, probe_every_s=0.25)
    i = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        board.add(i, frame)
        i += 1
    cap.release()
    dur_ms = round(1000 * i / fps)
    clocks = [(r.t_ms, r.clock_s) for r in board.readings if r.clock_s is not None]
    runs = scoreboard.play_intervals(clocks, end_ms=dur_ms) if clocks else []
    run_ms = sum(b - a for a, b in runs)
    return {
        "readings": len(clocks),
        "runs": [list(r) for r in runs],
        "run_share": round(run_ms / dur_ms, 3) if dur_ms else None,
        "clock_values": sorted({c for _, c in clocks})[:3] + sorted({c for _, c in clocks})[-3:],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("videos", type=Path)
    ap.add_argument("ocr", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    ocr = NumberReader(a.ocr / "ch_PP-OCRv4_det_infer.onnx", a.ocr / "ch_PP-OCRv4_rec_infer.onnx")
    rows = {r["seg"]: r for r in json.loads(PAUSE.read_text())["rows"]}
    out = []
    for seg in sorted(s for s, r in rows.items() if r["kind"] == "break"):
        game, k = seg.rsplit("_s", 1)
        for j in (int(k) - 1, int(k), int(k) + 1):
            name = f"{game}_s{j}"
            video = a.videos / f"{name}.mp4"
            if not video.exists():
                continue
            r = read_segment(video, ocr)
            kind = rows[name]["kind"] if name in rows else "?"
            out.append(
                {"seg": name, "kind": kind, "truth_play": rows.get(name, {}).get("play"), **r}
            )
            print(name, kind, r["readings"], r["run_share"], r["clock_values"], flush=True)
    summary: dict[str, Any] = {}
    for kind in sorted({x["kind"] for x in out}):
        xs = [x for x in out if x["kind"] == kind]
        summary[kind] = {
            "segments": len(xs),
            "with_readings": sum(x["readings"] > 0 for x in xs),
            "with_run": sum(bool(x["runs"]) for x in xs),
            "run_share_mean": round(sum(x["run_share"] or 0 for x in xs) / len(xs), 3),
        }
    a.out.write_text(json.dumps({"summary": summary, "rows": out}, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
