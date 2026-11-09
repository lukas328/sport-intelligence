"""Extra training crops from TeamTrack handball_side (MIT; one recreational hall, 3300x450 fisheye
panorama, 30 fps, ground-truth boxes for the 14 players and the ball in every frame).

Every STEP-th frame with a ball box: holder() on the ball centre against the ground-truth player
boxes; the holder positive, the other players negative (referees and bench are not annotated,
so they never appear). Same crop as build_crops.py (25 % sides, 25 % above, 5 % below; frames
t-2, t, t+2), at the native resolution (players are 20 to 90 px tall, so the crops are soft).

usage: build_tt_crops.py <scratch>/tt <out dir> [step=10]
"""

from pathlib import Path as _P

ROOT = _P(__file__).resolve().parents[2]
import csv
import glob
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, str(ROOT / "packages/vision"))
from handball_vision.ballpossession import holder

TT, OUT = _P(sys.argv[1]), _P(sys.argv[2])
STEP = int(sys.argv[3]) if len(sys.argv) > 3 else 10
G, CW, CH, MIN_H = 2, 128, 256, 30
(OUT / "crops").mkdir(parents=True, exist_ok=True)
meta, frames_meta = [], []
for split in ("train", "val"):
    for ann in sorted(glob.glob(str(TT / split / "annotations/*.csv"))):
        vid = str(TT / split / "videos" / (os.path.basename(ann)[:-4] + ".mp4"))
        if not os.path.exists(vid):
            continue
        rows = list(csv.reader(open(ann)))
        team, pid, attr = rows[0][1:], rows[1][1:], rows[2][1:]
        cols = {}
        for j, (t, p, a) in enumerate(zip(team, pid, attr)):
            cols.setdefault(f"{t}_{p}", {})[a] = j + 1
        data = [r for r in rows[3:] if r and r[0].isdigit()]
        cap = cv2.VideoCapture(vid)
        Ww, Hh = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        want = {int(r[0]) - 1 + d for r in data if (int(r[0]) - 1) % STEP == 0 for d in (-G, 0, G)}
        frames, k = {}, 0
        while True:  # keep only the frames needed (a whole clip is ~4 GB)
            ok, f = cap.read()
            if not ok:
                break
            if k in want:
                frames[k] = f
            k += 1
        for r in data:
            fi = int(r[0]) - 1
            if fi % STEP or any(fi + d not in frames for d in (-G, 0, G)):
                continue

            def box(k):
                c = cols[k]
                try:
                    h, x, y, w = (float(r[c[a]]) for a in ("bb_height", "bb_left", "bb_top", "bb_width"))
                except ValueError:
                    return None
                return None if not np.isfinite([h, x, y, w]).all() or w <= 0 else (x, y, x + w, y + h)

            b = box("BALL_BALL")
            if b is None:
                continue
            ball = ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
            players = [(k, bb) for k in cols if k != "BALL_BALL" and (bb := box(k)) is not None]
            hd = holder(ball, [(i, *bb) for i, (_, bb) in enumerate(players)])
            if hd is not None and players[hd][1][3] - players[hd][1][1] < MIN_H:
                continue
            fid = f"tt_{os.path.basename(ann)[:-4]}_{fi}"
            n = 0
            for i, (k, (x1, y1, x2, y2)) in enumerate(players):
                w, hh = x2 - x1, y2 - y1
                if hh < MIN_H:
                    continue
                X1, X2 = int(max(0, x1 - 0.25 * w)), int(min(Ww, x2 + 0.25 * w))
                Y1, Y2 = int(max(0, y1 - 0.25 * hh)), int(min(Hh, y2 + 0.05 * hh))
                if X2 - X1 < 4 or Y2 - Y1 < 8:
                    continue
                crops = [cv2.resize(frames[fi + d][Y1:Y2, X1:X2], (CW, CH), interpolation=cv2.INTER_CUBIC) for d in (-G, 0, G)]
                fn = f"{fid}_{i}.jpg"
                cv2.imwrite(str(OUT / "crops" / fn), cv2.hconcat(crops), [cv2.IMWRITE_JPEG_QUALITY, 88])
                meta.append({"file": fn, "y": int(i == hd), "frame": fid, "box": [x1, y1, x2, y2], "box_h": round(hh, 1),
                             "ball": [round(ball[0], 1), round(ball[1], 1)], "rect": [X1, Y1, X2, Y2],
                             "src": "teamtrack", "scene": os.path.basename(ann)[:-4], "hall": "teamtrack", "split": "train", "kind": "tt"})
                n += 1
            frames_meta.append({"frame": fid, "holder": hd is not None, "players": n, "src": "teamtrack"})
        print(ann, len(meta), flush=True)
json.dump(meta, open(OUT / "meta.json", "w"))
json.dump(frames_meta, open(OUT / "frames.json", "w"))
from collections import Counter

print(Counter(m["y"] for m in meta), Counter(m["holder"] for m in frames_meta))
