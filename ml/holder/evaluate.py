"""Evaluate holder-classifier predictions (train.py's pred.json) on the held-out data.

Per evaluation set (held-out path scenes / benchmark single frames) and per hall:
  auc        crop-level ROC AUC, holder vs. every other player in frames with a holder
  top        frames with a holder: the holder is the top-scoring player
  top@thr    ... and its score is above the threshold (what a pipeline would accept)
  free_fp    frames whose ball is free (in no box): top score above the threshold (false holder)
  biggest    baseline: the holder is the largest box in the frame
usage: evaluate.py <data dir> <pred.json> [<pred.json> ...] [--thr 0.5] [--md]
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("data")
ap.add_argument("preds", nargs="+")
ap.add_argument("--thr", type=float, default=0.5)
ap.add_argument("--md", action="store_true")
args = ap.parse_args()
D = Path(args.data)
meta = {m["file"]: m for m in json.load(open(D / "meta.json"))}


def auc(pos, neg):
    if not len(pos) or not len(neg):
        return float("nan")
    pos, neg = np.array(pos)[:, None], np.array(neg)[None]
    return float((pos > neg).mean() + 0.5 * (pos == neg).mean())


def metrics(rows, thr):
    by = defaultdict(list)
    for m, p in rows:
        by[m["frame"]].append((p, m["y"], m["box_h"]))
    hold = [v for v in by.values() if any(y for _, y, _ in v)]
    free = [v for v in by.values() if not any(y for _, y, _ in v)]
    pos = [p for m, p in rows if m["y"] and m["frame"] in {k for k, v in by.items() if any(y for _, y, _ in v)}]
    neg = [p for m, p in rows if not m["y"] and any(y for _, y, _ in by[m["frame"]])]
    top = [max(v)[1] == 1 for v in hold]
    topt = [max(v)[1] == 1 and max(v)[0] > thr for v in hold]
    big = [max(v, key=lambda r: r[2])[1] == 1 for v in hold]
    fp = [max(v)[0] > thr for v in free]
    return {
        "hold": len(hold),
        "free": len(free),
        "auc": auc(pos, neg),
        "top": np.mean(top) if top else float("nan"),
        "top@thr": np.mean(topt) if topt else float("nan"),
        "free_fp": np.mean(fp) if fp else float("nan"),
        "biggest": np.mean(big) if big else float("nan"),
    }


def fmt(name, r):
    f = lambda v: "  -  " if v != v else f"{v:.2f}"  # noqa: E731
    cells = [name, str(r["hold"]), str(r["free"]), f(r["auc"]), f(r["top"]), f(r["top@thr"]), f(r["free_fp"]), f(r["biggest"])]
    if args.md:
        return "| " + " | ".join(cells) + " |"
    return f"{cells[0]:34s}" + "".join(f"{c:>9s}" for c in cells[1:])


head = ["set / hall", "hold fr", "free fr", "AUC", "top", f"top@{args.thr}", "free FP", "biggest"]
for pf in args.preds:
    pred = json.load(open(pf))
    rows = [(meta[r["file"]], r["p"]) for r in pred]
    print(f"\n{pf}")
    print("| " + " | ".join(head) + " |\n|" + "---|" * len(head) if args.md else f"{head[0]:34s}" + "".join(f"{c:>9s}" for c in head[1:]))
    for setname, sel in (("held-out scenes", "path"), ("benchmark single test", "single")):
        rs = [r for r in rows if r[0]["src"] == sel]
        print(fmt(f"**{setname}**" if args.md else setname, metrics(rs, args.thr)))
        for hall in sorted({m["hall"] for m, _ in rs}):
            print(fmt(f"  {hall}", metrics([r for r in rs if r[0]["hall"] == hall], args.thr)))
    print(fmt("**all held-out**" if args.md else "all held-out", metrics(rows, args.thr)))
