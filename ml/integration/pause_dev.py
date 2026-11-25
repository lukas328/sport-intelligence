"""Pausen-Messung, Variante 2 (2026-11-25): how much of each dev segment the product calls
"no play" against the match clock of the 13 dev games.

Usage:
  uv run --project packages/vision python ml/integration/pause_dev.py OBS_DIR [OBS_DIR ...] --out R.json

OBS_DIR: folders with one sub-folder per segment (motion.npz, observations.npz), from the Kaggle
kernels handball-shot-dev-0..4 and the observe queue (handball-obs-qNNN). Truth per segment from
ml/data/segment_labels (the clock read in the video, mapped to the official log):
- a segment inside a half with a clock: playing share = clock seconds / video seconds
  (match_s range over the segment, edges of a few seconds ignored);
- a segment wholly before kick-off, in the half-time break or after the final whistle: 0;
- everything else (clock not read, straddles a boundary, half unknown): excluded.
Half boundaries in video time come from the log entries (video_ms and match_s): kick-off of a
half = the earliest entry's video time minus its match time in that half; its end = the latest
entry's video time plus the remaining match time (a lower bound when the clock stopped later).

The end test games are never read (they are not in segment_labels).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

from handball_vision import goalcandidates as gc
from handball_vision import observe as ob
from handball_vision.motion import CameraMotion

ROOT = Path(__file__).resolve().parents[2]
LABELS = ROOT / "ml/data/segment_labels"
HALF_S = 1800.0
SEG_S = 180.0
EDGE_S = 4.0


def halves(d: dict[str, Any]) -> dict[int, tuple[float, float]]:
    """Video seconds (start, end) of each half with log entries."""
    out = {}
    for h in (1, 2):
        es = [
            e
            for e in d["entries"]
            if e.get("video_ms") is not None
            and (e["match_s"] < HALF_S if h == 1 else e["match_s"] >= HALF_S)
        ]
        if not es:
            continue
        base = 0.0 if h == 1 else HALF_S
        start = min(e["video_ms"] / 1000 - (e["match_s"] - base) for e in es)
        end = max(e["video_ms"] / 1000 + (base + HALF_S - e["match_s"]) for e in es)
        out[h] = (start, end)
    return out


def truth(d: dict[str, Any]) -> dict[str, dict[str, Any]]:
    hv = halves(d)
    out = {}
    for s in d["segments"]:
        stem = s["file"][:-4]
        a, b = s["start_s"], s["start_s"] + SEG_S
        if s.get("clock_source") and s.get("match_s"):
            m0, m1 = s["match_s"]
            out[stem] = {"kind": "play", "play": min(1.0, (m1 - m0) / (SEG_S - EDGE_S))}
            continue
        if len(hv) < 2:
            continue
        (s1, e1), (s2, e2) = hv[1], hv[2]
        if b <= s1 - 5 or (a >= e1 + 60 and b <= s2 - 5) or a >= e2 + 60:
            label = "before" if b <= s1 else ("break" if b <= s2 else "after")
            out[stem] = {"kind": label, "play": 0.0}
    return out


def product_play(seg_dir: Path) -> float | None:
    obs = ob.load_observations(
        seg_dir / "observations.npz", CameraMotion.load(seg_dir / "motion.npz")
    )
    res = gc.from_observations(obs)
    if res is None:
        return None
    return res["play_s"] / res["duration_s"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("obs", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    dirs = {p.name: p for o in a.obs for p in o.iterdir() if (p / "observations.npz").exists()}
    rows = []
    for f in sorted(LABELS.glob("*.json")):
        d = json.loads(f.read_text())
        for stem, t in truth(d).items():
            if stem not in dirs:
                continue
            p = product_play(dirs[stem])
            rows.append({"seg": stem, "game": d["name"], **t, "product": p})
            print(
                stem, t["kind"], round(t["play"], 2), None if p is None else round(p, 2), flush=True
            )
    summary: dict[str, Any] = {}
    for kind in ("play", "before", "break", "after"):
        r = [x for x in rows if x["kind"] == kind]
        if not r:
            continue
        prod = np.array([np.nan if x["product"] is None else x["product"] for x in r])
        tru = np.array([x["play"] for x in r])
        summary[kind] = {
            "segments": len(r),
            "truth_play_mean": round(float(tru.mean()), 3),
            "product_play_mean": round(float(np.nanmean(prod)), 3),
            "product_none": int(np.isnan(prod).sum()),
            "abs_error_median": round(float(np.nanmedian(np.abs(prod - tru))), 3),
        }
    a.out.write_text(json.dumps({"summary": summary, "rows": rows}, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
