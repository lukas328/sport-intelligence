"""A1: AUC per cue and leave-one-game-out combinations, quota 1 / 1.5 / 2 per minute (goal_ball_cues.py)."""

# ruff: noqa: N803, N806  (matrix names as in the maths: X, A, H)
import json
import sys
from pathlib import Path

import numpy as np

rows = json.loads(Path(sys.argv[1]).read_text())
meta = {r["seg"]: r for r in rows if r.get("meta")}
C = [r for r in rows if not r.get("meta")]
F = ["score", "ball_speed_pre", "end_pre", "center_still_post", "center_any_post"]
X = np.array([[r[f] if r[f] is not None else np.nan for f in F] for r in C], float)
y = np.array([r["tp"] for r in C], bool)
games = np.array([r["game"] for r in C])


def auc(s, y):
    ok = np.isfinite(s)
    s, y = s[ok], y[ok]
    from scipy.stats import rankdata

    r = rankdata(s)
    n1 = y.sum()
    n0 = len(y) - n1
    return (r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


print(
    f"pool rate<=4: {len(C)} candidates, {y.sum()} TP, goals {sum(len(m['goals']) for m in meta.values())}"
)
for i, f in enumerate(F):
    print(f"  {f:20s} AUC {auc(X[:, i], y):.3f}  missing {np.isnan(X[:, i]).mean():.0%}")


def fit(Xt, yt, l2=1.0, it=500):
    w = np.zeros(Xt.shape[1] + 1)
    A = np.c_[np.ones(len(Xt)), Xt]
    for _ in range(it):
        p = 1 / (1 + np.exp(-A @ w))
        g = A.T @ (p - yt) / len(yt) + l2 * np.r_[0, w[1:]] / len(yt)
        H = (A * (p * (1 - p))[:, None]).T @ A / len(yt) + l2 * np.diag(
            np.r_[0, np.ones(len(w) - 1)]
        ) / len(yt)
        w -= np.linalg.solve(H + 1e-9 * np.eye(len(w)), g)
    return w


def logo(cols):
    out = np.zeros(len(C))
    for g in np.unique(games):
        tr, te = games != g, games == g
        Xs = X[:, cols].copy()
        mu = np.nanmedian(Xs[tr], 0)
        Xs = np.where(np.isnan(Xs), mu, Xs)
        sd = Xs[tr].std(0) + 1e-9
        Xs = (Xs - Xs[tr].mean(0)) / sd
        w = fit(Xs[tr], y[tr].astype(float))
        out[te] = np.c_[np.ones(te.sum()), Xs[te]] @ w
    return out


def quota(s, r):
    found = n = tp = 0
    for seg, m in meta.items():
        idx = [i for i, c in enumerate(C) if c["seg"] == seg]
        k = round(r * m["play_s"] / 60)
        keep = sorted(idx, key=lambda i: -s[i])[:k]
        n += len(keep)
        tp += sum(y[i] for i in keep)
        found += len({C[i]["goal"] for i in keep if C[i]["goal"] is not None})
    G = sum(len(m["goals"]) for m in meta.values())
    return found / G, tp / max(n, 1), n


sets = {
    "score": [0],
    "score+speed": [0, 1],
    "score+speed+end": [0, 1, 2],
    "score+throwoff": [0, 3, 4],
    "all": [0, 1, 2, 3, 4],
}
print("\nLOGO (13 games): AUC | recall/precision/count at 1, 1.5, 2 per min")
for name, cols in sets.items():
    s = logo(cols) if name != "score" else X[:, 0]
    q = [quota(s, r) for r in (1, 1.5, 2)]
    print(
        f"  {name:18s} AUC {auc(s, y):.3f} | " + "  ".join(f"{a:.2f}/{b:.2f}/{n}" for a, b, n in q)
    )
