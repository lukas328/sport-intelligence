"""Gold v1 evaluation of the shippable tracker (no OWLv2) and of its confidence ("don't know").

    PYTHONPATH=packages/vision python ml/gold/tracker_eval_conf.py PRE_A PRE_B
PRE_A, PRE_B: merged prelabel outputs of two nets (hr1, hrp1: net top 5 every frame plus OWLv2 from
the round-8 gold run); their net candidates are merged within 8 px with the mean score.

Reports, each with a 95 % interval from a bootstrap over the 42 clips (2 000 resamples):
1. hit rate (12 px) over all / fast / 50-60 fps gold balls: with OWLv2; without OWLv2 and the
   rescoring learned with OWLv2 (the number before the no-OWLv2 weights); without OWLv2 and the
   no-OWLv2 weights (shippable); paired against the line before; ablations of the repeated-frame
   step and the fast-ball gaps without OWLv2;
2. precision and recall over confidence thresholds: recall = hits / labelled ball frames; precision =
   hits / output points on labelled frames (ball frames and the "out" frames, a point there is
   false); the threshold for 95 % and 90 % precision is chosen on one half of the clips and applied
   to the other (2-fold by clip, both ways), so the reported operating point is held out.
"""

import copy
import json
import math
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from eval_ball import gold_points  # noqa: E402
from tracker import Params, track_clip, track_clip_conf  # noqa: E402

GOLD = json.loads((HERE / "data" / "gold_ball_v1.json").read_text())["clips"]
B = 2000


def ensemble(pa: dict, pb: dict) -> dict:
    out = copy.deepcopy(pb)
    for cid in out:
        for i, r in enumerate(out[cid]["pre"]):
            merged = []
            for lst in (pa[cid]["pre"][i]["net"], pb[cid]["pre"][i]["net"]):
                for x, y, s in lst:
                    for o in merged:
                        if math.hypot(o[0] - x, o[1] - y) <= 8:
                            o[2] += s
                            break
                    else:
                        merged.append([x, y, s])
            r["net"] = sorted(([x, y, s / 2] for x, y, s in merged), key=lambda v: -v[2])[:5]
    return out


def no_owl(pre: dict) -> dict:
    out = copy.deepcopy(pre)
    for c in out.values():
        for r in c["pre"]:
            r.pop("owl", None)
    return out


def labelled(cid: str) -> tuple[list, list]:
    balls = gold_points(GOLD[cid])
    outs = [lab["frame"] for lab in GOLD[cid]["labels"] if lab["x"] is None and lab.get("state") == "out"]
    return balls, outs


def hits(pre: dict, p: Params) -> dict:
    """clip -> list of (hit, fast, high_fps) per gold ball."""
    res = {}
    for cid in GOLD:
        tr = track_clip(pre[cid], p)
        hi = GOLD[cid]["fps"] >= 48
        res[cid] = [(bool(tr[b["frame"]] and math.hypot(tr[b["frame"]][0] - b["x"], tr[b["frame"]][1] - b["y"]) <= 12),
                     b["fast"], hi) for b in labelled(cid)[0]]
    return res


def rate(per: dict, ids: list, sel) -> float:
    n = h = 0
    for c in ids:
        for v in per[c]:
            if sel(v):
                n += 1
                h += v[0]
    return h / n if n else float("nan")


def boot(per: dict, sel, rnd: random.Random) -> tuple[float, float, float]:
    ids = list(per)
    est = rate(per, ids, sel)
    vals = sorted(rate(per, [rnd.choice(ids) for _ in ids], sel) for _ in range(B))
    vals = [v for v in vals if v == v]
    return est, vals[int(0.025 * len(vals))], vals[int(0.975 * len(vals)) - 1]


def sign_p(a: int, b: int) -> float:
    n, k = a + b, min(a, b)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n) if n else 1.0


def paired(new: dict, old: dict, rnd: random.Random) -> str:
    w = sum(x[0] and not y[0] for c in new for x, y in zip(new[c], old[c]))
    lose = sum(y[0] and not x[0] for c in new for x, y in zip(new[c], old[c]))
    ids = list(new)
    diffs = []
    for _ in range(B):
        s = [rnd.choice(ids) for _ in ids]
        diffs.append(rate(new, s, lambda v: True) - rate(old, s, lambda v: True))
    diffs.sort()
    return f"+{w} / -{lose} (sign p {sign_p(w, lose):.2g}), difference 95 % [{100 * diffs[50]:+.1f}, {100 * diffs[1949]:+.1f}] points"


def fmt(t: tuple) -> str:
    return f"{100 * t[0]:.1f} % [{100 * t[1]:.1f}, {100 * t[2]:.1f}]"


