"""Learned candidate rescoring for the ball tracker (research, ml/).

A logistic regression on per-candidate features, trained on the training clips (labels
ml/gold/data/train_ball_v1.json, candidates of the round-8 net and OWLv2 that never saw those
labels: scratchpad train1/out/pre.json), gives each candidate a ball probability that replaces the
hand-set detector reward of tracker.py when Params.rescore is set.

    python ml/gold/tracker_rescore.py TRAIN_PRE_JSON           # writes ml/gold/data/tracker_rescore.json
    python ml/gold/tracker_rescore.py TRAIN_PRE_JSON --noowl   # writes ml/gold/data/tracker_rescore_noowl.json

--noowl: the shippable variant. The product cannot run OWLv2 (about 1.4 s per frame on a T4), so
the OWLv2 boxes are removed from the training candidates before the features are computed; the
OWLv2 columns are then zero and get weight zero. tracker.py picks these weights automatically for a
clip without any OWLv2 output.
"""

import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
NAMES = ["bias", "net", "top1", "owl", "both", "static", "move", "slow"]


def features(frames, static, scale):
    """frames: per frame a list of candidates with .x .y .net .owl; static: same shape, bools."""
    out = []
    n = len(frames)
    vmin = 3.0 * scale
    for k, cs in enumerate(frames):
        top = max((q.net for q in cs), default=0.0)
        row = []
        for j, q in enumerate(cs):
            move = 0.0
            for d in (1, 2):
                if k - d < 0 or k + d >= n:
                    continue
                for a in frames[k - d]:
                    for b in frames[k + d]:
                        mx, my = (a.x + b.x) / 2, (a.y + b.y) / 2
                        if math.hypot(mx - q.x, my - q.y) <= 6 * scale and math.hypot(b.x - a.x, b.y - a.y) >= 2 * d * vmin:
                            move = max(move, min(1.0, (a.net + a.owl) * (b.net + b.owl)))
            slow = 0
            for d in range(-10, 11):
                if d == 0 or not 0 <= k + d < n:
                    continue
                if any(math.hypot(a.x - q.x, a.y - q.y) <= 2 * scale * abs(d) + 4 for a in frames[k + d]):
                    slow += 1
            row.append([1.0, q.net, float(q.net > 0 and q.net >= top), q.owl, float(q.net > 0 and q.owl > 0),
                        float(static[k][j]), move, slow / 20])
        out.append(row)
    return out


def fit(X, y, l2=1e-3, iters=50):
    w = np.zeros(X.shape[1])
    for _ in range(iters):  # Newton steps
        p = 1 / (1 + np.exp(-X @ w))
        g = X.T @ (p - y) + l2 * w
        H = (X * (p * (1 - p))[:, None]).T @ X + l2 * np.eye(len(w))
        w -= np.linalg.solve(H, g)
    return w


def main() -> None:
    sys.path.insert(0, str(HERE))
    from tracker import Params, candidates

    noowl = "--noowl" in sys.argv
    pre = json.loads(Path(sys.argv[1]).read_text())["clips"]
    if noowl:
        for c in pre.values():
            for r in c["pre"]:
                r.pop("owl", None)
    lab = json.loads((HERE / "data" / "train_ball_v1.json").read_text())["clips"]
    p = Params()
    X, Y = [], []
    for cid, c in pre.items():
        if cid not in lab:
            continue
        frames = candidates(c, p)
        static = [[q.static for q in cs] for cs in frames]
        scale = c["w"] / 1280 * 30 / c.get("fps_read", c.get("fps", 30))
        F = features(frames, static, scale)
        for l in lab[cid]["labels"]:
            if l["x"] is None or l["frame"] >= len(frames):
                continue
            for q, f in zip(frames[l["frame"]], F[l["frame"]]):
                X.append(f)
                Y.append(float(math.hypot(q.x - l["x"], q.y - l["y"]) <= 12))
    X, Y = np.array(X), np.array(Y)
    w = fit(X, Y)
    print(len(Y), "candidates", int(Y.sum()), "on the ball")
    print(dict(zip(NAMES, np.round(w, 3))))
    (HERE / "data" / ("tracker_rescore_noowl.json" if noowl else "tracker_rescore.json")).write_text(json.dumps({"names": NAMES, "w": [round(float(v), 4) for v in w],
                                                                     "n": len(Y), "pos": int(Y.sum())}, indent=1) + "\n")


if __name__ == "__main__":
    main()
