"""The product's ball chain today, measured on gold v1 (docs/plans/produkt-analyse-integration.md
step 1): YOLOX-S COCO "sports ball" in `handball_vision.observe.observe`, then the path exactly as
`handball_vision.ballpossession.from_observations` builds it (canvas peaks, `balltrack.track` with
the same parameters), mapped back to frame pixels on every frame of the path.

Clips: the gold prelabel kernel's output `clips/<id>.mp4` (frame k of the mp4 = gold frame k,
1280 px wide like the product proxy). No clock gating (8 s clips; the product would only drop
more). Reported like ml/gold/eval_ball.py (12 px, all / free / held / fast, 95 % clip bootstrap),
plus the detector alone: share of gold points on observed frames with a YOLOX ball box centre
within the radius (any score above the detector threshold 0.15).

    uv run python ml/gold/eval_product_ball.py CLIP_DIR --model yolox_s.onnx [--every 3 1]
"""

import argparse
import json
import math
import random
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from eval_ball import gold_points  # noqa: E402


def _apply(h, x, y):
    v = h @ np.array([x, y, 1.0])
    return float(v[0] / v[2]), float(v[1] / v[2])


def product_path(obs, min_score=0.35):
    """Copy of the path part of ballpossession.from_observations (without clock gating)."""
    from handball_vision import balltrack

    motion = obs.motion
    fw = motion.frame_size[0]
    peaks = []
    for fo in obs.frames:
        h = motion.frame_to_canvas(fo.index)
        if h is None:
            continue
        for d in fo.balls:
            x, y = _apply(h, (d.x1 + d.x2) / 2, (d.y1 + d.y2) / 2)
            peaks.append(balltrack.Peak(fo.index, x, y, float(d.score)))
    if not peaks:
        return {}
    step = obs.frames[1].index - obs.frames[0].index if len(obs.frames) > 1 else 1
    path, _ = balltrack.track(
        peaks, obs.fps, max_speed=0.9 * fw, radius=fw / 160, min_score=min_score, max_gap=3 * step
    )
    out = {}
    for p in path:
        h = motion.canvas_to_frame(p.frame)
        if h is not None:
            out[p.frame] = _apply(h, p.x, p.y)
    return out


def score_clip(gold_clip, path, balls, radius):
    """Per gold point: (subsets, tracker hit, detector hit or None when the frame was not observed)."""
    rows = []
    for p in gold_points(gold_clip):
        q = path.get(p["frame"])
        hit = q is not None and math.hypot(q[0] - p["x"], q[1] - p["y"]) <= radius
        det = None
        if p["frame"] in balls:
            det = any(math.hypot(x - p["x"], y - p["y"]) <= radius for x, y in balls[p["frame"]])
        keys = ("all", p["state"]) + (("fast",) if p["fast"] else ())
        rows.append((keys, hit, det, q is not None))
    return rows


def summarise(per_clip, boot=2000, seed=0):
    def rate(clips, idx, key):
        n = k = 0
        for c in clips:
            for keys, *vals in per_clip[c]:
                v = vals[idx]
                if key in keys and v is not None:
                    n += 1
                    k += bool(v)
        return k / n if n else float("nan"), n

    ids = sorted(per_clip)
    rnd = random.Random(seed)
    res = {}
    for name, idx in (("tracker", 0), ("detector", 1), ("given", 2)):
        for key in ("all", "free", "held", "fast"):
            r, n = rate(ids, idx, key)
            bs = sorted(rate([rnd.choice(ids) for _ in ids], idx, key)[0] for _ in range(boot))
            bs = [b for b in bs if b == b]
            lo, hi = bs[int(0.025 * len(bs))], bs[int(0.975 * len(bs)) - 1]
            res[f"{name}_{key}"] = {"rate": r, "n": n, "ci95": [lo, hi]}
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clips", type=Path)
    ap.add_argument("--model", type=Path, required=True)
    ap.add_argument("--gold", type=Path, default=HERE / "data" / "gold_ball_v1.json")
    ap.add_argument("--every", type=int, nargs="+", default=[3, 1])
    ap.add_argument("--radius", type=float, default=12.0)
    ap.add_argument("--threads", type=int, default=0)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()

    from handball_vision.detection import YoloxDetector
    from handball_vision.observe import observe

    gold = json.load(open(a.gold))["clips"]
    det = YoloxDetector(a.model, threads=a.threads or None)
    report = {}
    for every in a.every:
        per_clip, timings, frames = {}, {}, 0
        t0 = time.perf_counter()
        for cid in sorted(gold):
            video = a.clips / f"{cid}.mp4"
            if not video.exists():
                print("missing", cid, flush=True)
                continue
            obs = observe(video, det, detect_every=every)
            for k, v in obs.timings_s.items():
                timings[k] = timings.get(k, 0.0) + v
            frames += obs.total
            balls = {
                fo.index: [((d.x1 + d.x2) / 2, (d.y1 + d.y2) / 2) for d in fo.balls]
                for fo in obs.frames
            }
            per_clip[cid] = score_clip(gold[cid], product_path(obs), balls, a.radius)
            print(every, cid, sum(r[1] for r in per_clip[cid]), "/", len(per_clip[cid]), flush=True)
        res = summarise(per_clip)
        res["frames"] = frames
        res["wall_s"] = round(time.perf_counter() - t0, 1)
        res["timings_s"] = {k: round(v, 1) for k, v in timings.items()}
        res["ms_per_frame"] = {k: round(1000 * v / max(1, frames), 1) for k, v in timings.items()}
        report[f"detect_every_{every}"] = res
        print(f"detect_every={every}")
        for k, v in res.items():
            if isinstance(v, dict) and "rate" in v:
                print(
                    f"  {k:16} {100 * v['rate']:5.1f} % [{100 * v['ci95'][0]:.1f}, "
                    f"{100 * v['ci95'][1]:.1f}]  n={v['n']}"
                )
        print("  ms/frame", res["ms_per_frame"], "wall", res["wall_s"], flush=True)
        if a.out:
            a.out.write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
