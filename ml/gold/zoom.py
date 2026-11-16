"""Zoom into one frame of a clip for labelling by eye.

    python ml/gold/zoom.py CLIP_MP4 FRAME X Y OUT_JPG [--r 120] [--z 3] [--frames 1]
Writes the square of half size R px around (X, Y) of FRAME (and with --frames 3 also the frames
before and after, side by side) at Z times, with a grid every 20 frame px labelled in frame px.
"""

import argparse

import cv2
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("mp4")
ap.add_argument("frame", type=int)
ap.add_argument("x", type=float)
ap.add_argument("y", type=float)
ap.add_argument("out")
ap.add_argument("--r", type=int, default=120)
ap.add_argument("--z", type=float, default=3.0)
ap.add_argument("--frames", type=int, default=1, choices=(1, 3))
a = ap.parse_args()
cap = cv2.VideoCapture(a.mp4)
want = [a.frame] if a.frames == 1 else [a.frame - 1, a.frame, a.frame + 1]
got = {}
k = 0
while k <= max(want):
    ok, im = cap.read()
    if not ok:
        break
    if k in want:
        got[k] = im
    k += 1
tiles = []
for f in want:
    im = got.get(f)
    if im is None:
        continue
    h, w = im.shape[:2]
    x0 = int(min(max(a.x - a.r, 0), w - 2 * a.r))
    y0 = int(min(max(a.y - a.r, 0), h - 2 * a.r))
    t = cv2.resize(
        im[y0 : y0 + 2 * a.r, x0 : x0 + 2 * a.r],
        None,
        fx=a.z,
        fy=a.z,
        interpolation=cv2.INTER_CUBIC,
    )
    for gx in range((x0 // 20 + 1) * 20, x0 + 2 * a.r, 20):
        u = int((gx - x0) * a.z)
        cv2.line(t, (u, 0), (u, t.shape[0]), (255, 255, 255), 1)
        if gx % 40 == 0:
            cv2.putText(t, str(gx), (u + 2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
    for gy in range((y0 // 20 + 1) * 20, y0 + 2 * a.r, 20):
        v = int((gy - y0) * a.z)
        cv2.line(t, (0, v), (t.shape[1], v), (255, 255, 255), 1)
        if gy % 40 == 0:
            cv2.putText(t, str(gy), (2, v - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
    cv2.putText(
        t, f"frame {f}", (6, t.shape[0] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2
    )
    tiles.append(t)
sep = np.full((tiles[0].shape[0], 6, 3), 255, np.uint8)
out = tiles[0]
for t in tiles[1:]:
    out = np.hstack([out, sep, t])
cv2.imwrite(a.out, out, [cv2.IMWRITE_JPEG_QUALITY, 90])
print(a.out, out.shape[1], "x", out.shape[0])
