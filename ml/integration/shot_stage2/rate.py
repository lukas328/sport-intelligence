import collections
import json
import pickle
import sys
from pathlib import Path

import numpy as np


def _load(path: Path) -> list:
    with path.open("rb") as fh:
        return pickle.load(fh)  # noqa: S301 (our own feature files)


segs = [r for f in sorted(Path(sys.argv[1]).glob("feats_*.pkl")) for r in _load(f)]
marks = json.loads(Path(sys.argv[2]).read_text())["shots"]
by = collections.defaultdict(list)
for m in marks:
    if m["t_s"] is not None:
        by[m["seg"]].append(m)


def game(s):
    return s.rsplit("_s", 1)[0]


def match(cands, ms):
    """Greedy nearest pairs of candidates (estimate: peak minus 5 s) and marks within 2 s."""
    pairs = sorted(
        (abs(x["peak"] - 5 - m["t_s"]), i, j) for i, x in enumerate(cands) for j, m in enumerate(ms)
    )
    used_c, used_m = set(), set()
    for dd, i, j in pairs:
        if dd > 2:
            break
        if i in used_c or j in used_m:
            continue
        used_c.add(i)
        used_m.add(j)
    return used_c, used_m


def interval(d, n=2000):
    """95 % bootstrap interval over games of sum(hits) / sum(total)."""
    rng = np.random.default_rng(0)
    games = list(d)
    v = []
    for _ in range(n):
        p = [games[k] for k in rng.integers(0, len(games), len(games))]
        v.append(sum(d[x][0] for x in p) / max(1, sum(d[x][1] for x in p)))
    return [round(100 * np.percentile(v, 2.5), 1), round(100 * np.percentile(v, 97.5), 1)]


for R in (2, 4):
    rec = collections.defaultdict(lambda: [0, 0])
    prec = collections.defaultdict(lambda: [0, 0])
    for r in segs:
        c = [x for x in r["cands"] if x["kind"] == "shot" and x["rate"] <= R]
        ok = [m for m in by[r["seg"]] if m["status"] == "ok"]
        allm = by[r["seg"]]
        g = game(r["seg"])

        _, mj = match(c, ok)
        rec[g][0] += len(mj)
        rec[g][1] += len(ok)
        kept, _ = match(c, allm)
        prec[g][0] += len(kept)
        prec[g][1] += len(c)

    def tot(d):
        return sum(v[0] for v in d.values()) / sum(v[1] for v in d.values())

    print(
        R,
        "recall",
        round(100 * tot(rec), 1),
        interval(rec),
        "precision",
        round(100 * tot(prec), 1),
        interval(prec),
    )
