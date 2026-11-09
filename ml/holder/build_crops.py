"""Player crops for the holder classifier ("does this player hold the ball?").

Sources (user labels, 1280-wide frame coordinates):
  * ball paths (labelseq/db/paths/*.json): every keyframe with a clicked ball; for training scenes
    also the two frames between two clicked keyframes when the ball moved little (linear
    interpolation of the click, kind "interp"),
  * single frames (labelpage/db2/labels/*.json, state "ball").
Frames are decoded from the source videos exactly like the labelling tools did (seek to t-G, read
sequentially, resize to 1280 wide). People: YOLOX-m on the centre frame (boxes cached). The player
holder() assigns the ball to is positive, every other player negative; a frame whose ball is in no
box ("free") gives only negatives. Crop = box widened 25 % each side, raised 25 % (arms overhead),
5 % below, cut at the same place in t-G, t, t+G, each resized to 128x256, saved side by side.

Split: whole path scenes are held out (TEST_SCENES, one unseen hall plus one scene of each hall
with two), the single frames follow the shared per-hall split (ball3/user_split.json).

usage: build_crops.py <scratch>/labelseq <scratch>/labelpage <user_split.json> <out dir>
"""

from pathlib import Path as _P

ROOT = _P(__file__).resolve().parents[2]
import glob
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, str(ROOT / "packages/vision"))
from handball_vision.ballpossession import holder
from handball_vision.detection import YoloxDetector

SEQ, PAGE, SPLIT, OUT = (_P(a) for a in sys.argv[1:5])
VID = ROOT / "data/videos"
CW, CH = 128, 256  # stored crop size per frame
MIN_H = 24  # smaller boxes are not cropped (a holder that small drops the frame)
TEST_SCENES = {
    "eisenach_wetzlar_2_3189",  # contains a benchmark test frame
    "ch_spl2_2024_leimental_arbon_843",
    "leimental_frauenfeld_2_1919",
    "muelheim_suedpfalz_1_4347",
    "uznach_dietikon_s3_3574",
    "u20_sui_ger_0_4287",  # hall not in training at all
}
(OUT / "crops").mkdir(parents=True, exist_ok=True)
cache_f = OUT / "boxes.json"
cache = json.load(open(cache_f)) if cache_f.exists() else {}
det = None


def read(rel, first, n):
    """Frames first..first+n-1 the way the labelling tools read them, 1280 wide."""
    cap = cv2.VideoCapture(str(VID / rel))
    cap.set(cv2.CAP_PROP_POS_FRAMES, first)
    out = {}
    for k in range(n):
        ok, f = cap.read()
        if not ok:
            break
        if f.shape[1] != 1280:
            f = cv2.resize(f, (1280, round(f.shape[0] * 1280 / f.shape[1])), interpolation=cv2.INTER_AREA)
        out[first + k] = f
    return out


def boxes_for(key, img):
    global det
    if key not in cache:
        if det is None:
            det = YoloxDetector(_P(str(ROOT / "data/models/yolox_m.onnx")), threads=3)
        ds = [d for d in det.detect([img])[0] if d.cls == "person"]
        cache[key] = [[round(d.x1, 1), round(d.y1, 1), round(d.x2, 1), round(d.y2, 1), round(d.score, 3)] for d in ds]
    return cache[key]


def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    i = ix * iy
    return i / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i + 1e-9)


meta, frames_meta = [], []


def emit(fid, frames, t, G, xy, info):
    bs = boxes_for(fid, frames[t])
    h = holder(xy, [(i, *b[:4]) for i, b in enumerate(bs)])
    if h is not None and bs[h][3] - bs[h][1] < MIN_H:
        return
    H, W = frames[t].shape[:2]
    n = 0
    for i, (x1, y1, x2, y2, sc) in enumerate(bs):
        w, hh = x2 - x1, y2 - y1
        if hh < MIN_H:
            continue
        # a near-duplicate box of the holder is neither positive nor a fair negative
        if h is not None and i != h and iou(bs[i], bs[h]) > 0.6:
            continue
        X1, X2 = int(max(0, x1 - 0.25 * w)), int(min(W, x2 + 0.25 * w))
        Y1, Y2 = int(max(0, y1 - 0.25 * hh)), int(min(H, y2 + 0.05 * hh))
        crops = [cv2.resize(frames[t + d][Y1:Y2, X1:X2], (CW, CH), interpolation=cv2.INTER_AREA) for d in (-G, 0, G)]
        fn = f"{fid}_{i}.jpg"
        cv2.imwrite(str(OUT / "crops" / fn), cv2.hconcat(crops), [cv2.IMWRITE_JPEG_QUALITY, 90])
        meta.append({"file": fn, "y": int(i == h), "frame": fid, "box": [x1, y1, x2, y2], "score": sc, "box_h": round(hh, 1), "ball": [round(xy[0], 1), round(xy[1], 1)], "rect": [X1, Y1, X2, Y2]} | info)
        n += 1
    frames_meta.append({"frame": fid, "holder": h is not None, "players": n} | info)


# --- ball paths
for f in sorted(glob.glob(str(SEQ / "db/paths/*.json"))):
    sid = os.path.basename(f)[:-5]
    p = json.load(open(f))
    G, step, keys, marks = p["gap"], p["step"], p["frames"], p["marks"]
    if not any(m and "x" in m for m in marks):
        continue
    split = "test" if sid in TEST_SCENES else "train"
    fr = read(p["video"], keys[0] - G, keys[-1] - keys[0] + 2 * G + 1)
    for j, k in enumerate(keys):
        m = marks[j]
        if not (m and "x" in m):
            continue
        info = {"src": "path", "scene": sid, "hall": p["hall"], "split": split}
        emit(f"{sid}_{k}", fr, k, G, (m["x"], m["y"]), info | {"kind": "key"})
        nxt = marks[j + 1] if j + 1 < len(marks) else None
        if split == "train" and nxt and "x" in nxt and np.hypot(nxt["x"] - m["x"], nxt["y"] - m["y"]) < 40:
            for d in range(1, step):
                a = d / step
                xy = (m["x"] + a * (nxt["x"] - m["x"]), m["y"] + a * (nxt["y"] - m["y"]))
                emit(f"{sid}_{k + d}", fr, k + d, G, xy, info | {"kind": "interp"})
    print(sid, split, len(meta), flush=True)
    json.dump(cache, open(cache_f, "w"))

# --- single frames
user_split = json.load(open(SPLIT))
for f in sorted(glob.glob(str(PAGE / "db2/labels/*.json"))):
    lid = os.path.basename(f)[:-5]
    lab = json.load(open(f))
    if lab["state"] != "ball" or lid not in user_split:
        continue
    G = lab["gap"]
    fr = read(lab["video"], lab["frame"] - G, 2 * G + 1)
    if len(fr) < 2 * G + 1:
        continue
    hall = lab["hall"].removesuffix("_2") if lab["hall"].startswith("eisenach") else lab["hall"]
    emit(lid, fr, lab["frame"], G, (lab["x"], lab["y"]), {"src": "single", "scene": lid, "hall": hall, "split": user_split[lid], "kind": "single"})
print("single frames done", len(meta), flush=True)
json.dump(cache, open(cache_f, "w"))
json.dump(meta, open(OUT / "meta.json", "w"))
json.dump(frames_meta, open(OUT / "frames.json", "w"))
from collections import Counter

print(Counter((m["split"], m["kind"], m["y"]) for m in meta))
print(Counter((m["split"], m["kind"], m["holder"]) for m in frames_meta))
