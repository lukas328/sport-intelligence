"""Tor-Kandidaten, Stufe 2 auf Dev (2026-11-26): does a second-stage classifier on the people and
camera signals around a candidate sort real goals above false alarms better than today's template
score? Audit 2026-11 point 3 (`docs/plans/produkt-audit-2026-11.md`).

Usage:
  uv run --project packages/vision --with scikit-learn python ml/integration/goal_stage2_dev.py \
      FEATS.pkl --out R.json

FEATS.pkl: output of `shot_time_dev.py extract` (49 dev segments of 13 games, signals and no-play
mask per segment). Candidates: today's goal candidates (`goalcandidates.score` and `pick`, all up to
rate 4, no-play masked). A candidate is a goal when an official log goal lies within peak - 3 s to
peak + 8 s (as in `goal_ball_cues.py`). Features per candidate: the score, and the five signals
(pan, cx_v, vx, speed, spread) as 2 s means from 10 s before to 30 s after the peak (after a goal
the play turns, players walk back and line up for the throw-off). Models trained leave one game
out, scored by AUC and by goals found / precision when each segment keeps 1, 1.5 or 2 candidates
per playing minute, as in the ball-path test. Bootstrap over games for the difference.

The end test (ml/gold/shot_endtest_*) is never read. The answers coaches give in «Prüfen» are the
intended labels for the product; this only tells whether the signals carry anything beyond the
score before such a stage is built.
"""

# ruff: noqa: N803, N806  (matrix names as in the maths: X, G)
from __future__ import annotations

import argparse
import json
import pickle
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from handball_vision import goalcandidates as gc

GOALS = ("goal", "penalty_goal", "empty_goal")
HIT = (-3.0, 8.0)
CH = ("pan", "cx_v", "vx", "speed", "spread")
BINS = np.arange(-10.0, 30.0, 2.0)


def candidates(feats: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    tmpl = gc.load_template()
    rows, meta = [], {}
    for seg, v in feats.items():
        s = {"t": v["t"], **v["signals"]}
        sc = gc.score(s, tmpl)
        found = gc.pick(s["t"], sc, rates=(1, 2, 4), play=~v["idle"])
        goals = [e["t"] for e in v["entries"] if e["kind"] in GOALS]
        meta[seg] = {
            "game": v["game"],
            "goals": goals,
            "play_s": float((~v["idle"]).sum() * gc.DT),
        }
        t = v["t"]
        for c in found:
            x = [c.score]
            for ch in CH:
                sig = np.asarray(v["signals"][ch], float)
                for b in BINS:
                    m = (t >= c.t + b) & (t < c.t + b + 2.0)
                    x.append(
                        float(np.nanmean(sig[m]))
                        if m.any() and np.isfinite(sig[m]).any()
                        else np.nan
                    )
            g = next((g for g in goals if HIT[0] <= c.t - g <= HIT[1]), None)
            rows.append({"seg": seg, "game": v["game"], "t": c.t, "x": x, "goal": g})
    return rows, meta


def logo(model: Any, X: np.ndarray, y: np.ndarray, games: np.ndarray) -> np.ndarray:
    out = np.zeros(len(y))
    for g in np.unique(games):
        tr, te = games != g, games == g
        Xt = X[tr]
        med = np.nanmedian(Xt, 0)
        m = model()
        m.fit(np.where(np.isnan(Xt), med, Xt), y[tr])
        Xe = X[te]
        out[te] = m.predict_proba(np.where(np.isnan(Xe), med, Xe))[:, 1]
    return out


def quota(
    rows: list[dict], meta: dict, s: np.ndarray, rate: float, segs: list[str]
) -> tuple[int, int, int, int]:
    found = n = tp = goals = 0
    for seg in segs:
        idx = [i for i, r in enumerate(rows) if r["seg"] == seg]
        k = round(rate * meta[seg]["play_s"] / 60)
        keep = sorted(idx, key=lambda i: -s[i])[:k]
        n += len(keep)
        tp += sum(rows[i]["goal"] is not None for i in keep)
        found += len({rows[i]["goal"] for i in keep if rows[i]["goal"] is not None})
        goals += len(meta[seg]["goals"])
    return found, goals, tp, n


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("feats", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    feats = pickle.loads(a.feats.read_bytes())  # noqa: S301 (own file from shot_time_dev extract)
    rows, meta = candidates(feats)
    X = np.array([r["x"] for r in rows], float)
    y = np.array([r["goal"] is not None for r in rows], int)
    games = np.array([r["game"] for r in rows])
    scores = {
        "score": X[:, 0],
        "logreg": logo(
            lambda: make_pipeline(StandardScaler(), LogisticRegression(C=0.05, max_iter=2000)),
            X,
            y,
            games,
        ),
        "boosting": logo(
            lambda: HistGradientBoostingClassifier(
                max_depth=3, learning_rate=0.05, max_iter=200, l2_regularization=1.0, random_state=0
            ),
            X,
            y,
            games,
        ),
    }
    gl = sorted(set(games))
    seg_of = {g: [s for s, m in meta.items() if m["game"] == g] for g in gl}
    res: dict[str, Any] = {
        "segments": len(meta),
        "games": len(gl),
        "goals": sum(len(m["goals"]) for m in meta.values()),
        "candidates": len(rows),
        "true": int(y.sum()),
    }
    rng = np.random.default_rng(0)
    picks = [rng.integers(0, len(gl), len(gl)) for _ in range(2000)]
    for name, s in scores.items():
        row: dict[str, Any] = {"auc": round(float(roc_auc_score(y, s)), 3)}
        for rate in (1, 1.5, 2):
            f, G, tp, n = quota(rows, meta, s, rate, list(meta))
            row[f"at_{rate}"] = {
                "found": round(f / G, 3),
                "precision": round(tp / max(n, 1), 3),
                "n": n,
            }
        res[name] = row
    # paired bootstrap over games: found and precision at 2/min, model minus score
    per_game = {
        name: {g: quota(rows, meta, s, 2, seg_of[g]) for g in gl} for name, s in scores.items()
    }
    for name in ("logreg", "boosting"):
        dprec, dfound = [], []
        for p in picks:
            sel = [gl[i] for i in p]
            agg = {k: np.sum([per_game[k][g] for g in sel], 0) for k in ("score", name)}
            dfound.append(agg[name][0] / agg[name][1] - agg["score"][0] / agg["score"][1])
            dprec.append(agg[name][2] / agg[name][3] - agg["score"][2] / agg["score"][3])
        res[f"{name} - score at 2"] = {
            "found_ci95": [round(float(v), 3) for v in np.percentile(dfound, [2.5, 97.5])],
            "precision_ci95": [round(float(v), 3) for v in np.percentile(dprec, [2.5, 97.5])],
        }
    out = json.dumps(res, indent=1)
    print(out)
    a.out.write_text(out)


if __name__ == "__main__":
    main()
