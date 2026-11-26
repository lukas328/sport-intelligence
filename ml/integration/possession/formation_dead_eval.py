# ruff: noqa: S301, N806
"""«Kein Besitz» from the throw-off formation, the throw-off event and an empty court, scored on
the frozen possession truth (LLM labels). Rules fixed before any comparison with the labels
(docs/plans/produkt-analyse-integration.md, «Kein Besitz aus Anwurf-Formation»):
  A  formation: >= 4 field players per team on court and >= 80 % of each team in its own half
     (side from events.detect), for >= 3 s in a row
  E  the 15 s before each throw_off event of the product
  L  fewer than half the clip's usual field players (median per second) on court, >= 5 s in a row
  H  main rule = A or E or L
«klarer Gewinn»: accuracy over all seconds at least 5 points higher than the position rule alone,
20 s block bootstrap 95 % CI above 0, correct on team seconds at most 2 points lower, and better in
each half on its own.
usage: POSS_DIR=... SHOT_LOC_DIR=... python formation_dead_eval.py"""

import collections
import hashlib
import json
import os
import pickle
import sys
from pathlib import Path

import numpy as np

from handball_vision.events import detect

sys.path.insert(0, str(Path(__file__).parent))
import poss_methods as m

D = Path(os.environ["POSS_DIR"])
WO = Path(os.environ["SHOT_LOC_DIR"]) / "wo"
N_S = 609


def runs(flags, min_len):
    out = [False] * len(flags)
    k = 0
    while k < len(flags):
        if flags[k]:
            j = k
            while j < len(flags) and flags[j]:
                j += 1
            if j - k >= min_len:
                out[k:j] = [True] * (j - k)
            k = j
        else:
            k += 1
    return out


def signals(h):
    with (WO / f"out_{h}" / "trk.pkl").open("rb") as fh:
        d = pickle.load(fh)
    fps = d["fps"]
    lab = {t: str(v.get("label")) for t, v in d["teams"].items()}
    pts = [(round(f * 1000 / fps), tid, x, y) for f, tid, x, y, _, _ in d["points"]]
    ev = detect(pts, lab)
    sides = ev.sides

    def home_left(ms):
        cur = None
        for t0, side in sides:
            if t0 <= ms:
                cur = side
        return None if cur is None else cur == "left"

    per = collections.defaultdict(dict)  # second -> track -> (x, y)
    for f, tid, x, y, _, obs in d["points"]:
        if obs and lab.get(tid) in ("home", "away"):
            per[int(f / fps)].setdefault(tid, (x, y))
    on_court = [0] * N_S
    form = [False] * N_S
    for s in range(N_S):
        ps = per.get(s, {})
        court = {t: p for t, p in ps.items() if 0 <= p[0] <= 40 and 0 <= p[1] <= 20}
        on_court[s] = len(court)
        hl = home_left((s + 0.5) * 1000)
        if hl is None:
            continue
        ok = True
        for team in ("home", "away"):
            xs = [p[0] for t, p in court.items() if lab[t] == team]
            if len(xs) < 4:
                ok = False
                break
            own_left = hl if team == "home" else not hl
            share = np.mean([(x < 20) == own_left for x in xs])
            ok = ok and share >= 0.8
        form[s] = ok
    usual = float(np.median([n for n in on_court if n > 0])) if any(on_court) else 0.0
    A = runs(form, 3)
    E = [False] * N_S
    for e in ev.events:
        if e.type == "throw_off":
            s1 = int(e.t_ms / 1000)
            for s in range(max(0, s1 - 15), min(N_S, s1)):
                E[s] = True
    L = runs([0 < n < usual / 2 or n == 0 for n in on_court], 5)
    H = [a or b or c for a, b, c in zip(A, E, L, strict=True)]
    return {"A": A, "E": E, "L": L, "H": H}, {
        "usual": usual,
        "throw_offs": sum(1 for e in ev.events if e.type == "throw_off"),
    }


def main():
    raw = (D / "truth.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == (D / "truth.sha256").read_text().split()[0]
    truth = json.loads(raw)
    rows, info = [], {}
    for h, tr in truth.items():
        sig, info[h] = signals(h)
        pos = m.per_second(WO / f"out_{h}", N_S)["position"]
        rows += [
            (h, t, tr[t], {k: v[t] for k, v in sig.items()}, pos[t])
            for t in range(N_S)
            if tr[t] is not None
        ]
    dead = [r[2] == "none" for r in rows]
    out = {"truth_sha256": hashlib.sha256(raw).hexdigest(), "clips": info}

    def acc(rr, k):
        return [
            (
                ((None if (k and r[3][k]) else r[4]) is None)
                if r[2] == "none"
                else ((None if (k and r[3][k]) else r[4]) == r[2])
            )
            for r in rr
        ]

    def team_on_none(rr, k):
        nn = [r for r in rr if r[2] == "none"]
        return float(np.mean([(None if (k and r[3][k]) else r[4]) is not None for r in nn]))

    for k in ("A", "E", "L", "H"):
        p = [r[3][k] for r in rows]
        tp = sum(a and b for a, b in zip(p, dead, strict=True))
        v = acc(rows, k)
        team_idx = [i for i, r in enumerate(rows) if r[2] != "none"]
        out[k] = {
            "flagged": sum(p),
            "precision": round(tp / max(1, sum(p)), 3),
            "recall": round(tp / max(1, sum(dead)), 3),
            "acc_all": round(float(np.mean(v)), 3),
            "correct_team": round(float(np.mean([v[i] for i in team_idx])), 3),
            "team_on_none": round(team_on_none(rows, k), 3),
        }
    base = acc(rows, None)
    team_idx = [i for i, r in enumerate(rows) if r[2] != "none"]
    out["position_alone"] = {
        "acc_all": round(float(np.mean(base)), 3),
        "correct_team": round(float(np.mean([base[i] for i in team_idx])), 3),
        "team_on_none": round(team_on_none(rows, None), 3),
    }
    hv = acc(rows, "H")
    blocks = collections.defaultdict(list)
    for r, a, b in zip(rows, hv, base, strict=True):
        blocks[(r[0], r[1] // 20)].append(int(a) - int(b))
    keys = list(blocks)
    rng = np.random.default_rng(0)
    boots = []
    for _ in range(2000):
        pick = [keys[i] for i in rng.integers(0, len(keys), len(keys))]
        vals = [x for kk in pick for x in blocks[kk]]
        boots.append(float(np.mean(vals)))
    per_half = {}
    for h in truth:
        idx = [i for i, r in enumerate(rows) if r[0] == h]
        per_half[h] = round(
            float(np.mean([hv[i] for i in idx]) - np.mean([base[i] for i in idx])), 3
        )
    diff = float(np.mean(hv) - np.mean(base))
    ci = [round(float(np.percentile(boots, 2.5)), 3), round(float(np.percentile(boots, 97.5)), 3)]
    team_drop = out["position_alone"]["correct_team"] - out["H"]["correct_team"]
    out["H_minus_position"] = {
        "acc_all": round(diff, 3),
        "ci95": ci,
        "team_drop": round(team_drop, 3),
        "per_half": per_half,
    }
    out["klarer_gewinn"] = bool(
        diff >= 0.05 and ci[0] > 0 and team_drop <= 0.02 and all(v > 0 for v in per_half.values())
    )
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
