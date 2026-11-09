"""Benchmark the 3-frame ball nets (and OWLv2's suggestions) on ball test set 2.

Test set 2: 252 frames from 42 halls never used in training (testset_pick.py, labelled on the
"Ball-Testset: neue Hallen" page). Hit = a peak within 12 px (1280-wide frame) of the label.

    python ml/ball/bench_testset2.py ITEMS_JSON LABELS_DIR T_DIR MODEL.pt [MODEL.pt ...]

LABELS_DIR holds one JSON per frame as the artifact database exports it; T_DIR the triplets
(<k>.jpg, 3 x 1280 wide). Needs torch, torchvision, opencv (CPU is enough).
"""
import collections, glob, json, math, sys
from pathlib import Path

import cv2, numpy as np, torch, torch.nn as nn, torch.nn.functional as F, torchvision

R_HIT = 12


class BallNet3(nn.Module):  # as in kaggle/train_r6.py
    def __init__(s):
        super().__init__()
        r = torchvision.models.resnet18(weights=None)
        c1 = nn.Conv2d(9, 64, 7, 2, 3, bias=False)
        s.stem = nn.Sequential(c1, r.bn1, r.relu, r.maxpool); s.l1 = r.layer1; s.l2 = r.layer2
        s.up = nn.Sequential(nn.Conv2d(128, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU())
        s.head = nn.Sequential(nn.Conv2d(128, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(), nn.Conv2d(64, 1, 1))
        s.register_buffer("mean", torch.tensor([0.485, 0.456, 0.406] * 3).view(1, 9, 1, 1) * 255)
        s.register_buffer("std", torch.tensor([0.229, 0.224, 0.225] * 3).view(1, 9, 1, 1) * 255)

    def forward(s, x):
        x = (x - s.mean) / s.std; a = s.l1(s.stem(x)); b = s.l2(a)
        b = F.interpolate(s.up(b), size=a.shape[-2:], mode="bilinear", align_corners=False)
        return s.head(torch.cat([a, b], 1))


def peaks(hm, k=5):
    hm = hm.copy(); out = []
    for _ in range(k):
        y, x = np.unravel_index(hm.argmax(), hm.shape)
        out.append((x * 4 + 2, y * 4 + 2, float(hm[y, x])))
        hm[max(0, y - 6):y + 6, max(0, x - 6):x + 6] = 0
    return out


def summary(name, rows):
    b = [r for r in rows if r["state"] == "ball"]; n = [r for r in rows if r["state"] == "none"]
    def pct(xs): return f"{100 * np.mean(xs):.0f} %" if xs else "-"
    line = (f"{name:14s} balls {len(b):3d}  top1 {pct([r['top1'] for r in b]):>5s}  top5 {pct([r['top5'] for r in b]):>5s}"
            f"  score>=0.3 at ball {pct([r['at_ball'] >= 0.3 for r in b]):>5s}")
    if n:
        line += f"  | no-ball frames {len(n)}: top peak median {np.median([r['top'] for r in n]):.2f}, >=0.5 in {pct([r['top'] >= 0.5 for r in n])}"
    print(line)


def main() -> None:
    items = {i["id"]: i for i in json.load(open(sys.argv[1]))}
    labels = {}
    for f in glob.glob(str(Path(sys.argv[2]) / "*.json")):
        d = json.load(open(f)); labels[Path(f).stem] = d.get("data", d)
    labels = {k: v for k, v in labels.items() if v["state"] in ("ball", "none") and k in items}
    tdir = Path(sys.argv[3])
    print(len(labels), "frames:", collections.Counter(v["state"] for v in labels.values()))
    # OWLv2 suggestions (centre frame) as a reference
    owl = []
    for k, l in labels.items():
        o = items[k]["owl"]
        d = [math.hypot(b[0] - l["x"], b[1] - l["y"]) for b in o] if l["state"] == "ball" else []
        at = max([b[4] for b, dd in zip(o, d) if dd < R_HIT], default=0.0)
        owl.append({"id": k, "state": l["state"], "top1": bool(d) and d[0] < R_HIT, "top5": any(x < R_HIT for x in d[:5]),
                    "at_ball": at, "top": o[0][4] if o else 0.0, "clock": items[k]["clock_running"]})
    torch.set_num_threads(4)
    results = {"OWLv2": owl}
    for mp in sys.argv[4:]:
        net = BallNet3(); net.load_state_dict(torch.load(mp, map_location="cpu", weights_only=True)); net.eval()
        rows = []
        for k, l in labels.items():
            it = items[k]; t = cv2.imread(str(tdir / f"{it.get('k', k)}.jpg")); W = it["w"]
            ims = [cv2.cvtColor(t[:, j * W:(j + 1) * W], cv2.COLOR_BGR2RGB) for j in range(3)]
            h2, w2 = ims[0].shape[0] // 32 * 32, W // 32 * 32
            x = torch.from_numpy(np.concatenate([i[:h2, :w2] for i in ims], 2).transpose(2, 0, 1)[None].astype(np.float32))
            with torch.no_grad():
                hm = torch.sigmoid(net(x))[0, 0].numpy()
            pk = peaks(hm); r = {"id": k, "state": l["state"], "top": pk[0][2], "clock": it["clock_running"]}
            if l["state"] == "ball":
                d = [math.hypot(px - l["x"], py - l["y"]) for px, py, _ in pk]
                yy, xx = int(l["y"] / 4), int(l["x"] / 4); loc = hm[max(0, yy - 3):yy + 4, max(0, xx - 3):xx + 4]
                r |= {"top1": d[0] < R_HIT, "top5": min(d) < R_HIT, "at_ball": float(loc.max()) if loc.size else 0.0}
            rows.append(r)
        results[Path(mp).stem] = rows
    for name, rows in results.items():
        summary(name, rows)
    print("-- clock running (ball in play) only")
    for name, rows in results.items():
        summary(name, [r for r in rows if r["clock"]])
    print("-- clock stopped or unknown")
    for name, rows in results.items():
        summary(name, [r for r in rows if not r["clock"]])
    out = Path(sys.argv[2]).parent / "bench_results.json"
    json.dump(results, open(out, "w")); print("rows:", out)


if __name__ == "__main__":
    main()
