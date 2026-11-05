"""Goal-candidate template for the product (`handball_vision.goalcandidates`), learned from the
overlay labels of the cached club segments, plus its leave-one-game-out evaluation.

The product computes its signals from the observation pass only (camera motion and people
detections, no optical flow, no second decoding pass). This script feeds the cached heavy pass of
`seg_extract.py` through the same product code: the camera track is the accumulated phase
correlation shift (canvas = image - shift), the people are the cached YOLOX-m detections at 2 Hz.
So the numbers printed here are those of the shipped code on the 13 labelled games.

Output: `packages/vision/handball_vision/data/goal_template.json` (versioned): the mean goal profile
of the per-window standardised channels (pan, people image velocity, matched people x velocity,
people speed) from 2 s before to 3 s after the point 2 s after each overlay goal, how the channels
are normalised, the lull windows, the candidate selection and the evaluation.

usage: uv run --project packages/vision python ml/goals/goal_template.py \
         <scratch>/goals_raw/cache <scratch>/goals_raw/labels.json [--version 2026-11-05.1] \
         [--out packages/vision/handball_vision/data/goal_template.json] [--check]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages/vision"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from handball_vision import goalcandidates as gc  # noqa: E402

import seg_eval as se  # noqa: E402

CHANNELS = ("pan", "cx_v", "vx", "speed")
SIGN_CHANNELS = ("pan", "cx_v", "vx")
WINDOW_S = (-2.0, 3.0)
SHIFT_S = 2.0  # template centre - overlay goal
LULL = {"busy_s": [-4.0, 4.0], "quiet_s": [8.0, 24.0]}
EDGE_MARGIN_S = 6.0
OUT = ROOT / "packages/vision/handball_vision/data/goal_template.json"


def cache_signals(z: Any) -> dict[str, np.ndarray]:
    """Product signals from a cached segment: canvas = image - accumulated content shift."""
    t = z["t"].astype(float)
    shift = z["pan"].astype(float)  # content shift per decoded frame (1280 px)
    cam = -np.cumsum(shift, axis=0)
    pe = z["people"].astype(float)
    pt = pe[:, 0]
    px = (pe[:, 1] + pe[:, 3]) / 2 + np.interp(pt, t, cam[:, 0])
    py = pe[:, 4] + np.interp(pt, t, cam[:, 1])
    ph = pe[:, 4] - pe[:, 2]
    return gc.signals(t, cam[:, 0], pt, px, py, ph, float(t[-1]))


def profile(sig: dict[str, np.ndarray], goals: list[float]) -> list[np.ndarray]:
    ch = gc.channels(sig, CHANNELS)
    at = np.array([round((g + SHIFT_S) / gc.DT) for g in goals], int)
    at = at[(at >= 0) & (at < len(ch))]
    sign = tuple(CHANNELS.index(c) for c in SIGN_CHANNELS)
    return list(gc.windows(ch, at, WINDOW_S, sign)) if len(at) else []


def template_dict(prof: np.ndarray, version: str, extra: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": "goal_candidates",
        "version": version,
        "dt_s": gc.DT,
        "channels": list(CHANNELS),
        "sign_channels": list(SIGN_CHANNELS),
        "window_s": list(WINDOW_S),
        "centre_after_goal_s": SHIFT_S,
        "normalisation": {
            "channels": "mean / sd over a rolling window, kept at full length at the video ends",
            "window_s": gc.BLOCK_S,
            "scores": "median / IQR over the same window, clipped to -3..10",
        },
        "lull": LULL,
        "score": "rz(template cosine) + rz(lull)",
        "selection": {
            "rates_per_min": list(gc.RATES),
            "default_rate": gc.DEFAULT_RATE,
            "block_s": gc.BLOCK_S,
            "nms_s": gc.NMS_S,
            "edge_s": gc.EDGE_S,
            "clip_s": [-gc.CLIP_BEFORE_S, gc.CLIP_AFTER_S],
            "goal_offset_s": gc.GOAL_OFFSET_S,
        },
        **extra,
        "profile": [[round(float(v), 5) for v in row] for row in prof],
    }


def evaluate(sigs: dict[str, dict], segs: dict, refs: dict, use: list[str], version: str
             ) -> tuple[dict[str, Any], dict[str, list]]:
    """Leave-one-game-out: every game is scored with a template that none of its goals built."""
    games = sorted({segs[k]["lab"]["game"] for k in use})
    ex = {g: [] for g in games}
    for k in use:
        ex[segs[k]["lab"]["game"]] += profile(sigs[k], refs[k])
    cands: dict[str, list] = {}
    series: dict[str, np.ndarray] = {}
    for k in use:
        others = [e for g, v in ex.items() if g != segs[k]["lab"]["game"] for e in v]
        tmpl = gc.Template.from_dict(template_dict(np.mean(others, axis=0), version, {}))
        series[k] = gc.score(sigs[k], tmpl)
        cands[k] = gc.pick(sigs[k]["t"], series[k])
    rows: dict[str, Any] = {}
    test = [k for k in use if segs[k]["lab"]["game"] not in se.DEV_GAMES]
    for name, subset in (("all", use), ("test", test)):
        n_goals = sum(len(refs[k]) for k in subset)
        row: dict[str, Any] = {"goals": n_goals, "segments": len(subset), "games": len(
            {segs[k]["lab"]["game"] for k in subset}),
            "minutes": round(sum(segs[k]["lab"]["duration_s"] for k in subset) / 60, 1)}
        for r in gc.RATES:
            hits, errs = 0, []
            for k in subset:
                h, e = se.match([c.t for c in cands[k] if c.rate <= r], refs[k])
                hits += h
                errs += e
            row[f"recall@{r}"] = round(hits / max(n_goals, 1), 3)
            if r == gc.DEFAULT_RATE and errs:
                row["peak_minus_goal_s"] = {
                    "median": round(float(np.median(errs)), 1),
                    "iqr": round(float(np.percentile(errs, 75) - np.percentile(errs, 25)), 1)}
        sx = {k: series[k] for k in subset}
        segs_t = {k: {"x": {"t": sigs[k]["t"]}} for k in subset}
        row["window_auc"] = round(se.window_auc(sx, segs_t, refs), 3)
        rows[name] = row
    return rows, cands


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cache", type=Path)
    ap.add_argument("labels", type=Path)
    ap.add_argument("--version", default=None, help="template version (default: today + .1)")
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--check", action="store_true",
                    help="only compare the regenerated profile with the stored one")
    a = ap.parse_args()
    labels = json.loads(a.labels.read_text())
    delay, _ = se.log_delay(labels)
    segs, refs = {}, {}
    for stem, lab in sorted(labels.items()):
        f = a.cache / f"{stem}.npz"
        if not f.exists():
            continue
        goals, src = se.reference(lab, delay)
        if src == "none":
            continue
        dur = lab["duration_s"]
        segs[stem] = {"lab": lab}
        refs[stem] = [g for g in goals if EDGE_MARGIN_S <= g <= dur - EDGE_MARGIN_S]
    use = sorted(segs)
    sigs = {k: cache_signals(np.load(a.cache / f"{k}.npz")) for k in use}
    version = a.version or f"{dt.date.today().isoformat()}.1"
    allp = [e for k in use for e in profile(sigs[k], refs[k])]
    prof = np.mean(allp, axis=0)
    if a.check:
        stored = json.loads(a.out.read_text())
        diff = float(np.abs(np.asarray(stored["profile"]) - prof).max())
        print(f"stored {stored['version']}: max profile difference {diff:.2e}")
        sys.exit(0 if diff < 1e-3 else 1)
    rows, _ = evaluate(sigs, segs, refs, use, version)
    for name, row in rows.items():
        print(f"{name}: {row}")
    extra = {
        "created": dt.date.today().isoformat(),
        "trained_on": {
            "games": len({segs[k]["lab"]["game"] for k in use}),
            "segments": len(use),
            "goals": len(allp),
            "labels": "score overlay changes read by PP-OCR (ml/goals/seg_labels.py), goals more "
            f"than {EDGE_MARGIN_S:g} s from a segment end",
            "footage": "SG Waedenswil/Horgen NLB club streams, panning camera, 1280x720",
            "people": "YOLOX-m at 2 Hz",
            "script": "ml/goals/goal_template.py",
        },
        "evaluation_leave_one_game_out": rows,
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(template_dict(prof, version, extra), indent=1) + "\n")
    print(f"wrote {a.out} ({a.out.stat().st_size} bytes), version {version}, {len(allp)} goals")


if __name__ == "__main__":
    main()
