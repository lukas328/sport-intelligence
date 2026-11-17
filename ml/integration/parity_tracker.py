"""Parity of the product ball tracker (`handball_vision.balltrack2`) with the research tracker
(`ml/gold/tracker.py`, no OWLv2) on gold v1, plus product variants (docs/plans/
produkt-analyse-integration.md step 2):

- research: `track_clip` on the hr1 + hrp1 ensemble without OWLv2 (the 80.0 % headline);
- product: `balltrack2.track` on the same candidates (must give the same points);
- product, windows: `track_windows` (8 s windows; gold clips are 8 s, so nearly the same);
- every 2nd frame: the net only on every 2nd frame, the tracker on that half-rate sequence, the
  other frames filled linearly between neighbouring points (cost saving, step 4);
- single nets hr1 or hrp1 only.

    uv run python ml/integration/parity_tracker.py PRE_HR1 PRE_HRP1
PRE_*: the gold prelabel outputs of kernels handball-gold-hr1 / handball-gold-hrp1 (pre.json).
"""

import json
import math
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
GOLD_DIR = HERE.parent / "gold"
sys.path.insert(0, str(GOLD_DIR))
from eval_ball import gold_points  # noqa: E402
from tracker import track_clip  # noqa: E402
from tracker_eval_conf import ensemble, no_owl  # noqa: E402

from handball_vision import balltrack2  # noqa: E402

GOLD = json.loads((GOLD_DIR / "data" / "gold_ball_v1.json").read_text())["clips"]


def peaks_of(c):
    return [[tuple(v) for v in r["net"]] for r in c["pre"]]


def fps_of(c):
    return c.get("fps_read", c.get("fps", 30))


def half_rate(c, merge=None):
    """Net on every 2nd frame only: track at half rate, fill the frames in between."""
    pk = peaks_of(c)[::2]
    o, _ = balltrack2.track(pk, fps_of(c) / 2, c["w"])
    n = len(c["pre"])
    out = [None] * n
    for i, q in enumerate(o):
        out[2 * i] = q
    for t in range(1, n, 2):
        a = out[t - 1]
        b = out[t + 1] if t + 1 < n else None
        if a is not None and b is not None:
            out[t] = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    return out


def score(paths):
    per = {}
    for cid, g in GOLD.items():
        tr = paths[cid]
        hi = g["fps"] >= 48
        per[cid] = []
        for b in gold_points(g):
            q = tr[b["frame"]] if b["frame"] < len(tr) else None
            hit = bool(q is not None and math.hypot(q[0] - b["x"], q[1] - b["y"]) <= 12)
            per[cid].append((hit, b["fast"], hi))
    return per


def rate(per, ids, sel):
    n = h = 0
    for c in ids:
        for v in per[c]:
            if sel(v):
                n += 1
                h += v[0]
    return h / n if n else float("nan")


def report(name, per, boot=2000):
    ids = sorted(per)
    rnd = random.Random(0)
    cols = []
    for sel in (lambda v: True, lambda v: v[1], lambda v: v[2]):
        r = rate(per, ids, sel)
        bs = sorted(rate(per, [rnd.choice(ids) for _ in ids], sel) for _ in range(boot))
        cols.append(
            f"{100 * r:5.1f} % [{100 * bs[int(0.025 * boot)]:.1f}, {100 * bs[int(0.975 * boot) - 1]:.1f}]"
        )
    print(f"{name:34} " + "  ".join(cols), flush=True)


def main():
    pa = json.loads(Path(sys.argv[1]).read_text())["clips"]
    pb = json.loads(Path(sys.argv[2]).read_text())["clips"]
    ens = no_owl(ensemble(pa, pb))
    print(f"{'variant':34} {'all':>22}  {'fast':>22}  {'50/60 fps':>22}")
    research = {cid: track_clip(ens[cid]) for cid in GOLD}
    report("research tracker (no OWLv2)", score(research))
    product = {
        cid: balltrack2.track(peaks_of(ens[cid]), fps_of(ens[cid]), ens[cid]["w"])[0]
        for cid in GOLD
    }
    same = sum(
        (a is None and b is None)
        or (a is not None and b is not None and math.hypot(a[0] - b[0], a[1] - b[1]) < 1e-6)
        for cid in GOLD
        for a, b in zip(research[cid], product[cid], strict=True)
    )
    total = sum(len(research[cid]) for cid in GOLD)
    report("product balltrack2.track", score(product))
    print(f"  identical points: {same} / {total}")
    win = {
        cid: balltrack2.track_windows(peaks_of(ens[cid]), fps_of(ens[cid]), ens[cid]["w"])[0]
        for cid in GOLD
    }
    report("product track_windows (8 s)", score(win))
    report("net every 2nd frame", score({cid: half_rate(ens[cid]) for cid in GOLD}))
    for name, single in (("hr1 only", pa), ("hrp1 only", pb)):
        s = no_owl(single)
        report(
            name,
            score(
                {
                    cid: balltrack2.track(peaks_of(s[cid]), fps_of(s[cid]), s[cid]["w"])[0]
                    for cid in GOLD
                }
            ),
        )
        report(name + ", every 2nd frame", score({cid: half_rate(s[cid]) for cid in GOLD}))


if __name__ == "__main__":
    main()