def conf_rows(pre: dict, p: Params) -> dict:
    """clip -> list of (conf, kind) per labelled frame with an output point; kind 1 hit, 0 false;
    and the number of labelled ball frames."""
    res = {}
    for cid in GOLD:
        out, conf = track_clip_conf(pre[cid], p)
        balls, outs = labelled(cid)
        rows = []
        for b in balls:
            q = out[b["frame"]]
            if q is not None:
                rows.append((conf[b["frame"]], int(math.hypot(q[0] - b["x"], q[1] - b["y"]) <= 12)))
        for f in outs:
            if f < len(out) and out[f] is not None:
                rows.append((conf[f], 0))
        res[cid] = (rows, len(balls))
    return res


def pr(res: dict, ids: list, thr: float) -> tuple[float, float]:
    tp = fp = nb = 0
    for c in ids:
        rows, n = res[c]
        nb += n
        for cf, ok in rows:
            if cf >= thr:
                tp += ok
                fp += 1 - ok
    return (tp / (tp + fp) if tp + fp else 1.0), tp / nb


def thr_for(res: dict, ids: list, target: float) -> float:
    for thr in [i / 100 for i in range(0, 100)]:
        if pr(res, ids, thr)[0] >= target:
            return thr
    return 1.0


def main() -> None:
    pa = json.loads(Path(sys.argv[1]).read_text())["clips"]
    pb = json.loads(Path(sys.argv[2]).read_text())["clips"]
    ens = ensemble(pa, pb)
    noowl = no_owl(ens)
    rnd = random.Random(0)
    sels = {"all": lambda v: True, "fast": lambda v: v[1], "50/60 fps": lambda v: v[2]}
    runs = {
        "with OWLv2": (ens, Params()),
        "no OWLv2, OWLv2-trained weights": (noowl, Params(rescore_w="owl")),
        "no OWLv2, no-OWLv2 weights (shippable)": (noowl, Params()),
        "  same, without repeated-frame step": (noowl, Params(dup_max=0)),
        "  same, without fast-ball gaps": (noowl, Params(gap_fast=2)),
    }
    per = {}
    print("1. Hit rate, gold v1, hr1 + hrp1, 12 px, 95 % clip bootstrap")
    for name, (pre, p) in runs.items():
        per[name] = hits(pre, p)
        print(f"{name:42s}", " | ".join(f"{k} {fmt(boot(per[name], s, rnd))}" for k, s in sels.items()))
    ship = "no OWLv2, no-OWLv2 weights (shippable)"
    print("paired shippable vs OWLv2-trained weights (net only):", paired(per[ship], per["no OWLv2, OWLv2-trained weights"], rnd))
    print("paired shippable vs without repeated-frame step:", paired(per[ship], per["  same, without repeated-frame step"], rnd))
    print("paired shippable vs without fast-ball gaps:", paired(per[ship], per["  same, without fast-ball gaps"], rnd))

    print("\n2. Confidence: precision / recall over thresholds (all labelled frames)")
    ids = sorted(GOLD)
    half = [ids[0::2], ids[1::2]]
    for name, (pre, p) in (("no OWLv2 (shippable)", (noowl, Params())), ("with OWLv2", (ens, Params()))):
        res = conf_rows(pre, p)
        nout = sum(len(labelled(c)[1]) for c in ids)
        print(f"{name}: {sum(n for _, n in res.values())} ball frames, {nout} out frames")
        for thr in (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7):
            P, R = pr(res, ids, thr)
            print(f"  thr {thr:.1f}: precision {100 * P:.1f} %, recall {100 * R:.1f} %")
        for target in (0.95, 0.90):
            hp = hr = 0.0
            for a, b in ((0, 1), (1, 0)):
                t = thr_for(res, half[a], target)
                P, R = pr(res, half[b], t)
                print(f"  target {target:.0%}: threshold {t:.2f} from half {a}, held out on half {b}: precision {100 * P:.1f} %, recall {100 * R:.1f} %")
                hp += P / 2
                hr += R / 2
            t_all = thr_for(res, ids, target)
            bp, br = [], []
            for _ in range(B):
                s = [rnd.choice(ids) for _ in ids]
                P, R = pr(res, s, t_all)
                bp.append(P)
                br.append(R)
            bp.sort()
            br.sort()
            print(f"  target {target:.0%}: held-out mean precision {100 * hp:.1f} %, recall {100 * hr:.1f} %; "
                  f"at threshold {t_all:.2f} (all clips) precision 95 % [{100 * bp[50]:.1f}, {100 * bp[1949]:.1f}], "
                  f"recall [{100 * br[50]:.1f}, {100 * br[1949]:.1f}]")


if __name__ == "__main__":
    main()
