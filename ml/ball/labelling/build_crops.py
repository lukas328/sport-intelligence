"""Build the "Ball oder nicht?" page data from a hardneg kernel's output (kaggle/hardneg_gpu.py).

One composite JPEG per item, i/<k>.jpg: the three-frame crop on top (cw x ch px, left-aligned),
the centre frame below (xh px high). Round 3 has 1280 px scenes, so the owner can click the true
ball when the ring misses it (crops.html, state "elsewhere").

    python ml/ball/labelling/build_crops.py KERNEL_OUT PUB_DIR [--n 500] [--seed 3]
        [--exclude LABELLED_ITEMS_JSON ...]

Selection for round 3 (balls in flight, the net's unsure peaks):
- at most 3 peaks per frame, as the kernel wrote them;
- half of the items from peaks with score < 0.5, half from >= 0.5;
- within each half, peaks with the most motion between the first and last frame first (half of
  the half), the rest random, so held balls and players standing still do not dominate.
"""
import argparse, json, random
from pathlib import Path

import cv2
import numpy as np


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("kout", type=Path)
    ap.add_argument("pub", type=Path)
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--seed", type=int, default=3)
    ap.add_argument("--exclude", type=Path, nargs="*", default=[])
    a = ap.parse_args()
    rnd = random.Random(a.seed)
    items = json.load(open(a.kout / "items.json"))
    seen = set()
    for e in a.exclude:
        seen |= {i["id"] for i in json.load(open(e))}
    items = [i for i in items if i["id"] not in seen]
    chosen = []
    for half in ([i for i in items if i["score"] < 0.5], [i for i in items if i["score"] >= 0.5]):
        want = min(len(half), a.n // 2)
        moving = sorted(half, key=lambda i: -i.get("motion", 0))[: want // 2]
        rest = [i for i in half if i not in moving]
        rnd.shuffle(rest)
        chosen += moving + rest[: want - len(moving)]
    rnd.shuffle(chosen)
    (a.pub / "i").mkdir(parents=True, exist_ok=True)
    out = []
    for k, it in enumerate(chosen):
        c = cv2.imread(str(a.kout / "c" / f"{it['id']}.jpg"))
        x = cv2.imread(str(a.kout / "x" / f"{it['id']}.jpg"))
        if c is None or x is None:
            continue
        W = max(c.shape[1], x.shape[1])
        img = np.zeros((c.shape[0] + x.shape[0], W, 3), np.uint8)
        img[: c.shape[0], : c.shape[1]] = c
        img[c.shape[0]:, : x.shape[1]] = x
        key = f"{k:03d}"
        cv2.imwrite(str(a.pub / "i" / f"{key}.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 80])
        out.append(it | {"k": key, "cw": c.shape[1], "ch": c.shape[0], "xw": x.shape[1], "xh": x.shape[0]})
    json.dump(out, open(a.pub / "items.json", "w"))
    lo = sum(i["score"] < 0.5 for i in out)
    print(len(out), "items;", lo, "with score < 0.5;", len({i["game"] for i in out}), "games")


if __name__ == "__main__":
    main()
