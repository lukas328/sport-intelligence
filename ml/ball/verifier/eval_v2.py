"""Verifier v2 on ball test set 2 with the choice frozen on the tuning set (run once; never train on it).

    python ml/ball/verifier/eval_v2.py ITEMS_JSON LABELS_DIR T_DIR PEAKS_CACHE.json CHOICE.json [OUT.json]

PEAKS_CACHE.json: round 7's top-5 peaks per frame (eval.py writes it). CHOICE.json from tune_v2.py
(verifier path, rule, gate threshold). Crops: v2.canon_frames, i.e. the same 96 px / 2x bicubic /
JPEG 85 / area-down path as the human-labelled training crops, centre 64 px. Metrics and table as
eval.py (top 1, top 5, no-ball >= 0.5, found at matched false alarms, paired McNemar vs the net).
"""
import json, math, sys

import cv2, numpy as np, torch

from eval import R_HIT, frames, load, report
from train import Verifier, auc, predict
from tune_v2 import rule_scores
from v2 import canon_frames


def main():
    items_json, labels_dir, tdir, cache, choice = sys.argv[1:6]
    out = sys.argv[6] if len(sys.argv) > 6 else None
    torch.set_num_threads(4)
    items, labels = load(items_json, labels_dir); P = json.load(open(cache)); c = json.load(open(choice))["best"]
    ver = Verifier(); ver.load_state_dict(torch.load(c["path"], map_location="cpu", weights_only=True)); ver.eval()
    rows = []
    for k, l in labels.items():
        bgr = [cv2.cvtColor(f, cv2.COLOR_RGB2BGR) for f in frames(items, tdir, k)]
        pk = P[k]; v = predict(ver, np.stack([canon_frames(bgr, px, py, 64) for px, py, _ in pk]))
        s = np.array([q[2] for q in pk])
        d = np.array([math.hypot(px - l["x"], py - l["y"]) for px, py, _ in pk]) if l["state"] == "ball" else None
        rows.append({"id": k, "state": l["state"], "clock": bool(items[k]["clock_running"]), "s": s.tolist(),
                     "v": v.round(4).tolist(), "d": None if d is None else d.round(1).tolist()})
    if out:
        json.dump(rows, open(out, "w"))
    name = f"{c['model']}/{c['rule']}"[:9]
    scorers = {"net": lambda r: np.array(r["s"]),
               name: lambda r: rule_scores(c["rule"], np.array(r["s"]), np.array(r["v"]), c["t"])}
    print(f"frozen choice: {c['model']} ({c['path']}), rule {c['rule']}" + (f", t = {c['t']:.3f}" if c["t"] is not None else ""))
    report(rows, "test set 2, all frames", scorers)
    report([r for r in rows if r["clock"]], "clock running", scorers)
    report([r for r in rows if not r["clock"]], "clock stopped or unknown", scorers)
    for lo, title in ((0.0, "all top-5 peaks"), (0.4, "confident peaks (>= 0.4, as the tuning set)")):
        hit = [(s, v) for r in rows if r["state"] == "ball" for s, v, d in zip(r["s"], r["v"], r["d"]) if d < R_HIT and s >= lo]
        mis = [(s, v) for r in rows for i, (s, v) in enumerate(zip(r["s"], r["v"]))
               if (r["state"] == "none" or r["d"][i] > 20) and s >= lo]
        H, M = np.array(hit), np.array(mis)
        f = lambda A: rule_scores(c["rule"], A[:, 0], A[:, 1], c["t"])
        print(f"\n{title}: {len(H)} hits, {len(M)} false peaks; AUC net {auc(H[:, 0], M[:, 0]):.3f}, "
              f"verifier {auc(H[:, 1], M[:, 1]):.3f}, chosen rule {auc(f(H), f(M)):.3f}")


if __name__ == "__main__":
    main()
