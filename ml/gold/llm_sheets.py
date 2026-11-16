"""Contact sheets for labelling the gold clips by eye (Claude looks, the owner confirms the video).

Per keyframe (every STEP frames) one row: the previous, the current and the next keyframe as
240 px crops (2x) around the best guess (the owner's rough point one frame later, else the
suggestion, else the frame centre). The current crop carries the ball candidates (net peaks,
OWLv2 boxes) as small numbered rings; the number sits beside the ring so the ball stays visible.
The answer per row is a candidate number, a point "x,y" in the crop (0..300), "h" for in hand
with a number or point, or "-" for no ball visible.

    python ml/gold/llm_sheets.py CLIPS_JSON CLIPS_DIR LABELS_DIR CLIP_ID OUT_DIR [--step 6]
writes OUT_DIR/<clip>_<n>.jpg (4 rows each) and OUT_DIR/<clip>.json (row -> frame, crop origin, candidates).
"""

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

R = 100  # crop half size in frame px (shown 1.5x = 300 px)
Z = 1.5


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("clips_json", type=Path)
    ap.add_argument("clips_dir", type=Path)
    ap.add_argument("labels_dir", type=Path)
    ap.add_argument("clip")
    ap.add_argument("out", type=Path)
    ap.add_argument("--step", type=int, default=6)
    ap.add_argument(
        "--only-rough",
        action="store_true",
        help="only keyframes with a rough point within 2 frames (the crop elsewhere is a guess)",
    )
    a = ap.parse_args()
    c = next(x for x in json.loads(a.clips_json.read_text()) if x["id"] == a.clip)
    lp = a.labels_dir / f"{a.clip}.json"
    rough = {}
    if lp.exists():
        d = json.loads(lp.read_text())
        d = d.get("data", d)
        rough = {int(k): v for k, v in d["labels"].items() if v.get("x") is not None}
    cap = cv2.VideoCapture(str(a.clips_dir / f"{a.clip}.mp4"))
    frames = []
    while True:
        ok, im = cap.read()
        if not ok:
            break
        frames.append(im)
    n = len(frames)
    keys = list(range(0, n, a.step))
    rows, meta = [], []
    for k in keys:
        if a.only_rough and not any(k + d in rough for d in (-2, -1, 0, 1, 2)):
            continue
        g = rough.get(k + 1) or rough.get(k)
        if g:
            cx, cy = g["x"], g["y"]
        elif c["sug"][k]:
            cx, cy = c["sug"][k][:2]
        else:
            cx, cy = c["w"] / 2, c["h"] / 2
        x0 = int(min(max(cx - R, 0), c["w"] - 2 * R))
        y0 = int(min(max(cy - R, 0), c["h"] - 2 * R))
        cands = [p for p in c["cand"][k] if x0 <= p[0] < x0 + 2 * R and y0 <= p[1] < y0 + 2 * R][:6]
        tiles = []
        for j in (max(0, k - a.step), k, min(n - 1, k + a.step)):
            t = cv2.resize(
                frames[j][y0 : y0 + 2 * R, x0 : x0 + 2 * R],
                (int(2 * R * Z), int(2 * R * Z)),
                interpolation=cv2.INTER_CUBIC,
            )
            if j == k:
                for i, (px, py) in enumerate(cands):
                    u, v = int((px - x0) * Z), int((py - y0) * Z)
                    cv2.circle(t, (u, v), 11, (0, 255, 255), 1)
                    cv2.putText(
                        t, str(i + 1), (u + 12, v - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3
                    )
                    cv2.putText(
                        t,
                        str(i + 1),
                        (u + 12, v - 8),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 255, 255),
                        1,
                    )
            tiles.append(t)
        row = np.hstack(
            [
                tiles[0],
                np.full((int(2 * R * Z), 4, 3), 255, np.uint8),
                tiles[1],
                np.full((int(2 * R * Z), 4, 3), 255, np.uint8),
                tiles[2],
            ]
        )
        cv2.putText(
            row,
            f"row {len(meta)}  frame {k}",
            (6, 16),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            2,
        )
        cv2.putText(
            row, f"row {len(meta)}  frame {k}", (6, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1
        )
        rows.append(row)
        meta.append({"row": len(meta), "frame": k, "x0": x0, "y0": y0, "cands": cands})
    a.out.mkdir(parents=True, exist_ok=True)
    for s in range(0, len(rows), 4):
        sheet = np.vstack(
            [np.vstack([r, np.full((4, r.shape[1], 3), 255, np.uint8)]) for r in rows[s : s + 4]]
        )
        cv2.imwrite(
            str(a.out / f"{a.clip}_{s // 4:02d}.jpg"), sheet, [cv2.IMWRITE_JPEG_QUALITY, 85]
        )
    (a.out / f"{a.clip}.json").write_text(
        json.dumps({"clip": a.clip, "step": a.step, "rows": meta})
    )
    print(a.clip, len(meta), "rows,", (len(rows) + 3) // 4, "sheets")


if __name__ == "__main__":
    main()
