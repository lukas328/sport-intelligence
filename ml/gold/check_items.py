"""Build "Ball oder nicht?" items for the gold points of tier "check" (export.py), so the owner
confirms or rejects Claude's points in one key press each (labelling/crops.html).

Per item one composite JPEG: frames f-1, f, f+1 as 96 px crops around the point (2x, the ring in
the middle of each), and the whole frame below (640 wide, the point circled).

    python ml/gold/check_items.py GOLD_JSON CLIPS_DIR OUT_DIR [--parts 2]
writes OUT_DIR/part<N>/i/<k>.jpg and items.json per part.
"""

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

R = 48


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("gold", type=Path)
    ap.add_argument("clips_dir", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--parts", type=int, default=2)
    a = ap.parse_args()
    g = json.loads(a.gold.read_text())["clips"]
    todo = [
        (cid, r)
        for cid, c in g.items()
        for r in c["labels"]
        if r["tier"] == "check" and r["x"] is not None
    ]
    per = -(-len(todo) // a.parts)
    for p in range(a.parts):
        d = a.out / f"part{p + 1}"
        (d / "i").mkdir(parents=True, exist_ok=True)
        items = []
        cur, frames = None, []
        for k, (cid, r) in enumerate(todo[p * per : (p + 1) * per]):
            if cid != cur:
                cap = cv2.VideoCapture(str(a.clips_dir / f"{cid}.mp4"))
                frames = []
                while True:
                    ok, im = cap.read()
                    if not ok:
                        break
                    frames.append(im)
                cur = cid
            f, x, y = r["frame"], int(r["x"]), int(r["y"])
            crops = []
            for j in (max(0, f - 1), f, min(len(frames) - 1, f + 1)):
                pad = cv2.copyMakeBorder(
                    frames[j], R, R, R, R, cv2.BORDER_CONSTANT, value=(0, 0, 0)
                )
                crops.append(
                    cv2.resize(
                        pad[y : y + 2 * R, x : x + 2 * R],
                        (4 * R, 4 * R),
                        interpolation=cv2.INTER_CUBIC,
                    )
                )
            top = np.concatenate(crops, 1)
            sc = frames[f].copy()
            cv2.circle(sc, (x, y), 22, (0, 230, 255), 3)
            H = round(sc.shape[0] * 640 / sc.shape[1])
            sc = cv2.resize(sc, (640, H))
            W = max(top.shape[1], 640)
            img = np.zeros((top.shape[0] + H, W, 3), np.uint8)
            img[: top.shape[0], : top.shape[1]] = top
            img[top.shape[0] :, :640] = sc
            key = f"{k:03d}"
            cv2.imwrite(str(d / "i" / f"{key}.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 80])
            items.append(
                {
                    "id": f"{cid}_{f}",
                    "k": key,
                    "ch": top.shape[0],
                    "cw": top.shape[1],
                    "xh": H,
                    "xw": 640,
                    "game": cid,
                    "video": cid,
                    "frame": f,
                    "x": r["x"],
                    "y": r["y"],
                    "score": 0,
                }
            )
        (d / "items.json").write_text(json.dumps(items))
        print(d, len(items))


if __name__ == "__main__":
    main()
