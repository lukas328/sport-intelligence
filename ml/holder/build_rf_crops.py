"""Extra training crops from the Roboflow handball sets with ball boxes (CC BY 4.0, downloaded for the
ball detector, see ml/ball/README.md). Still frames from many halls and broadcasts: no neighbour
frames, so the crop is stored once (the trainer repeats it for t-G and t+G, "static").

Most exports are squashed to a square; those are stretched back to 16:9, then everything is scaled
to 1280 wide. People: YOLOX-m (cached), holder() on the ball box centre, same crop as
build_crops.py. Images whose ball lies in no box give negatives only; images without a ball label
are skipped (the ball may just be unlabelled).

usage: build_rf_crops.py <scratch>/rf <out dir> [max images per set]
"""

from pathlib import Path as _P

ROOT = _P(__file__).resolve().parents[2]
import glob
import json
import os
import sys

import cv2

sys.path.insert(0, str(ROOT / "packages/vision"))
from handball_vision.ballpossession import holder
from handball_vision.detection import YoloxDetector

RF, OUT = _P(sys.argv[1]), _P(sys.argv[2])
CAP = int(sys.argv[3]) if len(sys.argv) > 3 else 10**9
SETS = ["ballon", "collado", "custom", "gergely", "h5", "xutbx", "spin"]  # ball is class 0 in all
CW, CH, MIN_H = 128, 256, 24
(OUT / "crops").mkdir(parents=True, exist_ok=True)
cache_f = OUT / "boxes.json"
cache = json.load(open(cache_f)) if cache_f.exists() else {}
det = YoloxDetector(_P(str(ROOT / "data/models/yolox_m.onnx")), threads=3)
meta, frames_meta = [], []
for s in SETS:
    files = sorted(glob.glob(str(RF / s / "*/images/*.jpg")))[:CAP]
    for n, f in enumerate(files):
        lab = f.replace("/images/", "/labels/").rsplit(".", 1)[0] + ".txt"
        if not os.path.exists(lab):
            continue
        balls = [list(map(float, ln.split()[1:3])) for ln in open(lab) if ln.split() and ln.split()[0] == "0"]
        if len(balls) != 1:  # none or ambiguous
            continue
        img = cv2.imread(f)
        if img is None:
            continue
        h, w = img.shape[:2]
        W = 1280
        H = round(W * 9 / 16) if w == h else round(h * W / w)
        img = cv2.resize(img, (W, H), interpolation=cv2.INTER_LINEAR)
        bx, by = balls[0][0] * W, balls[0][1] * H
        fid = f"rf_{s}_{os.path.basename(f)[:40]}_{n}"
        if fid not in cache:
            cache[fid] = [[round(d.x1, 1), round(d.y1, 1), round(d.x2, 1), round(d.y2, 1), round(d.score, 3)] for d in det.detect([img])[0] if d.cls == "person"]
        bs = cache[fid]
        hd = holder((bx, by), [(i, *b[:4]) for i, b in enumerate(bs)])
        if hd is not None and bs[hd][3] - bs[hd][1] < MIN_H:
            continue
        k = 0
        for i, (x1, y1, x2, y2, sc) in enumerate(bs):
            bw, bh = x2 - x1, y2 - y1
            if bh < MIN_H:
                continue
            X1, X2 = int(max(0, x1 - 0.25 * bw)), int(min(W, x2 + 0.25 * bw))
            Y1, Y2 = int(max(0, y1 - 0.25 * bh)), int(min(H, y2 + 0.05 * bh))
            if hd is not None and i != hd:
                a, b = bs[i], bs[hd]
                ix = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
                if ix / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - ix) > 0.6:
                    continue
            fn = f"{fid}_{i}.jpg"
            cv2.imwrite(str(OUT / "crops" / fn), cv2.resize(img[Y1:Y2, X1:X2], (CW, CH), interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 90])
            meta.append({"file": fn, "y": int(i == hd), "frame": fid, "box": [x1, y1, x2, y2], "score": sc, "box_h": round(bh, 1),
                         "ball": [round(bx, 1), round(by, 1)], "rect": [X1, Y1, X2, Y2], "src": "roboflow", "scene": s, "hall": "rf_" + s, "split": "train", "kind": "static"})
            k += 1
        frames_meta.append({"frame": fid, "holder": hd is not None, "players": k, "src": "roboflow", "hall": "rf_" + s})
        if n % 200 == 0:
            print(s, n, len(files), len(meta), flush=True)
            json.dump(cache, open(cache_f, "w"))
json.dump(cache, open(cache_f, "w"))
json.dump(meta, open(OUT / "meta.json", "w"))
json.dump(frames_meta, open(OUT / "frames.json", "w"))
from collections import Counter

print(Counter((m["hall"], m["y"]) for m in meta))
print(Counter((m["hall"], m["holder"]) for m in frames_meta))
