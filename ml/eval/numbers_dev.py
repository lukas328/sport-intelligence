"""Shirt-number reading on the frozen dev labels (ml/gold/data/numbers_dev_v1.json).

    python ml/eval/numbers_dev.py CLIPS_DIR MODELS_DIR [THRESHOLD]

CLIPS_DIR holds sghorgen-h1-5min.mp4 and sghorgen-h2-5min.mp4 (R2 handball-testdata/testclips),
MODELS_DIR the PP-OCRv4 det/rec ONNX files (as in the image). Reads every labelled box with the
product reader (`NumberReader.read_player`) and prints, at the confidence threshold (default the
product's `MIN_CONFIDENCE`): correct readings, wrong readings, precision, and the share of the
readable shirts that were read correctly. Dev only: never tune on the end test.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2

from handball_vision.numbers import MIN_CONFIDENCE, NumberReader

LABELS = Path(__file__).resolve().parents[1] / "gold" / "data" / "numbers_dev_v1.json"
FILES = {"h1": "sghorgen-h1-5min.mp4", "h2": "sghorgen-h2-5min.mp4"}


def main() -> None:
    clips, models = Path(sys.argv[1]), Path(sys.argv[2])
    threshold = float(sys.argv[3]) if len(sys.argv) > 3 else MIN_CONFIDENCE
    items = json.loads(LABELS.read_text(encoding="utf-8"))["items"]
    reader = NumberReader(
        models / "ch_PP-OCRv4_det_infer.onnx", models / "ch_PP-OCRv4_rec_infer.onnx"
    )
    frames = {}
    for clip, name in FILES.items():
        need = {it["frame"] for it in items if it["clip"] == clip}
        cap = cv2.VideoCapture(str(clips / name))
        i = 0
        while need:
            ok, frame = cap.read()
            if not ok:
                break
            if i in need:
                frames[(clip, i)] = frame
                need.discard(i)
            i += 1
    right = wrong = readable = 0
    mistakes = []
    for it in items:
        label = it["label"]
        readable += label != "-"
        r = reader.read_player(frames[(it["clip"], it["frame"])], tuple(it["box"]))
        if r is None or r.confidence < threshold:
            continue
        if r.number == label:
            right += 1
        else:
            wrong += 1
            mistakes.append((label, r.number, round(r.confidence, 2)))
    print(
        json.dumps(
            {
                "threshold": threshold,
                "boxes": len(items),
                "readable": readable,
                "right": right,
                "wrong": wrong,
                "precision": round(right / max(1, right + wrong), 3),
                "read_share": round(right / max(1, readable), 3),
                "mistakes (label, read, conf)": mistakes,
            }
        )
    )


if __name__ == "__main__":
    main()
