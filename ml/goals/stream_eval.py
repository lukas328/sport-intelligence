"""Streaming check on continuous footage: the goal-moment score over whole 3-minute segments,
peaks above a threshold as detections, matched against the goals the overlay shows there.

The matched-filter template is rebuilt from the goal clips that do NOT overlap the segments, so
no goal in the segments helped build it. Reference goal times: score-bug digit changes (overlay,
reference only) found over the whole segment.

usage: uv run --project packages/vision python ml/goals/stream_eval.py SEG_CACHE CLIP_CACHE
       GOAL_INDEX.json --starts 855,1709,3988,4843
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cues as cuemod  # noqa: E402
from overlay_ref import REGIONS  # noqa: E402


def overlay_changes(z: np.lib.npyio.NpzFile, fps: float, gap_s: float = 1.5) -> list[float]:
    """Times (s) where a score digit region switches to a new stable state."""
    b = z["bugs"].astype(np.int32)
    m = (b[..., 2] > 140) & (b[..., 1] > 110) & (b[..., 0] < 110)
    ts = z["thumb_idx"] / fps
    lag = round(gap_s * fps / (z["thumb_idx"][1] - z["thumb_idx"][0]))
    out: list[float] = []
    for rs, cs in REGIONS:
        r = m[:, rs, cs]
        for i in range(lag, len(r) - lag):
            before = r[i - lag:i].mean(axis=0) > 0.5
            after = r[i:i + lag].mean(axis=0) > 0.5
            if (before != after).mean() * 100 >= 2.5:
                if all(abs(ts[i] - o) > 5 for o in out):
                    out.append(float(ts[i]))
    return sorted(out)


def template_scores(ch: np.ndarray, tmpl: np.ndarray, mu: np.ndarray, sd: np.ndarray,
                    ts: np.ndarray) -> np.ndarray:
    tpv = (tmpl - tmpl.mean()).ravel()
    out = []
    for t in ts:
        w = ((cuemod.profile_at(ch, t) - mu) / sd).ravel()
        w = w - w.mean()
        out.append(float(w @ tpv / (np.linalg.norm(w) * np.linalg.norm(tpv) + 1e-9)))
    return np.array(out)


def peaks(ts: np.ndarray, s: np.ndarray, thr: float, nms_s: float = 8.0) -> list[tuple[float, float]]:
    order = np.argsort(-s)
    out: list[tuple[float, float]] = []
    for i in order:
        if s[i] < thr:
            break
        if all(abs(ts[i] - t) > nms_s for t, _ in out):
            out.append((float(ts[i]), float(s[i])))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("seg_cache", type=Path)
    ap.add_argument("clip_cache", type=Path)
    ap.add_argument("goal_index", type=Path)
    ap.add_argument("--starts", required=True)
    ap.add_argument("--shift", type=float, default=1.0)
    ap.add_argument("--window", default="-1,4", help="detection - overlay change accepted (s)")
    a = ap.parse_args()
    lo, hi = (float(v) for v in a.window.split(","))
    starts = [float(s) for s in a.starts.split(",")]
    segs = sorted(a.seg_cache.glob("*.npz"))
    index = {Path(e["clip"]).stem: e for e in json.loads(a.goal_index.read_text())}
    ref = json.loads((a.clip_cache / "overlay_ref.json").read_text())
    ranges = [(s - 20, s + 200) for s in starts]
    train = [c for c, e in index.items()
             if ref.get(c, {}).get("change_s") is not None
             and not any(r0 <= e["video_ms"] / 1000 <= r1 for r0, r1 in ranges)]
    negs = [f for f in a.clip_cache.glob("neg_*.npz")]
    neg_all = np.concatenate([cuemod.profile_channels(np.load(f)) for f in negs])
    mu, sd = neg_all.mean(axis=0), neg_all.std(axis=0) + 1e-6
    tmpl = np.mean([(cuemod.profile_at(cuemod.profile_channels(np.load(a.clip_cache / f"{c}.npz")),
                                       ref[c]["change_s"] + a.shift) - mu) / sd for c in train], axis=0)
    print(f"template from {len(train)} goal clips outside the segments, {len(negs)} non-goal clips")
    all_scores, truth = [], []
    total_min = 0.0
    for f, start in zip(segs, starts, strict=True):
        z = np.load(f)
        fps = float(z["fps"])
        ch = cuemod.profile_channels(z)
        ts = np.arange(2.0, int(z["n"]) / fps - 3.0, cuemod.STEP_S)
        s = template_scores(ch, tmpl, mu, sd, ts)
        goals = overlay_changes(z, fps)
        logged = [e["video_ms"] / 1000 - start for e in index.values()
                  if 0 <= e["video_ms"] / 1000 - start <= int(z["n"]) / fps]
        print(f"{f.stem}: overlay goals at {[round(g, 1) for g in goals]}, logged {[round(g) for g in logged]}")
        all_scores.append((ts, s))
        truth.append(goals)
        total_min += (ts[-1] - ts[0]) / 60
    n_goals = sum(len(g) for g in truth)
    print(f"{n_goals} goals in {total_min:.1f} min of continuous play")
    print("thr   recall  precision  false/min  time error (det - overlay) median")
    for thr in (0.4, 0.5, 0.6, 0.65, 0.7, 0.75, 0.8):
        tp = fp = 0
        errs = []
        for (ts, s), goals in zip(all_scores, truth, strict=True):
            dets = peaks(ts, s, thr)
            used = set()
            for t, _ in dets:
                hit = [i for i, g in enumerate(goals) if lo <= t - g <= hi and i not in used]
                if hit:
                    used.add(hit[0])
                    tp += 1
                    errs.append(t - goals[hit[0]])
                else:
                    fp += 1
        rec = tp / max(n_goals, 1)
        prec = tp / max(tp + fp, 1)
        print(f"{thr:.2f}  {rec:6.2f}  {prec:9.2f}  {fp / total_min:9.2f}  "
              f"{np.median(errs) if errs else float('nan'):+.2f}")


if __name__ == "__main__":
    main()
