"""Measure ball methods on the gold standard (ml/gold/data/gold_ball_v1.json).

A method gives at most one point per frame of a clip. A gold point counts as hit when the method's
point in that frame lies within RADIUS px. Usable gold points: tiers owner, sure, track, confirmed.
Subsets: "free" and "held" (gold state), "fast" (the ball moves more than 12 px per frame to the
nearest gold point at most 2 frames away). "out" labels (ball off the picture) count as false
positives when the method gives a point there.

    python ml/gold/eval_ball.py PRE_JSON [--gold ml/gold/data/gold_ball_v1.json] [--radius 12]
PRE_JSON is the prelabel kernel's output (ball net peaks every frame, OWLv2 boxes every 2nd).
"""

import argparse
import json
import math
import sys
from collections.abc import Callable
from pathlib import Path

HERE = Path(__file__).resolve().parent
USABLE = {"owner", "sure", "track", "confirmed"}


def gold_points(clip: dict) -> list[dict]:
    pts = [lab for lab in clip["labels"] if lab["tier"] in USABLE and lab["x"] is not None]
    by = {p["frame"]: p for p in pts}
    for p in pts:
        sp = 0.0
        for d in (1, 2):
            for q in (by.get(p["frame"] - d), by.get(p["frame"] + d)):
                if q:
                    sp = max(sp, math.hypot(q["x"] - p["x"], q["y"] - p["y"]) / d)
            if sp:
                break
        p["fast"] = sp > 12
    return pts


Method = Callable[[dict], list]  # pre clip -> per frame [x, y] or None


def evaluate(pre: dict, gold: dict, methods: dict[str, Method], radius: float, clips=None) -> dict:
    res = {}
    for name, fn in methods.items():
        cnt = {k: [0, 0] for k in ("all", "free", "held", "fast")}
        fp = [0, 0]
        given = [0, 0]
        for cid, g in gold["clips"].items():
            if clips is not None and cid not in clips:
                continue
            out = fn(pre[cid])
            for p in gold_points(g):
                q = out[p["frame"]] if p["frame"] < len(out) else None
                hit = q is not None and math.hypot(q[0] - p["x"], q[1] - p["y"]) <= radius
                for k in ("all", p["state"]) + (("fast",) if p["fast"] else ()):
                    cnt[k][0] += hit
                    cnt[k][1] += 1
                given[0] += q is not None
                given[1] += 1
            for lab in g["labels"]:
                if lab["state"] == "out":
                    q = out[lab["frame"]] if lab["frame"] < len(out) else None
                    fp[0] += q is not None
                    fp[1] += 1
        res[name] = {k: v[0] / max(1, v[1]) for k, v in cnt.items()}
        res[name]["n"] = cnt["all"][1]
        res[name]["given"] = given[0] / max(1, given[1])
        res[name]["out_fp"] = f"{fp[0]}/{fp[1]}"
    return res


def net_top1(c: dict) -> list:
    return [[r["net"][0][0], r["net"][0][1]] if r["net"] else None for r in c["pre"]]


def owl_top1(c: dict) -> list:
    out = []
    for k, r in enumerate(c["pre"]):
        o = r.get("owl") or (c["pre"][k - 1].get("owl") if k else None)
        out.append([o[0][0], o[0][1]] if o else None)
    return out


def balltrack_path(c: dict) -> list:
    sys.path.insert(0, str(HERE))
    from suggest import suggest

    return [s[:2] if s else None for s in suggest(c)]


def table(res: dict) -> str:
    lines = [f"{'method':24} {'all':>6} {'free':>6} {'held':>6} {'fast':>6} {'given':>6}  out_fp"]
    for name, r in res.items():
        lines.append(
            f"{name:24} "
            + " ".join(f"{100 * r[k]:5.1f}%" for k in ("all", "free", "held", "fast", "given"))
            + f"  {r['out_fp']}"
        )
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pre", type=Path)
    ap.add_argument("--gold", type=Path, default=HERE / "data" / "gold_ball_v1.json")
    ap.add_argument("--radius", type=float, default=12.0)
    a = ap.parse_args()
    pre = json.load(open(a.pre))["clips"]
    gold = json.load(open(a.gold))
    sys.path.insert(0, str(HERE))
    from tracker import track_clip

    res = evaluate(
        pre,
        gold,
        {
            "net top-1": net_top1,
            "owl top-1": owl_top1,
            "balltrack (product)": balltrack_path,
            "tracker v2": track_clip,
        },
        a.radius,
    )
    print(table(res))


if __name__ == "__main__":
    main()
