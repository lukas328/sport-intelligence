"""Heavy pass over short clips, run once: per-frame cheap cues, ball-net peaks, people, thumbnails.

Everything later (`cues.py`, `evaluate.py`) works on the cached npz, so analysis iterations are
cheap. Per clip:

- every frame: camera pan (phase correlation on a quarter-size grey image, in full-res pixels),
  correlation response, compensated motion energy (mean |grey_t - shifted grey_t-1| outside the
  overlay band), raw frame-difference energy;
- every `--ball-step` frames: 3-frame ball net (t-G, t, t+G stacked, RGB 0..255, stride-4 heatmap)
  on the frame cropped to multiples of 32; top 5 peaks >= 0.2 in image and canvas coordinates;
- every `--det-step` frames: YOLOX people (boxes, score);
- every `--thumb-step` frames: 320x180 colour thumbnail (for goal finding and looking at it) and
  the bottom-centre overlay crop (score bug reference only).

usage: uv run --project packages/vision python ml/goals/extract.py OUT_DIR clip.mp4 [clip.mp4 ...]
       [--ball MODEL.onnx] [--ball-step 4] [--det-step 25] [--thumb-step 5] [--threads 2]
       [--no-ball] [--no-det]
"""

from __future__ import annotations

import argparse
import sys
import time
from collections import deque
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "packages/vision"))
from handball_vision.detection import YoloxDetector  # noqa: E402

BALL = "/tmp/claude-0/-home-user/3dc450e2-2499-5e21-b252-1c4e366c6b5a/scratchpad/ball3/ball3d.onnx"
OVERLAY_BAND = (0.85, 0.94)  # share of the height where the score bug sits (excluded from energy)


def run_clip(path: Path, out: Path, ball: ort.InferenceSession | None, det: YoloxDetector | None,
             a: argparse.Namespace) -> None:
    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 50.0
    g_off = 3 if fps > 40 else 2
    buf: deque[np.ndarray] = deque(maxlen=2 * g_off + 1)
    prev = None
    off = np.zeros(2)
    pan, resp, energy, rawdiff, offs = [], [], [], [], []
    peaks = []  # frame, x_img, y_img, x_canvas, y_canvas, score, rank
    people = []  # frame, x1, y1, x2, y2, score
    thumbs, thumb_idx, bugs = [], [], []
    k = -1
    t0 = time.time()
    while True:
        ok, f = cap.read()
        if not ok:
            break
        k += 1
        if f.shape[1] != 1280:
            f = cv2.resize(f, (1280, round(f.shape[0] * 1280 / f.shape[1])), interpolation=cv2.INTER_AREA)
        hh, ww = f.shape[:2]
        g = cv2.cvtColor(cv2.resize(f, (320, 180), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
        g = g.astype(np.float32)
        y0, y1 = int(OVERLAY_BAND[0] * 180), int(OVERLAY_BAND[1] * 180)
        if prev is None:
            d = np.zeros(2)
            r = 1.0
            e = 0.0
            rd = 0.0
        else:
            (dx, dy), r = cv2.phaseCorrelate(prev, g)
            d = np.array([dx, dy])
            m = np.float32([[1, 0, dx], [0, 1, dy]])
            warped = cv2.warpAffine(prev, m, (320, 180), borderMode=cv2.BORDER_REPLICATE)
            diff = np.abs(g - warped)
            diff[y0:y1] = 0
            pad = 8 + int(abs(dx)) + 1
            e = float(diff[8:-8, pad:-pad].mean()) if pad < 150 else float(diff.mean())
            rd = float(np.abs(g - prev)[np.r_[0:y0, y1:180]].mean())
        prev = g
        off = off + d * 4.0  # full-res (1280) pixels
        pan.append(d * 4.0)
        resp.append(r)
        energy.append(e)
        rawdiff.append(rd)
        offs.append(off.copy())
        buf.append(f)
        if k % a.thumb_step == 0:
            thumbs.append(cv2.resize(f, (320, 180), interpolation=cv2.INTER_AREA))
            thumb_idx.append(k)
            bugs.append(f[int(0.86 * hh):int(0.93 * hh), int(0.36 * ww):int(0.64 * ww)].copy())
        if det is not None and k % a.det_step == 0:
            for dd in det.detect([f])[0]:
                if dd.cls == "person":
                    people.append((k, dd.x1, dd.y1, dd.x2, dd.y2, dd.score))
        if len(buf) == 2 * g_off + 1:
            c = k - g_off
            if ball is not None and c % a.ball_step == 0:
                h2, w2 = hh // 32 * 32, ww // 32 * 32
                x = np.concatenate(
                    [cv2.cvtColor(b[:h2, :w2], cv2.COLOR_BGR2RGB) for b in (buf[0], buf[g_off], buf[2 * g_off])], 2
                ).transpose(2, 0, 1)[None].astype(np.float32)
                hm = 1 / (1 + np.exp(-ball.run(None, {"x": x})[0][0, 0]))
                for rank in range(5):
                    yx = np.unravel_index(hm.argmax(), hm.shape)
                    if hm[yx] < 0.2:
                        break
                    px, py = yx[1] * 4 + 2, yx[0] * 4 + 2
                    oc = offs[c]
                    peaks.append((c, px, py, px + oc[0], py + oc[1], float(hm[yx]), rank))
                    hm[max(0, yx[0] - 6):yx[0] + 6, max(0, yx[1] - 6):yx[1] + 6] = 0
    np.savez_compressed(
        out,
        fps=fps, n=k + 1, g_off=g_off, ball_step=a.ball_step,
        pan=np.array(pan, np.float32), resp=np.array(resp, np.float32),
        energy=np.array(energy, np.float32), rawdiff=np.array(rawdiff, np.float32),
        offs=np.array(offs, np.float32),
        peaks=np.array(peaks, np.float32).reshape(-1, 7),
        people=np.array(people, np.float32).reshape(-1, 6),
        thumbs=np.array(thumbs, np.uint8), thumb_idx=np.array(thumb_idx),
        bugs=np.array(bugs, np.uint8),
    )
    print(f"{path.name}: {k + 1} frames, {len(peaks)} peaks, {len(people)} people, "
          f"{time.time() - t0:.0f}s", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out", type=Path)
    ap.add_argument("clips", type=Path, nargs="+")
    ap.add_argument("--ball", default=BALL)
    ap.add_argument("--ball-step", type=int, default=4)
    ap.add_argument("--det-step", type=int, default=25)
    ap.add_argument("--thumb-step", type=int, default=5)
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--no-det", action="store_true")
    ap.add_argument("--no-ball", action="store_true", help="cheap cues only (fast pass)")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    so = ort.SessionOptions()
    so.intra_op_num_threads = a.threads
    ball = None if a.no_ball else ort.InferenceSession(a.ball, so, providers=["CPUExecutionProvider"])
    root = Path(__file__).resolve().parents[2]
    det = None if a.no_det else YoloxDetector(root / "data/models/yolox_m.onnx", threads=a.threads)
    for clip in a.clips:
        out = a.out / (clip.stem + ".npz")
        if out.exists():
            continue
        run_clip(clip, out, ball, det, a)


if __name__ == "__main__":
    main()
