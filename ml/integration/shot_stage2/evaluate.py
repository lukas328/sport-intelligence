"""Second stage for the shot and goal candidates on Dev (2026-11-26), leave one game out.

    uv run --with scikit-learn python ml/integration/shot_stage2/evaluate.py FEATS_DIR \
        ml/gold/data/shot_release_dev_llm.json goal|shot MAXRATE

FEATS_DIR holds feats_*.pkl from feats.py (49 dev segments). A candidate is right when a release
mark (any status; without t_s the log time minus 3.9 s) lies within 2 s of its estimate (peak minus
5 s). Window recall: sure marks with a kept candidate whose peak lies 3 s before to 12 s after the
release. Per held-out game the threshold comes from the training games: the highest that keeps at
least 95 % of their window recall. Compared: today's list, a higher score threshold alone, logistic
regression and gradient boosting on score plus the people features. End test never read.
"""

import collections
import json
import pickle
import sys
from pathlib import Path

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score


def _load(path: Path) -> list:
    with path.open("rb") as fh:
        return pickle.load(fh)  # noqa: S301 (our own feature files)


segs = [r for f in sorted(Path(sys.argv[1]).glob("feats_*.pkl")) for r in _load(f)]
marks = json.loads(Path(sys.argv[2]).read_text())["shots"]
GOAL = ("goal", "penalty_goal", "empty_goal")
by = collections.defaultdict(list)
for m in marks:
    rel = (
        m["t_s"]
        if m["t_s"] is not None
        else (m["log_t"] - 3.9 if m.get("log_t") is not None else None)
    )
    if rel is not None:
        by[m["seg"]].append({**m, "rel": rel})
KIND = sys.argv[3]  # goal | shot
MAXRATE = int(sys.argv[4])
OFF = 5.0


def game(s):
    return s.rsplit("_s", 1)[0]


rows, dur = [], collections.Counter()
for r in segs:
    dur[game(r["seg"])] += r["dur"]
    for c in r["cands"]:
        if c["kind"] != KIND or c["rate"] > MAXRATE:
            continue
        ms = [m for m in by[r["seg"]] if KIND == "shot" or m["kind"] in GOAL]
        est = c["peak"] - OFF
        c = dict(c)
        c["y"] = int(any(abs(est - m["rel"]) <= 2.0 for m in ms))
        rows.append(c)
names = sorted(k for k in rows[0] if k not in ("seg", "kind", "peak", "y", "rate"))
X = np.array([[c[k] for k in names] for c in rows])
y = np.array([c["y"] for c in rows])
g = np.array([game(c["seg"]) for c in rows])
targets = []  # (seg, rel) of sure marks for window recall
for s, ms in by.items():
    for m in ms:
        if m["status"] == "ok" and (KIND == "shot" or m["kind"] in GOAL):
            targets.append((s, m["rel"]))


def window_recall(keep):
    hit = 0
    for s, rel in targets:
        hit += any(
            k and c["seg"] == s and rel - 3 <= c["peak"] <= rel + 12
            for c, k in zip(rows, keep, strict=False)
        )
    return hit / len(targets)


def run(model_fn, feats):
    prob = np.zeros(len(rows))
    keep = np.zeros(len(rows), bool)
    for held_out in sorted(set(g)):
        tr, te = g != held_out, g == held_out
        if feats == "score":
            ptr, pte = X[tr][:, names.index("score")], X[te][:, names.index("score")]
        else:
            m = model_fn().fit(X[tr], y[tr])
            ptr, pte = m.predict_proba(X[tr])[:, 1], m.predict_proba(X[te])[:, 1]
        prob[te] = pte
        # threshold on the training games: keep >= 95 % of their window recall
        idx = np.where(tr)[0]
        base = window_recall_sub(idx, np.ones(len(idx), bool))
        best = -np.inf
        for th in np.unique(ptr):
            if window_recall_sub(idx, ptr >= th) >= 0.95 * base:
                best = th
            else:
                break
        keep[te] = pte >= best
    return prob, keep


def window_recall_sub(idx, keep_sub):
    segs_tr = {rows[i]["seg"] for i in idx}
    tg = [(s, rel) for s, rel in targets if s in segs_tr]
    kept = [rows[i] for i, k in zip(idx, keep_sub, strict=False) if k]
    hit = sum(
        any(c["seg"] == s and rel - 3 <= c["peak"] <= rel + 12 for c in kept) for s, rel in tg
    )
    return hit / max(1, len(tg))


total_min = sum(dur.values()) / 60
out = {
    "kind": KIND,
    "cands": len(rows),
    "pos": int(y.sum()),
    "base": {
        "window_recall": round(window_recall(np.ones(len(rows), bool)), 3),
        "precision": round(y.mean(), 3),
        "per_min": round(len(rows) / total_min, 2),
    },
}
for name, fn, feats in (
    ("score", None, "score"),
    ("logreg", lambda: LogisticRegression(max_iter=2000, C=0.5), "all"),
    (
        "gb",
        lambda: GradientBoostingClassifier(
            max_depth=2, n_estimators=150, learning_rate=0.05, subsample=0.8, random_state=0
        ),
        "all",
    ),
):
    prob, keep = run(fn, feats)
    out[name] = {
        "auc": round(roc_auc_score(y, prob), 3),
        "window_recall": round(window_recall(keep), 3),
        "precision": round(y[keep].mean(), 3) if keep.any() else 0,
        "per_min": round(keep.sum() / total_min, 2),
        "kept": int(keep.sum()),
    }
print(json.dumps(out, indent=1))
if KIND == "goal":
    m = GradientBoostingClassifier(
        max_depth=2, n_estimators=150, learning_rate=0.05, subsample=0.8, random_state=0
    ).fit(X, y)
    print(sorted(zip(m.feature_importances_.round(3), names, strict=False), reverse=True)[:12])
