"""Goal clips vs non-goal clips: per-cue and combined AUC, time error of the peak.

Clip score = maximum of the cue over the grid (`cues.GRID`, same for both kinds of clip).
Combined score per time step = sum of the chosen cues, each standardised on the non-goal steps
(robust: median / IQR, clipped) and weighted by a logistic regression on the clip maxima, trained
leave-one-clip-out so every clip is scored by a model that never saw it.
Time error = peak time - logged time (6 s into a goal clip) and - overlay score change (reference).

usage: uv run --project packages/vision python ml/goals/evaluate.py CACHE_DIR GOAL_INDEX.json
       [--cues pan_rev,still_swing,...] [--out results.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cues as cuemod  # noqa: E402

LOGGED_S = 6.0


def auc(pos: np.ndarray, neg: np.ndarray) -> float:
    """Mann-Whitney AUC with ties counted half."""
    pos, neg = np.asarray(pos, float), np.asarray(neg, float)
    gt = (pos[:, None] > neg[None, :]).sum() + 0.5 * (pos[:, None] == neg[None, :]).sum()
    return float(gt / (len(pos) * len(neg)))


def load_cues(cache: Path, recompute: bool = False) -> dict[str, dict[str, np.ndarray]]:
    store = cache / "cues_cache.npz"
    have: dict[str, dict[str, np.ndarray]] = {}
    if store.exists() and not recompute:
        z = np.load(store, allow_pickle=True)
        have = z["cues"].item()
    changed = False
    for f in sorted(cache.glob("*.npz")):
        if f.name == "cues_cache.npz" or f.stem in have:
            continue
        z = np.load(f)
        have[f.stem] = cuemod.compute(z)
        changed = True
    if changed:
        np.savez(store, cues=np.array(have, dtype=object))
    return have


def standardise(cues: dict[str, dict[str, np.ndarray]], negs: list[str], names: list[str]
                ) -> dict[str, dict[str, np.ndarray]]:
    out: dict[str, dict[str, np.ndarray]] = {c: {} for c in cues}
    for n in names:
        ref = np.concatenate([cues[c][n] for c in negs])
        med = np.median(ref)
        iqr = max(np.percentile(ref, 75) - np.percentile(ref, 25), 1e-6)
        for c in cues:
            out[c][n] = np.clip((cues[c][n] - med) / iqr, -3, 10)
    return out


def logreg(x: np.ndarray, y: np.ndarray, l2: float = 1.0, iters: int = 500) -> np.ndarray:
    xb = np.column_stack([x, np.ones(len(x))])
    w = np.zeros(xb.shape[1])
    for _ in range(iters):  # Newton steps
        p = 1 / (1 + np.exp(-xb @ w))
        g = xb.T @ (p - y) + l2 * np.r_[w[:-1], 0]
        h = xb.T @ (xb * (p * (1 - p))[:, None]) + l2 * np.diag(np.r_[np.ones(len(w) - 1), 0])
        step = np.linalg.solve(h, g)
        w -= step
        if np.abs(step).max() < 1e-8:
            break
    return w


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cache", type=Path)
    ap.add_argument("goal_index", type=Path)
    ap.add_argument("--cues", default="")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--recompute", action="store_true")
    ap.add_argument("--template", action="store_true", help="also score the matched-filter cue")
    ap.add_argument("--channels", default="0,1,2", help="profile channels: 0 pan, 1 goal-area paint, 2 energy")
    ap.add_argument("--template-shift", type=float, default=1.0,
                    help="template centre relative to the overlay change (s)")
    a = ap.parse_args()
    index = {Path(e["clip"]).stem: e for e in json.loads(a.goal_index.read_text())}
    cues = load_cues(a.cache, a.recompute)
    ref_path = a.cache / "overlay_ref.json"
    ref = json.loads(ref_path.read_text()) if ref_path.exists() else {}
    pos = [c for c in cues if c in index]
    neg = [c for c in cues if c.startswith("neg_")]
    names = list(next(iter(cues.values())).keys())
    tg = cuemod.grid()
    print(f"{len(pos)} goal clips, {len(neg)} non-goal clips, grid {tg[0]}..{tg[-1]} s")
    rows = []

    ovl = [c for c in pos if ref.get(c, {}).get("change_s") is not None]
    print(f"{len(ovl)} goal clips with the overlay score change inside the clip")
    ref_t = np.array([ref[c]["change_s"] for c in ovl])
    # timing prior: always answer the same clip time (median overlay change); its error is the
    # spread a detector has to beat
    prior_err = ref_t - np.median(ref_t)
    print(f"prior (constant {np.median(ref_t):.1f} s): |err| median {np.median(np.abs(prior_err)):.2f} s, "
          f"within 1 s {np.mean(np.abs(prior_err) <= 1):.2f}")

    def report(name: str, series: dict[str, np.ndarray], show_fp: bool = False) -> dict[str, object]:
        sp = np.array([series[c].max() for c in pos])
        so = np.array([series[c].max() for c in ovl])
        sn = np.array([series[c].max() for c in neg])
        thr = np.percentile(sn, 90)
        peak = {c: float(tg[int(np.argmax(series[c]))]) for c in pos}
        err_log = np.array([peak[c] - LOGGED_S for c in pos])
        err = np.array([peak[c] - ref[c]["change_s"] for c in ovl])
        off = float(np.median(err))
        row = {
            "cue": name,
            "auc_all": round(auc(sp, sn), 3),
            "auc_overlay_confirmed": round(auc(so, sn), 3),
            "recall_at_10fp": round(float((so > thr).mean()), 3),
            "peak_minus_logged_median_s": round(float(np.median(err_log)), 2),
            "peak_minus_overlay_median_s": round(off, 2),
            "abs_dev_from_offset_median_s": round(float(np.median(np.abs(err - off))), 2),
            "within1s_after_offset": round(float(np.mean(np.abs(err - off) <= 1.0)), 3),
        }
        rows.append(row)
        print(f"{name:15s} AUC {row['auc_all']:.3f} / {row['auc_overlay_confirmed']:.3f}  "
              f"R@10%FP {row['recall_at_10fp']:.2f}  peak-logged {row['peak_minus_logged_median_s']:+.1f}  "
              f"peak-overlay {off:+.1f} (|dev| {row['abs_dev_from_offset_median_s']:.2f}, "
              f"<=1s {row['within1s_after_offset']:.2f})")
        if show_fp:
            top = sorted(neg, key=lambda c: -series[c].max())[:6]
            miss = sorted(ovl, key=lambda c: series[c].max())[:6]
            print("   top non-goal clips:", [(c, float(tg[int(np.argmax(series[c]))])) for c in top])
            print("   weakest goal clips:", miss)
        return row

    for n in names:
        if max(np.ptp(cues[c][n]) for c in cues) == 0:
            continue  # cue not available in this cache
        report(n, {c: cues[c][n] for c in cues})
    chosen = [c for c in a.cues.split(",") if c] or names
    zc = standardise(cues, neg, chosen)
    clips = pos + neg
    y = np.r_[np.ones(len(pos)), np.zeros(len(neg))]
    x = np.array([[zc[c][n].max() for n in chosen] for c in clips])
    combined: dict[str, np.ndarray] = {}
    for i, c in enumerate(clips):
        m = np.arange(len(clips)) != i
        w = logreg(x[m], y[m])
        combined[c] = np.array([zc[c][n] for n in chosen]).T @ w[:-1]
    report("combined(LOO)", combined)
    w_all = logreg(x, y)
    print("weights (all clips):", dict(zip(chosen, np.round(w_all[:-1], 3).tolist(), strict=True)))
    # equal-weight sum: no fitting at all
    report("sum(z)", {c: np.array([zc[c][n] for n in chosen]).sum(axis=0) for c in clips}, show_fp=True)
    # matched filter: the mean cue profile around the overlay score change of the goal clips
    # (leave-one-out for goal clips), cosine similarity at every grid step
    if a.template:
        chans = [int(v) for v in a.channels.split(",")]
        prof = {}
        for f in sorted(a.cache.glob("*.npz")):
            if f.stem in cues:
                prof[f.stem] = cuemod.profile_channels(np.load(f))[:, chans]
        neg_all = np.concatenate([prof[c] for c in neg])
        mu, sd = neg_all.mean(axis=0), neg_all.std(axis=0) + 1e-6
        ex = {c: [(cuemod.profile_at(prof[c], ref[c]["change_s"] + dt) - mu) / sd
                  for dt in (a.template_shift,)] for c in ovl}

        def tmpl(skip: str | None) -> np.ndarray:
            return np.mean([e for c in ovl if c != skip for e in ex[c]], axis=0)

        full = tmpl(None)
        tseries = {}
        for c in pos + neg:
            tp = tmpl(c) if c in ex else full
            tpv = (tp - tp.mean()).ravel()
            vals = []
            for t in tg:
                w = ((cuemod.profile_at(prof[c], t) - mu) / sd).ravel()
                w = w - w.mean()
                vals.append(float(w @ tpv / (np.linalg.norm(w) * np.linalg.norm(tpv) + 1e-9)))
            tseries[c] = np.array(vals)
        report(f"template{a.channels}", tseries, show_fp=True)
        np.save(a.cache / "template.npy", np.stack([full, mu[None].repeat(len(full), 0), sd[None].repeat(len(full), 0)]))
    if a.out:
        a.out.write_text(json.dumps({"rows": rows, "cues": chosen,
                                     "weights": dict(zip(chosen, w_all[:-1].tolist(), strict=True))}, indent=1))


if __name__ == "__main__":
    main()
