# ruff: noqa: S301, N806
"""«Ball nicht im Spiel» per second, scored on the frozen possession truth (LLM labels).
Pre-registered (written before any signal was compared with the labels):
  C  clock: the hall-board clock does not run (outside play.json intervals_ms)
  M  motion: 3 s rolling median of the median field-player speed < MOTION_MS
  N  product: goal_candidates no_play_ms (parked / bunched / warm-up / clock breaks)
  D  primary rule = C or M
Scores: precision / recall of "dead" against truth "none"; effect on possession: position rule
with dead seconds set to None, accuracy over ALL truth seconds (a dead second is right when None).
«klarer Gewinn» (D): accuracy over all seconds at least 5 points higher than the position rule
alone, 20 s block bootstrap 95 % CI above 0, and correct on team seconds at most 2 points lower.
MOTION_MS = 0.8 is fixed here; 0.6 and 1.0 are reported as sensitivity only."""

import collections
import hashlib
import json
import os
import pickle
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import poss_methods as m

D = Path(os.environ["POSS_DIR"])
WO = Path(os.environ["SHOT_LOC_DIR"]) / "wo"
N_S = 609
MOTION_MS = 0.8


def speeds(d):
    fps = d["fps"]
    lab = {t: str(v.get("label")) for t, v in d["teams"].items()}
    per = collections.defaultdict(dict)  # track -> second -> (x, y) first point in that second
    for f, tid, x, y, _, obs in d["points"]:
        if not obs or lab.get(tid) not in ("home", "away"):
            continue
        s = int(f / fps)
        per[tid].setdefault(s, (x, y))
    sp = collections.defaultdict(list)
    for tr in per.values():
        for s, p in tr.items():
            q = tr.get(s + 1)
            if q is not None:
                sp[s].append(float(np.hypot(q[0] - p[0], q[1] - p[1])))
    med = np.array([np.median(sp[s]) if len(sp[s]) >= 4 else np.nan for s in range(N_S)])
    roll = np.array(
        [
            np.nanmedian(med[max(0, s - 1) : s + 2])
            if not np.all(np.isnan(med[max(0, s - 1) : s + 2]))
            else np.nan
            for s in range(N_S)
        ]
    )
    return roll


def inside(ms_list, t):
    return any(a <= (t + 0.5) * 1000 <= b for a, b in ms_list)


def signals(h, thr=MOTION_MS):
    with (WO / f"out_{h}" / "trk.pkl").open("rb") as fh:
        d = pickle.load(fh)
    play = json.loads((WO / h / "play.json").read_text())["intervals_ms"]
    nop = d["extra"]["goal_candidates"]["no_play_ms"]
    roll = speeds(d)
    C = [not inside(play, t) for t in range(N_S)]
    M = [bool(not np.isnan(roll[t]) and roll[t] < thr) for t in range(N_S)]
    N = [inside(nop, t) for t in range(N_S)]
    return {"C": C, "M": M, "N": N, "D": [a or b for a, b in zip(C, M, strict=True)]}


def main():
    raw = (D / "truth.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == (D / "truth.sha256").read_text().split()[0]
    truth = json.loads(raw)
    res = {"truth_sha256": hashlib.sha256(raw).hexdigest()}
    for thr in (MOTION_MS, 0.6, 1.0):
        rows = []
        for h, tr in truth.items():
            sig = signals(h, thr)
            pos = m.per_second(WO / f"out_{h}", N_S)["position"]
            rows += [
                (h, t, tr[t], {k: v[t] for k, v in sig.items()}, pos[t])
                for t in range(N_S)
                if tr[t] is not None
            ]
        out = {}
        dead = [r[2] == "none" for r in rows]
        for k in ("C", "M", "N", "D"):
            p = [r[3][k] for r in rows]
            tp = sum(a and b for a, b in zip(p, dead, strict=True))
            out[k] = {
                "flagged": sum(p),
                "precision": round(tp / max(1, sum(p)), 3),
                "recall": round(tp / max(1, sum(dead)), 3),
            }

        def acc(rr, k):
            vals = []
            for r in rr:
                pred = None if (k and r[3][k]) else r[4]
                vals.append((pred is None) if r[2] == "none" else (pred == r[2]))
            return vals

        base = acc(rows, None)
        for k in ("C", "M", "N", "D"):
            v = acc(rows, k)
            team_rows = [i for i, r in enumerate(rows) if r[2] != "none"]
            out[k]["acc_all"] = round(float(np.mean(v)), 3)
            out[k]["correct_team"] = round(float(np.mean([v[i] for i in team_rows])), 3)
        out["position_alone"] = {
            "acc_all": round(float(np.mean(base)), 3),
            "correct_team": round(
                float(np.mean([base[i] for i, r in enumerate(rows) if r[2] != "none"])), 3
            ),
        }
        if thr == MOTION_MS:
            dv = acc(rows, "D")
            blocks = collections.defaultdict(list)
            for r, a, b in zip(rows, dv, base, strict=True):
                blocks[(r[0], r[1] // 20)].append(int(a) - int(b))
            keys = list(blocks)
            rng = np.random.default_rng(0)
            boots = []
            for _ in range(2000):
                pick = [keys[i] for i in rng.integers(0, len(keys), len(keys))]
                boots.append(np.mean([x for k in pick for x in blocks[k]]))
            diff = out["D"]["acc_all"] - out["position_alone"]["acc_all"]
            ci = [
                round(float(np.percentile(boots, 2.5)), 3),
                round(float(np.percentile(boots, 97.5)), 3),
            ]
            drop = out["position_alone"]["correct_team"] - out["D"]["correct_team"]
            out["D_minus_position"] = {
                "acc_all": round(diff, 3),
                "ci95": ci,
                "team_drop": round(drop, 3),
            }
            out["klarer_gewinn"] = bool(diff >= 0.05 and ci[0] > 0 and drop <= 0.02)
        res[f"motion_{thr}"] = out
    print(json.dumps(res, indent=1))
    (D / "dead_eval.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
