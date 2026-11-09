"""Shot-candidate template for the product (`handball_vision.goalcandidates.shot_score`), learned
from the shots of the official game logs on the labelled club segments, plus its
leave-one-game-out evaluation.

Labels: `ml/data/segment_labels/*.json` (`segment_clock.py --labels`): goals, saved and missed
shots with their time in the segment. Signals: the product channels (pan, people image velocity,
matched people x velocity, people speed) from each segment's stored observation pass
(`product_path.py observe`), else from the research cache (`seg_extract.py`), as `shot_eval.py`
loads them. The profile is the mean of the per-window standardised channels from 2 s before to
3 s after the point `SHIFT_S` after each logged shot. The shot score adds it to the goal score
with the weights stored in the asset (`--weights`); `shot_eval.py` compares the variants.

Output: `packages/vision/handball_vision/data/shot_template.json` (versioned).

usage: uv run --project packages/vision python ml/goals/shot_template.py [labels dir] \
         --obs <scratch>/gc_bench/obs <scratch>/gc_bench/obs_l --cache <scratch>/goals_raw/cache \
         --store <scratch>/shots/sig.pkl [--version 2026-11-05.s1] [--check]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages/vision"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import goal_template as gt  # noqa: E402
import seg_eval as se  # noqa: E402
import shot_eval as sh  # noqa: E402

from handball_vision import goalcandidates as gc  # noqa: E402

SHIFT_S = 1.0  # template centre - logged shot
WEIGHTS = {"shot": 1.0, "goal": 1.0, "lull": 1.0}
OUT = ROOT / "packages/vision/handball_vision/data/shot_template.json"


def template_dict(
    prof: np.ndarray, version: str, weights: dict[str, float], offset_s: float, extra: dict
) -> dict[str, Any]:
    goal = json.loads(gc.TEMPLATE_PATH.read_text())
    return {
        "name": "shot_candidates",
        "version": version,
        "dt_s": gc.DT,
        "channels": list(gt.CHANNELS),
        "sign_channels": list(gt.SIGN_CHANNELS),
        "window_s": list(gt.WINDOW_S),
        "centre_after_shot_s": SHIFT_S,
        "normalisation": goal["normalisation"],
        "lull": goal["lull"],
        "weights": weights,
        "score": "shot * rz(shot template cosine) + goal * rz(goal template cosine)"
        " + lull * rz(lull); goal template and lull from goal_template.json",
        "selection": {
            "rates_per_min": list(gc.SHOT_RATES),
            "default_rate": gc.SHOT_DEFAULT_RATE,
            "block_s": gc.BLOCK_S,
            "nms_s": gc.NMS_S,
            "edge_s": gc.EDGE_S,
            "clip_s": [-gc.SHOT_CLIP_BEFORE_S, gc.SHOT_CLIP_AFTER_S],
            "shot_offset_s": offset_s,
        },
        **extra,
        "profile": [[round(float(v), 5) for v in row] for row in prof],
    }


def evaluate(
    data: dict, segs: dict, stems: list[str], weights: dict[str, float]
) -> tuple[dict[str, Any], float]:
    """Leave-one-game-out: the shot template of each game is learned from the other games; the
    candidates are the product's (`gc.pick` with the shot rates on `gc.shot_score`)."""
    sigs = {k: data[k]["p"] for k in stems}
    game = {k: segs[k]["game"] for k in stems}
    dur = {k: float(sigs[k]["t"][-1]) for k in stems}
    shots = {k: [e["t"] for e in segs[k]["entries"] if e["kind"] in sh.SHOT] for k in stems}
    goal_t = gc.load_template()
    cands: dict[str, list[gc.Candidate]] = {}
    for g in sorted(set(game.values())):
        others = {k: v for k, v in sigs.items() if game[k] != g}
        tm = sh.template(sh.shot_profiles(others, shots, SHIFT_S))
        model = gc.ShotModel(tm, weights, 0.0)
        for k in stems:
            if game[k] == g:
                cands[k] = gc.pick(
                    sigs[k]["t"], gc.shot_score(sigs[k], model, goal_t), rates=gc.SHOT_RATES
                )
    out: dict[str, Any] = {
        "segments": len(stems),
        "games": len(set(game.values())),
        "minutes": round(sum(dur.values()) / 60, 1),
    }
    errs_all: list[float] = []
    for cname, kinds in sh.CLASSES.items():
        refs = sh.refs_of(segs, stems, kinds, dur)
        n = sum(len(v) for v in refs.values())
        row: dict[str, Any] = {"n": n}
        for r in gc.SHOT_RATES:
            hits, errs = 0, []
            for k in stems:
                h, e = se.match([c.t for c in cands[k] if c.rate <= r], refs[k])
                hits += h
                errs += e
            row[f"recall@{r}"] = round(hits / max(n, 1), 3)
            if r == gc.SHOT_DEFAULT_RATE and errs:
                row["peak_minus_shot_s"] = {
                    "median": round(float(np.median(errs)), 1),
                    "iqr": round(float(np.subtract(*np.percentile(errs, [75, 25]))), 1),
                }
                if cname == "shots":
                    errs_all = errs
        out[cname] = row
    return out, float(np.median(errs_all)) if errs_all else 1.5


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("labels", type=Path, nargs="?", default=ROOT / "ml/data/segment_labels")
    ap.add_argument("--obs", type=Path, nargs="*", default=[])
    ap.add_argument("--cache", type=Path, nargs="*", default=[])
    ap.add_argument("--store", type=Path)
    ap.add_argument("--version", default=None, help="template version (default: today + .s1)")
    ap.add_argument("--weights", default=json.dumps(WEIGHTS), help="JSON: shot, goal, lull")
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--check", action="store_true", help="compare with the stored profile only")
    a = ap.parse_args()
    weights = {k: float(v) for k, v in json.loads(a.weights).items()}
    segs = sh.load_segments(a.labels)
    data = sh.load_all(segs, a.obs, a.cache, a.store)
    stems = [k for k in segs if data[k]["src"] != "none"]
    shots = {k: [e["t"] for e in segs[k]["entries"] if e["kind"] in sh.SHOT] for k in stems}
    prof = np.mean(sh.shot_profiles({k: data[k]["p"] for k in stems}, shots, SHIFT_S), axis=0)
    if a.check:
        stored = np.asarray(json.loads(a.out.read_text())["profile"])
        diff = float(np.abs(stored - prof).max())
        print(f"max |stored - regenerated| = {diff:.5f}")
        sys.exit(0 if diff < 1e-3 else 1)
    ev, offset = evaluate(data, segs, stems, weights)
    kinds: dict[str, int] = defaultdict(int)
    for k in stems:
        for e in segs[k]["entries"]:
            kinds[e["kind"]] += 1
    version = a.version or f"{dt.date.today().isoformat()}.s1"
    extra = {
        "created": dt.date.today().isoformat(),
        "trained_on": {
            "games": ev["games"],
            "segments": ev["segments"],
            "minutes": ev["minutes"],
            "shots": ev["shots"]["n"],
            "kinds": dict(sorted(kinds.items())),
            "labels": "official game logs (handball.ch) per segment, ml/data/segment_labels",
            "footage": "Swiss club streams (NLB, cup), operated panning camera, 1280x720",
            "signals": "product observation pass where stored, else the research pass",
            "script": "ml/goals/shot_template.py",
        },
        "evaluation_leave_one_game_out": ev,
    }
    out = template_dict(prof, version, weights, round(offset, 1), extra)
    gc.ShotModel.from_dict(out)  # loads
    a.out.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "profile"}, indent=1))


if __name__ == "__main__":
    main()
