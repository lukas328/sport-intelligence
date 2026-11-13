"""Second pass for the gold clips: contact sheets for the frames the keyframe pass left open.

Targets per clip (from the clip's current gold document):
- every frame between two precise points where the ball moved more than FAST px per frame (passes, shots,
  bounces: a straight line in between would be wrong);
- keyframes left open ("?") next to a precise point within 2 keyframes (the ball should be near it).
Each row shows frame f-1, f, f+1 around the neighbouring precise point (same crop and answer
format as llm_sheets.py, so llm_apply.py applies the answers).

    python ml/gold/llm_dense_sheets.py CLIPS_JSON CLIPS_DIR DOC_JSON CLIP OUT_DIR [--fast 25] [--step 5]
"""

import argparse
import json
import math
from pathlib import Path

import cv2
import numpy as np

R, Z = 100, 1.5


def targets(L: dict[int, dict], n: int, step: int, fast: float) -> dict[int, tuple[float, float]]:
    P = sorted(k for k, v in L.items() if v.get("p") and v.get("x") is not None)
    out: dict[int, tuple[float, float]] = {}
    for a, b in zip(P, P[1:], strict=False):
        la, lb = L[a], L[b]
        if b - a > 1 and math.hypot(lb["x"] - la["x"], lb["y"] - la["y"]) / (b - a) > fast:
            for f in range(a + 1, b):
                t = (f - a) / (b - a)
                out[f] = (la["x"] + t * (lb["x"] - la["x"]), la["y"] + t * (lb["y"] - la["y"]))
    for k in range(0, n, step):
        if k in L and L[k].get("p"):
            continue
        near = [p for p in P if abs(p - k) <= 2 * step]
        if near and k not in out:
            p = min(near, key=lambda p: abs(p - k))
            out[k] = (L[p]["x"], L[p]["y"])
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("clips_json", type=Path)
    ap.add_argument("clips_dir", type=Path)
    ap.add_argument("doc", type=Path)
    ap.add_argument("clip")
    ap.add_argument("out", type=Path)
    ap.add_argument("--fast", type=float, default=12.0, help="px per frame")
    ap.add_argument("--step", type=int, default=5)
    ap.add_argument("--count-only", action="store_true")
    a = ap.parse_args()
    c = next(x for x in json.loads(a.clips_json.read_text()) if x["id"] == a.clip)
    d = json.loads(a.doc.read_text())
    d = d.get("data", d)
    L = {int(k): v for k, v in d["labels"].items()}
    T = targets(L, c["n"], a.step, a.fast)
    if a.count_only:
        print(a.clip, len(T))
        return
    cap = cv2.VideoCapture(str(a.clips_dir / f"{a.clip}.mp4"))
    frames = []
    while True:
        ok, im = cap.read()
        if not ok:
            break
        frames.append(im)
    n = len(frames)
    rows, meta = [], []
    for f in sorted(T):
        cx, cy = T[f]
        x0 = int(min(max(cx - R, 0), c["w"] - 2 * R))
        y0 = int(min(max(cy - R, 0), c["h"] - 2 * R))
        cands = [p for p in c["cand"][f] if x0 <= p[0] < x0 + 2 * R and y0 <= p[1] < y0 + 2 * R][:6]
        tiles = []
        for j in (max(0, f - 1), f, min(n - 1, f + 1)):
            t = cv2.resize(
                frames[j][y0 : y0 + 2 * R, x0 : x0 + 2 * R],
                (int(2 * R * Z),) * 2,
                interpolation=cv2.INTER_CUBIC,
            )
            if j == f:
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
        sep = np.full((int(2 * R * Z), 4, 3), 255, np.uint8)
        row = np.hstack([tiles[0], sep, tiles[1], sep, tiles[2]])
        lab = f"row {len(meta)}  frame {f}"
        cv2.putText(row, lab, (6, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        cv2.putText(row, lab, (6, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        rows.append(row)
        meta.append({"row": len(meta), "frame": f, "x0": x0, "y0": y0, "cands": cands})
    a.out.mkdir(parents=True, exist_ok=True)
    for s in range(0, len(rows), 4):
        sheet = np.vstack(
            [np.vstack([r, np.full((4, r.shape[1], 3), 255, np.uint8)]) for r in rows[s : s + 4]]
        )
        cv2.imwrite(
            str(a.out / f"{a.clip}_{s // 4:02d}.jpg"), sheet, [cv2.IMWRITE_JPEG_QUALITY, 85]
        )
    (a.out / f"{a.clip}.json").write_text(json.dumps({"clip": a.clip, "rows": meta}))
    print(a.clip, len(meta), "rows,", (len(rows) + 3) // 4, "sheets")


if __name__ == "__main__":
    main()
