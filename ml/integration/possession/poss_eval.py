"""Possession: merge the two LLM passes per second, then score (pre-registered).
merge: seconds where A and B agree are truth; disagreeing runs longer than 2 s go to a third look
(third.json: clip -> list of {start, end, team}), shorter runs (change times) are left out.
score per method, on truth seconds with a team: correct (None counts wrong), coverage, precision;
on truth "none" seconds: share given a team. «klar besser» (combined vs position): correct at
least 10 points higher, 20 s block bootstrap 95 % CI above 0, false share on "none" seconds not
more than 10 points higher.
usage: POSS_DIR=... python poss_eval.py merge|score"""

import collections
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import poss_methods as m

D = Path(os.environ["POSS_DIR"])  # poss/ with passA, passB, passC
WO = Path(os.environ["SHOT_LOC_DIR"]) / "wo"
N_S = 609
MAP = {"yellow": "home", "red": "away", "none": "none"}


def secs(segs):
    out = [None] * N_S
    for s in segs:
        for t in range(N_S):
            if s["start"] <= t + 0.5 < s["end"]:
                out[t] = MAP[s["team"]]
    return out


def merge():
    third = (
        json.loads((D / "passC/third.json").read_text())
        if (D / "passC/third.json").exists()
        else None
    )
    truth, todo = {}, {}
    for h in ("h1", "h2"):
        a = secs(json.loads((D / f"passA/{h}.json").read_text()))
        b = secs(json.loads((D / f"passB/{h}.json").read_text()))
        tr = [x if x == y else None for x, y in zip(a, b, strict=True)]
        runs, t = [], 0
        while t < N_S:
            if a[t] != b[t]:
                u = t
                while u < N_S and a[u] != b[u]:
                    u += 1
                if u - t > 2:
                    runs.append([t, u])
                t = u
            else:
                t += 1
        todo[h] = runs
        if third is not None:
            c = secs(third.get(h, []))
            for t0, t1 in runs:
                for t in range(t0, t1):
                    if c[t] is not None and c[t] in (a[t], b[t]):
                        tr[t] = c[t]
        truth[h] = tr
        print(
            h, "agree", sum(x == y for x, y in zip(a, b, strict=True)), "of", N_S, "runs>2s", runs
        )
    (D / "third_todo.json").write_text(json.dumps(todo))
    if third is not None:
        raw = json.dumps(truth, sort_keys=True).encode()
        (D / "truth.json").write_bytes(raw)
        (D / "truth.sha256").write_text(hashlib.sha256(raw).hexdigest() + "  truth.json\n")
        print("frozen", hashlib.sha256(raw).hexdigest())


def score():
    raw = (D / "truth.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == (D / "truth.sha256").read_text().split()[0]
    truth = json.loads(raw)
    rows = []  # (clip, t, truth, {method: pred})
    for h, tr in truth.items():
        pred = m.per_second(WO / f"out_{h}", N_S)
        rows += [
            (h, t, tr[t], {k: v[t] for k, v in pred.items()})
            for t in range(N_S)
            if tr[t] is not None
        ]
    res = {
        "truth_sha256": hashlib.sha256(raw).hexdigest(),
        "seconds": len(rows),
        "truth_counts": dict(collections.Counter(r[2] for r in rows)),
    }
    team = [r for r in rows if r[2] != "none"]
    none = [r for r in rows if r[2] == "none"]
    for k in ("position", "ball", "combined"):
        cov = [r[3][k] is not None for r in team]
        ok = [r[3][k] == r[2] for r in team]
        prec = [r[3][k] == r[2] for r in team if r[3][k] is not None]
        res[k] = {
            "correct": round(float(np.mean(ok)), 3),
            "coverage": round(float(np.mean(cov)), 3),
            "precision": round(float(np.mean(prec)), 3),
            "team_on_none": round(float(np.mean([r[3][k] is not None for r in none])), 3)
            if none
            else None,
        }
    blocks = collections.defaultdict(list)
    for r in team:
        blocks[(r[0], r[1] // 20)].append((r[3]["combined"] == r[2]) - (r[3]["position"] == r[2]))
    keys = list(blocks)
    rng = np.random.default_rng(0)
    boots = []
    for _ in range(2000):
        pick = [keys[i] for i in rng.integers(0, len(keys), len(keys))]
        v = [x for k in pick for x in blocks[k]]
        boots.append(np.mean(v))
    diff = res["combined"]["correct"] - res["position"]["correct"]
    ci = [round(float(np.percentile(boots, 2.5)), 3), round(float(np.percentile(boots, 97.5)), 3)]
    res["combined_minus_position"] = {"correct": round(diff, 3), "ci95": ci}
    tn = (res["combined"]["team_on_none"] or 0) - (res["position"]["team_on_none"] or 0)
    res["klar_besser"] = bool(diff >= 0.10 and ci[0] > 0 and tn <= 0.10)
    print(json.dumps(res, indent=1))
    (D / "poss_eval.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    {"merge": merge, "score": score}[sys.argv[1]]()
