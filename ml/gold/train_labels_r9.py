"""Labels for ball round 9 in the format of ml/ball/kaggle/train_r8_push.py (HUMAN_LABELS_JSON).

- the owner's 1000 "Ball oder nicht?" peaks of round 8 (state ball / none), unchanged;
- Claude's training clip labels (export_train.py: tiers sure, track, confirmed) as "ball";
- per labelled frame up to NEG of the ball net's peaks (score >= MIN_SCORE, at least FAR px from
  the labelled ball) as "none": the net's own confident mistakes in frames where the ball is
  known, the hard negatives round 8 showed it can learn.
Frame numbers are segment frames (seg_frame0 of the prelabel kernel plus the clip frame), points in
the 1280 px wide picture the training kernel resizes to.

    python ml/gold/train_labels_r9.py R8_LABELS_JSON TRAIN_BALL_JSON PRE_JSON OUT_JSON [--neg 1]
"""

import argparse
import json
import math
from pathlib import Path

FAR = 40.0
MIN_SCORE = 0.3


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("r8", type=Path)
    ap.add_argument("train", type=Path)
    ap.add_argument("pre", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--neg", type=int, default=1)
    a = ap.parse_args()
    out = [x for x in json.loads(a.r8.read_text()) if x["state"] in ("ball", "none")]
    pre = json.loads(a.pre.read_text())["clips"]
    train = json.loads(a.train.read_text())["clips"]
    nb = nn = 0
    for cid, c in sorted(train.items()):
        p = pre[cid]
        s = 1280 / p["w"]
        video = f"{p['dataset']}/{p['file']}"
        for lab in c["labels"]:
            f = lab["frame"]
            seg_f = p["seg_frame0"] + f
            x, y = lab["x"] * s, lab["y"] * s
            base = {"game": p["game"], "video": video, "frame": seg_f, "gap": p["gap"]}
            out.append(base | {"id": f"{cid}_{f}", "x": round(x, 1), "y": round(y, 1),
                               "state": "ball", "src": "llm"})
            nb += 1
            if f >= len(p["pre"]):
                continue
            far = [
                q
                for q in p["pre"][f]["net"]
                if q[2] >= MIN_SCORE and math.hypot(q[0] * s - x, q[1] * s - y) >= FAR
            ]
            for i, q in enumerate(sorted(far, key=lambda q: -q[2])[: a.neg]):
                out.append(base | {"id": f"{cid}_{f}_n{i}", "x": round(q[0] * s, 1),
                                   "y": round(q[1] * s, 1), "state": "none", "src": "llm-neg"})
                nn += 1
    a.out.write_text(json.dumps(out))
    print(len(out), "labels:", nb, "new balls,", nn, "new negatives")


if __name__ == "__main__":
    main()
