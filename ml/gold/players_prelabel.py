"""Person suggestions for the player part of the gold standard (docs/plans/messplan-phase0.md, 2).

Three frames per gold clip (first, middle, last) from the clip mp4s of the prelabel kernel; the
product's person detector (handball_vision.detection.YoloxDetector, YOLOX-S COCO, Apache-2.0,
weights checked against the SHA-256 in ml/models/yolox-coco.md) on each. Output per frame: the
foot point, box and score of every person, plus a two-team guess from shirt colour (k-means on
the torso's Lab colour) as a starting point for the owner's role labels. CPU is enough
(126 frames).

    python ml/gold/players_prelabel.py CLIPS_DIR YOLOX_S_ONNX OUT_DIR
writes OUT_DIR/players.json and OUT_DIR/f/<clip>_<frame>.jpg (the frames, for the labelling page).
"""

import hashlib
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from handball_vision.detection import YoloxDetector

SHA = "c5c2d13e59ae883e6af3b45daea64af4833a4951c92d116ec270d9ddbe998063"


def torso_lab(img: np.ndarray, d) -> list[float] | None:
    h = d.y2 - d.y1
    x1, x2 = int(d.x1 + 0.25 * (d.x2 - d.x1)), int(d.x2 - 0.25 * (d.x2 - d.x1))
    y1, y2 = int(d.y1 + 0.2 * h), int(d.y1 + 0.5 * h)
    if x2 - x1 < 2 or y2 - y1 < 2:
        return None
    crop = cv2.cvtColor(img[max(0, y1) : y2, max(0, x1) : x2], cv2.COLOR_BGR2LAB)
    return [float(v) for v in np.median(crop.reshape(-1, 3), axis=0)] if crop.size else None


def team_guess(cols: list[list[float] | None]) -> list[int | None]:
    idx = [i for i, c in enumerate(cols) if c is not None]
    out: list[int | None] = [None] * len(cols)
    if len(idx) < 4:
        return out
    x = np.float32([cols[i] for i in idx])
    _, lab, _ = cv2.kmeans(
        x,
        2,
        None,
        (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 0.5),
        5,
        cv2.KMEANS_PP_CENTERS,
    )
    for i, team in zip(idx, lab.ravel().tolist(), strict=True):
        out[i] = int(team)
    return out


def main() -> None:
    clips_dir, onnx, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    if hashlib.sha256(onnx.read_bytes()).hexdigest() != SHA:
        raise SystemExit("yolox_s.onnx does not match the SHA-256 of the model card")
    (out / "f").mkdir(parents=True, exist_ok=True)
    det = YoloxDetector(onnx, threads=4)
    res: dict = {}
    for mp4 in sorted(clips_dir.glob("*.mp4")):
        cap = cv2.VideoCapture(str(mp4))
        n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frames = []
        for f in (0, n // 2, n - 1):
            cap.set(cv2.CAP_PROP_POS_FRAMES, f)
            ok, img = cap.read()
            if ok:
                frames.append((f, img))
        cap.release()
        res[mp4.stem] = {}
        for (f, img), dets in zip(frames, det.detect([im for _, im in frames]), strict=True):
            people = [d for d in dets if d.cls == "person"]
            teams = team_guess([torso_lab(img, d) for d in people])
            res[mp4.stem][str(f)] = [
                {
                    "foot": [round(d.foot[0], 1), round(d.foot[1], 1)],
                    "box": [round(v, 1) for v in (d.x1, d.y1, d.x2, d.y2)],
                    "score": round(d.score, 3),
                    "team": t,
                }
                for d, t in zip(people, teams, strict=True)
            ]
            cv2.imwrite(str(out / "f" / f"{mp4.stem}_{f}.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 88])
        print(mp4.stem, [len(v) for v in res[mp4.stem].values()], flush=True)
    (out / "players.json").write_text(json.dumps(res, separators=(",", ":")))


if __name__ == "__main__":
    main()
