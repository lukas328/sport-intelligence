"""Score readers as in the GPU job on one clip segment; writes the summaries.

    PYTHONPATH=packages/vision:apps/gpu-worker/src uv run python ml/integration/scoreboard/run.py \
        PROXY.mp4 START_S END_S OUT.json MODELS_DIR

The overlay reader first (Tesseract, as `analysis._overlay_reader`), else `HallBoardReader` with
PP-OCRv4 (MODELS_DIR holds ch_PP-OCRv4_det_infer.onnx and ch_PP-OCRv4_rec_infer.onnx) at the
default rates. Frame indices start at START_S, so times are clip seconds.
"""

import json
import sys
from pathlib import Path

import cv2
import numpy as np

from handball_gpu_worker.analysis import _overlay_reader, _overlay_summary
from handball_vision.hallboard import HallBoardReader
from handball_vision.numbers import NumberReader

video, a, b, out = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), Path(sys.argv[4])
M = Path(sys.argv[5])
cap = cv2.VideoCapture(video)
fps = cap.get(5)
f0, f1 = int(a * fps), int(b * fps)
spread = []
for t in np.linspace(f0, f1 - 1, 36):
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(t))
    ok, fr = cap.read()
    if ok:
        spread.append(fr)
reader = _overlay_reader(spread, fps, (f1 - f0) / fps)
board = None
if reader is None:
    board = HallBoardReader(
        NumberReader(M / "ch_PP-OCRv4_det_infer.onnx", M / "ch_PP-OCRv4_rec_infer.onnx"),
        fps,
        every_s=1.0,
        full_every_s=4.0,
        probe_every_s=0.25,
    )
cap.set(cv2.CAP_PROP_POS_FRAMES, f0)
for i in range(f1 - f0):
    ok, fr = cap.read()
    if not ok:
        break
    (reader.add if reader else board.add)(i, fr)
res = {
    "source": "overlay" if reader else "hall_scoreboard",
    "overlay": _overlay_summary(reader) if reader else None,
    "board": board.summary() if board else None,
}
out.write_text(
    json.dumps(res, default=lambda o: o.__dict__ if hasattr(o, "__dict__") else str(o), indent=1)
)
g = (res["overlay"] or {}).get("goals") if reader else (res["board"] or {}).get("goals")
print(res["source"], "readings", (res["board"] or {}).get("readings"), "goals", len(g or []))
