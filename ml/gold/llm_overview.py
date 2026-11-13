"""Overview sheets: Claude finds the ball in the whole picture (replaces the owner's rough track).

The precise contact sheets (llm_sheets.py) crop 200 px around a guess. Without the owner's rough
track the guess is the tracker's, which sits on a lamp, a logo or a bench bag about a third of the
time, and then the ball is not in the crop. Here every keyframe is shown whole (1280 px wide, a
labelled 100 px grid) with the ball candidates as numbered rings, and the answer is where the game
ball is. The answers become a rough track (labels without "p"), which llm_sheets.py then crops
around, exactly like the owner's.

    python ml/gold/llm_overview.py sheets CLIPS_JSON CLIPS_DIR CLIP OUT_DIR [--every 0.2]
    python ml/gold/llm_overview.py apply OUT_DIR CLIP ANSWERS_JSON LABELS_DIR
Answer per keyframe: candidate number, "x,y" in full-picture pixels (read off the grid), "h" suffix
when held, "-" when no game ball is in the picture, "?" when unsure.
"""

import argparse
import json
from pathlib import Path

import cv2

W = 1280
MAX_CANDS = 9


def sheets(a: argparse.Namespace) -> None:
    c = next(x for x in json.loads(a.clips_json.read_text()) if x["id"] == a.clip)
    step = max(1, round(c["fps"] * a.every))
    cap = cv2.VideoCapture(str(a.clips_dir / f"{a.clip}.mp4"))
    a.out.mkdir(parents=True, exist_ok=True)
    s = W / c["w"]
    meta, k = [], 0
    while True:
        ok, im = cap.read()
        if not ok:
            break
        if k % step == 0:
            im = cv2.resize(im, (W, round(c["h"] * s)), interpolation=cv2.INTER_AREA)
            h = im.shape[0]
            for x in range(100, W, 100):
                cv2.line(im, (x, 0), (x, h), (255, 255, 255), 1)
                cv2.putText(im, str(x), (x + 2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 3)
                cv2.putText(
                    im, str(x), (x + 2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1
                )
            for y in range(100, h, 100):
                cv2.line(im, (0, y), (W, y), (255, 255, 255), 1)
                cv2.putText(im, str(y), (2, y - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 3)
                cv2.putText(
                    im, str(y), (2, y - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1
                )
            cands = c["cand"][k][:MAX_CANDS]
            for i, (px, py) in enumerate(cands):
                u, v = round(px * s), round(py * s)
                cv2.circle(im, (u, v), 12, (0, 255, 255), 1)
                for col, th in (((0, 0, 0), 3), ((0, 255, 255), 1)):
                    cv2.putText(
                        im, str(i + 1), (u + 13, v - 9), cv2.FONT_HERSHEY_SIMPLEX, 0.5, col, th
                    )
            label = f"{a.clip} row {len(meta)} frame {k}"
            for col, th in (((255, 255, 255), 3), ((0, 0, 0), 1)):
                cv2.putText(im, label, (110, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, col, th)
            cv2.imwrite(
                str(a.out / f"{a.clip}_o{len(meta):02d}.jpg"), im, [cv2.IMWRITE_JPEG_QUALITY, 88]
            )
            meta.append({"row": len(meta), "frame": k, "scale": s, "cands": cands})
        k += 1
    (a.out / f"{a.clip}_o.json").write_text(json.dumps({"clip": a.clip, "rows": meta}))
    print(a.clip, len(meta), "overview frames, every", step)


def apply(a: argparse.Namespace) -> None:
    meta = json.loads((a.out / f"{a.clip}_o.json").read_text())["rows"]
    ans = json.loads(a.answers.read_text())
    pts: dict[int, dict] = {}
    for r in meta:
        t = str(ans.get(str(r["row"]), "?")).strip()
        if t in ("?", ""):
            continue
        if t == "-":
            pts[r["frame"]] = {"s": "out"}
            continue
        st = "held" if t.endswith("h") else "free"
        t = t.rstrip("h")
        if "," in t:
            x, y = (float(v) / r["scale"] for v in t.split(","))
        else:
            x, y = r["cands"][int(t) - 1]
        pts[r["frame"]] = {"x": round(x, 1), "y": round(y, 1), "s": st}
    # a rough point on every frame between two neighbouring keyframes with a ball (linear)
    keys = sorted(f for f, v in pts.items() if "x" in v)
    step = meta[1]["frame"] - meta[0]["frame"] if len(meta) > 1 else 1
    labels = {str(f): v for f, v in pts.items()}
    for f0, f1 in zip(keys, keys[1:], strict=False):
        if f1 - f0 > 2 * step:
            continue
        p0, p1 = pts[f0], pts[f1]
        for f in range(f0 + 1, f1):
            u = (f - f0) / (f1 - f0)
            labels[str(f)] = {
                "x": round(p0["x"] + u * (p1["x"] - p0["x"]), 1),
                "y": round(p0["y"] + u * (p1["y"] - p0["y"]), 1),
                "s": p0["s"],
            }
    a.labels.mkdir(parents=True, exist_ok=True)
    doc = {"labels": labels, "shots": [], "done": False, "pdone": False, "src": "llm-overview"}
    (a.labels / f"{a.clip}.json").write_text(json.dumps(doc))
    print(a.clip, len(pts), "overview answers,", len(labels), "rough points")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sheets")
    s.add_argument("clips_json", type=Path)
    s.add_argument("clips_dir", type=Path)
    s.add_argument("clip")
    s.add_argument("out", type=Path)
    s.add_argument("--every", type=float, default=0.2, help="seconds between keyframes")
    p = sub.add_parser("apply")
    p.add_argument("out", type=Path)
    p.add_argument("clip")
    p.add_argument("answers", type=Path)
    p.add_argument("labels", type=Path)
    a = ap.parse_args()
    sheets(a) if a.cmd == "sheets" else apply(a)


if __name__ == "__main__":
    main()
