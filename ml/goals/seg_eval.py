"""Goal candidates on whole ingest segments, scored against free labels (`seg_labels.py`).

Reference goal time per segment: the score overlay's change (exact to the 0.5 s reading step) where
the overlay is read; otherwise the official log time minus the log delay, which is measured here on
the goals that have both (same score). Segments with neither are left out.

Scores (one series per segment on a 0.2 s grid, from `seg_cues.py`):
- single cues: pan_rev, still_swing, pan_after, cen_rev, flow_rev, play_rev, energy_drop,
  restart_back (throw-off detector moved back to the goal);
- `sum_*`: sum of per-segment robust z-scores (median / IQR of the segment, clipped);
- `tmpl_*`: matched filter. Channels are z-scored per segment; the template is the mean profile
  around reference goal + `--shift`, built leave-one-game-out (no goal of the scored game helps);
- `bcast_*`: the Magdeburg broadcast template (pan, energy; `cues.profile_channels`, built from the
  overlay-confirmed goal clips as in `evaluate.py`), normalised with the broadcast's non-goal clips
  (`_mdnorm`) or per segment (`_segnorm`): how well the TV template transfers;
- `logreg`: logistic regression on all cues at t, leave-one-game-out.

Metrics:
- candidates: peaks with `NMS_S` non-maximum suppression, the top `rate * minutes` per segment
  (rates 1, 2, 4 per minute). A goal is found when a candidate lies `HIT` (-3..+8 s) around it; each
  candidate finds at most one goal. Recall per rate, with the recall of random candidates (same
  count, same suppression) as the baseline, and the median candidate - goal time of the hits;
- window AUC: the max score in the hit window of each goal against the same-length windows that
  stay 15 s away from every goal (comparable with the 9-second clip AUC of the broadcast study).
Breakdowns per game, per camera type (fixed / panning from the pan statistics) and per overlay.

usage: uv run --project packages/vision python ml/goals/seg_eval.py CACHE_DIR LABELS.json
       [--broadcast <scratch>/goals/cache] [--shift 2] [--out results.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import seg_cues as sc  # noqa: E402

STEP = 2  # grid stride (0.2 s)
NMS_S = 8.0
HIT = (-3.0, 8.0)  # candidate - goal (s)
RATES = (1, 2, 4)
SINGLE = ("pan_rev", "still_swing", "pan_after", "cen_rev", "flow_rev", "play_rev", "energy_drop",
          "restart", "restart_back", "lull_after")
SUMS = {
    "sum_camera": ("pan_rev", "still_swing"),
    "sum_people_flow": ("cen_rev", "flow_rev"),
    "sum_all": ("pan_rev", "still_swing", "cen_rev", "flow_rev"),
    "sum_all_restart": ("pan_rev", "still_swing", "cen_rev", "flow_rev", "restart_back"),
    "sum_all_lull": ("pan_rev", "still_swing", "cen_rev", "flow_rev", "lull_after"),
}
TEMPLATES = {
    "tmpl_all": (("pan", "cx_v", "flow_x", "flow_share", "energy"), (0, 1, 2)),
    "tmpl_camera": (("pan", "energy"), (0,)),
    "tmpl_people_flow": (("cx_v", "flow_x", "flow_share"), (0, 1)),
}
# games looked at while designing `lull_after`, the restart detector and RESTART_LAG; the others
# are a held-out test
DEV_GAMES = ("CH_NLB_SGWaedenswilHorgen_Emmen_2023-09-03", "CH_NLB_SGWaedenswilHorgen_FortitudoGossau_2023-09-23",
             "CH_NLB_SGWaedenswilHorgen_HCArbon_2023-12-10")
MAX_ANCHOR_GAP_S = 5.0  # log entries counted from a clock reading further away are unreliable
CAMERA_FIXED_PX_S = 25.0  # 90th percentile |pan| below this: fixed camera


# --- data ----------------------------------------------------------------------------------------


def load(cache: Path, labels: dict, shift_log: float | None) -> dict[str, dict]:
    store = cache.parent / "seg_signals.npz"
    have = dict(np.load(store, allow_pickle=True)["d"].item()) if store.exists() else {}
    segs, changed = {}, False
    for stem, lab in sorted(labels.items()):
        f = cache / f"{stem}.npz"
        if not f.exists():
            continue
        if stem not in have or have[stem].get("_mtime") != f.stat().st_mtime:
            s = sc.signals(np.load(f))
            c = sc.compute(s)
            have[stem] = {"_mtime": f.stat().st_mtime,
                          **{k: v.astype(np.float32) for k, v in {**s, **c}.items()}}
            changed = True
        segs[stem] = {"lab": lab, "x": have[stem]}
    if changed:
        np.savez_compressed(store, d=np.array(have, dtype=object))
    return segs


def log_delay(labels: dict) -> tuple[float | None, list[float]]:
    """Log time - overlay change for goals that have both (same score in the same segment)."""
    d = []
    for lab in labels.values():
        ov = {tuple(g["score"]): g["t"] for g in lab["overlay_goals"]}
        for g in lab["log_goals"]:
            if (g.get("anchor_gap_s") or 0) > MAX_ANCHOR_GAP_S:
                continue
            sc_ = tuple(g["score"] or ())
            for key in (sc_, sc_[::-1]):
                if key in ov:
                    d.append(g["t"] - ov[key])
                    break
    d = [x for x in d if abs(x) < 30]
    return (float(np.median(d)) if d else None), d


def reference(lab: dict, delay: float | None) -> tuple[list[float], str]:
    dur = lab["duration_s"]
    if lab["score_reads"] >= 0.5 * dur / 0.5:  # overlay read on at least half of the probes
        # a jump by several goals (overlay hidden or misread for a while) has no usable time
        return [g["t"] for g in lab["overlay_goals"] if g.get("single", True)], "overlay"
    if lab["log_goals"] and delay is not None:
        return [g["t"] - delay for g in lab["log_goals"]
                if 0 <= g["t"] - delay <= dur and (g.get("anchor_gap_s") or 0) <= MAX_ANCHOR_GAP_S], "log"
    return [], "none"


def camera_type(x: dict) -> str:
    return "fixed" if np.percentile(np.abs(x["pan"]), 90) < CAMERA_FIXED_PX_S else "panning"


# --- scores --------------------------------------------------------------------------------------


def rz(v: np.ndarray) -> np.ndarray:
    med = np.median(v)
    iqr = max(np.percentile(v, 75) - np.percentile(v, 25), 1e-6)
    return np.clip((v - med) / iqr, -3, 10)


def template_series(ch: np.ndarray, tmpl: np.ndarray, sign_cols: tuple[int, ...]) -> np.ndarray:
    tpv = (tmpl - tmpl.mean()).ravel()
    idx = np.arange(0, len(ch), STEP)
    vals = []
    for i in idx:
        w = sc.profile_at(ch, i, sign_cols).ravel()
        w = w - w.mean()
        vals.append(float(w @ tpv / (np.linalg.norm(w) * np.linalg.norm(tpv) + 1e-9)))
    return np.interp(np.arange(len(ch)), idx, vals)


def seg_channels(x: dict, names: tuple[str, ...]) -> np.ndarray:
    ch = np.column_stack([x[n] for n in names]).astype(float)
    med = np.median(ch, axis=0)
    iqr = np.maximum(np.percentile(ch, 75, axis=0) - np.percentile(ch, 25, axis=0), 1e-6)
    return (ch - med) / iqr


def broadcast_template(cache: Path) -> dict | None:
    """Magdeburg template on (pan, energy) as `evaluate.py --template --channels 0,2` builds it."""
    import cues as cuemod

    ref_p = cache / "overlay_ref.json"
    if not ref_p.exists():
        return None
    ref = json.loads(ref_p.read_text())
    prof, neg = {}, []
    for f in sorted(cache.glob("*.npz")):
        if f.name in ("cues_cache.npz",):
            continue
        z = np.load(f)
        if "pan" not in z:
            continue
        ch = cuemod.profile_channels(z)[:, [0, 2]]
        if f.stem.startswith("neg_"):
            neg.append(ch)
        elif ref.get(f.stem, {}).get("change_s") is not None:
            prof[f.stem] = (ch, ref[f.stem]["change_s"])
    allneg = np.concatenate(neg)
    mu, sd = allneg.mean(axis=0), allneg.std(axis=0) + 1e-6
    tm = np.mean([(cuemod.profile_at(ch, t + 1.0) - mu) / sd for ch, t in prof.values()], axis=0)
    return {"tmpl": tm, "mu": mu, "sd": sd, "n": len(prof)}


def bcast_channels(x: dict) -> np.ndarray:
    """(pan px/s / 100, energy) on the 10 Hz grid, the units of `cues.profile_channels`."""
    return np.column_stack([x["pan"] / 100, x["energy"]]).astype(float)


def all_scores(segs: dict, refs: dict, shift: float, bc: dict | None) -> dict[str, dict[str, np.ndarray]]:
    out: dict[str, dict[str, np.ndarray]] = {}
    games = sorted({s["lab"]["game"] for s in segs.values()})
    for stem, s in segs.items():
        x = s["x"]
        d = {n: x[n].astype(float) for n in SINGLE}
        for name, cols in SUMS.items():
            d[name] = sum(rz(x[c]) for c in cols)
        out[stem] = d
    # leave-one-game-out templates
    for name, (cols, sign) in TEMPLATES.items():
        chs = {stem: seg_channels(s["x"], cols) for stem, s in segs.items()}
        ex = {g: [] for g in games}
        for stem, s in segs.items():
            for t in refs[stem]:
                i = round((t + shift) / sc.DT)
                if 0 <= i < len(chs[stem]):
                    ex[s["lab"]["game"]].append(sc.profile_at(chs[stem], i, sign))
        for stem, s in segs.items():
            others = [e for g, v in ex.items() if g != s["lab"]["game"] for e in v]
            out[stem][name] = template_series(chs[stem], np.mean(others, axis=0), sign) if others else np.zeros(len(chs[stem]))
    # matched filter (the transition) plus the post-goal lull (goal-specific evidence)
    for stem in segs:
        o = out[stem]
        o["tmpl_all+lull"] = rz(o["tmpl_all"]) + rz(o["lull_after"])
        o["tmpl_people_flow+lull"] = rz(o["tmpl_people_flow"]) + rz(o["lull_after"])
        o["tmpl_camera+lull"] = rz(o["tmpl_camera"]) + rz(o["lull_after"])
    if bc is not None:
        for stem, s in segs.items():
            ch = bcast_channels(s["x"])
            out[stem]["bcast_mdnorm"] = template_series((ch - bc["mu"]) / bc["sd"], bc["tmpl"], (0,))
            seg = (ch - ch.mean(axis=0)) / (ch.std(axis=0) + 1e-6)
            out[stem]["bcast_segnorm"] = template_series(seg, bc["tmpl"], (0,))
    # leave-one-game-out logistic regression on the cues at t (z-scored per segment)
    feats = ("pan_rev", "still_swing", "pan_after", "cen_rev", "flow_rev", "play_rev", "energy_drop",
             "restart_back", "lull_after", "tmpl_all")
    X, Y, G = {}, {}, {}
    for stem, s in segs.items():
        n = len(s["x"]["t"])
        X[stem] = np.column_stack([rz(out[stem][f]) for f in feats])[::STEP]
        y = np.zeros(n)
        for t in refs[stem]:
            y[max(0, round((t - 0.5) / sc.DT)):round((t + 4.0) / sc.DT)] = 1
        Y[stem] = y[::STEP]
        G[stem] = s["lab"]["game"]
    import evaluate as ev

    for g in games:
        tr = [k for k in segs if G[k] != g]
        if not tr or not any(Y[k].any() for k in tr):
            w = np.zeros(len(feats) + 1)
        else:
            w = ev.logreg(np.concatenate([X[k] for k in tr]), np.concatenate([Y[k] for k in tr]), l2=10.0, iters=50)
        for k in segs:
            if G[k] == g:
                n = len(segs[k]["x"]["t"])
                idx = np.arange(0, n, STEP)
                out[k]["logreg"] = np.interp(np.arange(n), idx, X[k] @ w[:-1])
    return out


# --- metrics -------------------------------------------------------------------------------------


def peaks(ts: np.ndarray, s: np.ndarray, k: int, nms: float = NMS_S) -> list[float]:
    order = np.argsort(-s)
    got: list[float] = []
    for i in order:
        if len(got) >= k:
            break
        if all(abs(ts[i] - t) > nms for t in got):
            got.append(float(ts[i]))
    return got


def match(cands: list[float], goals: list[float]) -> tuple[int, list[float]]:
    used: set[int] = set()
    errs = []
    for g in sorted(goals):
        best = None
        for j, c in enumerate(cands):
            if j in used or not HIT[0] <= c - g <= HIT[1]:
                continue
            if best is None or abs(c - g - 2) < abs(cands[best] - g - 2):
                best = j
        if best is not None:
            used.add(best)
            errs.append(cands[best] - g)
    return len(errs), errs


def random_recall(dur: float, goals: list[float], k: int, rng: np.random.Generator, n: int = 200) -> float:
    ts = np.arange(0, dur, sc.DT * STEP)
    hits = 0
    for _ in range(n):
        hits += match(peaks(ts, rng.random(len(ts)), k), goals)[0]
    return hits / n


def window_auc(series: dict[str, np.ndarray], segs: dict, refs: dict) -> float:
    import evaluate as ev

    pos, neg = [], []
    span = HIT[1] - HIT[0]
    for stem, s in series.items():
        ts = segs[stem]["x"]["t"]
        goals = refs[stem]
        for g in goals:
            m = (ts >= g + HIT[0]) & (ts <= g + HIT[1])
            if m.any():
                pos.append(s[m].max())
        for a in np.arange(2.0, ts[-1] - span - 2, span):
            if all(a > g + 15 or a + span < g - 15 for g in goals):
                m = (ts >= a) & (ts <= a + span)
                neg.append(s[m].max())
    return ev.auc(np.array(pos), np.array(neg)) if pos and neg else float("nan")


def evaluate(scores: dict, segs: dict, refs: dict, subset: list[str], rng: np.random.Generator) -> dict:
    res: dict[str, dict] = {}
    n_goals = sum(len(refs[k]) for k in subset)
    minutes = sum(segs[k]["lab"]["duration_s"] for k in subset) / 60
    base = {}
    for r in RATES:
        h = sum(random_recall(segs[k]["lab"]["duration_s"], refs[k], round(r * segs[k]["lab"]["duration_s"] / 60), rng, 50)
                for k in subset if refs[k])
        base[r] = h / max(n_goals, 1)
    res["_random"] = {f"r@{r}": round(base[r], 3) for r in RATES}
    for name in next(iter(scores.values())):
        row = {}
        for r in RATES:
            hits, errs = 0, []
            for k in subset:
                ts = segs[k]["x"]["t"][::STEP]
                s = scores[k][name][::STEP]
                kk = round(r * segs[k]["lab"]["duration_s"] / 60)
                h, e = match(peaks(ts, s, kk), refs[k])
                hits += h
                errs += e
            row[f"r@{r}"] = round(hits / max(n_goals, 1), 3)
            if r == 2:
                row["err_med"] = round(float(np.median(errs)), 1) if errs else None
                row["err_iqr"] = (round(float(np.percentile(errs, 75) - np.percentile(errs, 25)), 1)
                                  if errs else None)
        row["auc"] = round(window_auc({k: scores[k][name] for k in subset}, segs, refs), 3)
        res[name] = row
    res["_n"] = {"goals": n_goals, "segments": len(subset), "minutes": round(minutes, 1)}
    return res


def inspect(name: str, scores: dict, segs: dict, refs: dict, use: list[str], delay: float) -> None:
    """Candidates of one score at 2 per minute: hits, misses, and false alarms explained by the
    nearest official log entry (shot saved / missed, turnover, ...) up to 10 s before them."""
    kinds: dict[str, int] = {}
    n_fa = 0
    for k in use:
        ts = segs[k]["x"]["t"][::STEP]
        cands = peaks(ts, scores[k][name][::STEP], round(2 * segs[k]["lab"]["duration_s"] / 60))
        hit_c = set()
        for g in refs[k]:
            ok = [c for c in cands if HIT[0] <= c - g <= HIT[1]]
            if ok:
                hit_c.add(min(ok, key=lambda c: abs(c - g - 2)))
        misses = [round(g) for g in refs[k] if not any(HIT[0] <= c - g <= HIT[1] for c in cands)]
        fas = sorted(c for c in cands if c not in hit_c)
        expl = []
        for c in fas:
            near = [e for e in segs[k]["lab"]["log_other"] if -2 <= c - (e["t"] - delay) <= 10]
            kind = near[-1]["kind"] if near else ("?" if segs[k]["lab"]["log_goals"] or segs[k]["lab"]["has_log"] else "no log")
            expl.append(f"{c:.0f}:{kind}")
            if segs[k]["lab"]["has_log"] and segs[k]["lab"]["clock_source"]:
                kinds[kind] = kinds.get(kind, 0) + 1
                n_fa += 1
        print(f"{k[26:]}: goals {[round(g) for g in refs[k]]} missed {misses} false {expl}")
    print(f"false alarms in segments with a clock and a log ({n_fa}):", kinds)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cache", type=Path)
    ap.add_argument("labels", type=Path)
    ap.add_argument("--broadcast", type=Path,
                    default=Path("/tmp/claude-0/-home-user/3dc450e2-2499-5e21-b252-1c4e366c6b5a/scratchpad/goals/cache"))
    ap.add_argument("--shift", type=float, default=2.0, help="template centre - reference goal (s)")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--inspect", help="score name: list its candidates at 2/min, misses and what the "
                    "false alarms were in the official log")
    a = ap.parse_args()
    labels = json.loads(a.labels.read_text())
    delay, pairs = log_delay(labels)
    print(f"log delay (log - overlay change): median {delay} s over {len(pairs)} goals: "
          f"{sorted(round(p, 1) for p in pairs)}")
    segs = load(a.cache, labels, delay)
    refs, src = {}, {}
    for stem, s in segs.items():
        refs[stem], src[stem] = reference(s["lab"], delay)
    use = [k for k in segs if src[k] != "none"]
    print(f"{len(use)} labelled segments of {len(segs)}: "
          f"{sum(len(refs[k]) for k in use)} goals in {sum(segs[k]['lab']['duration_s'] for k in use) / 60:.1f} min")
    for k in use:
        x = segs[k]["x"]
        print(f"  {k}: {src[k]}, {camera_type(x)} (pan p90 {np.percentile(np.abs(x['pan']), 90):.0f} px/s), "
              f"overlay {segs[k]['lab']['overlay']}, goals {[round(g) for g in refs[k]]}")
    bc = broadcast_template(a.broadcast) if a.broadcast.exists() else None
    if bc:
        print(f"broadcast template from {bc['n']} Magdeburg goal clips")
    scores = all_scores({k: segs[k] for k in use}, refs, a.shift, bc)
    rng = np.random.default_rng(0)
    groups: dict[str, list[str]] = {"all": use}
    for k in use:
        lab = segs[k]["lab"]
        groups.setdefault(f"game:{lab['game']}", []).append(k)
        groups.setdefault(f"camera:{camera_type(segs[k]['x'])}", []).append(k)
        groups.setdefault(f"overlay:{'yes' if lab['overlay'] else 'no'}", []).append(k)
        groups.setdefault(f"ref:{src[k]}", []).append(k)
        groups.setdefault(f"split:{'dev' if lab['game'] in DEV_GAMES else 'test'}", []).append(k)
    results = {}
    for gname, subset in groups.items():
        r = evaluate(scores, segs, refs, subset, rng)
        results[gname] = r
        n = r["_n"]
        print(f"\n== {gname}: {n['goals']} goals, {n['segments']} segments, {n['minutes']} min; "
              f"random r@1/2/4 {r['_random']['r@1']:.2f}/{r['_random']['r@2']:.2f}/{r['_random']['r@4']:.2f}")
        if gname != "all" and not gname.startswith(("camera", "overlay", "ref", "split")):
            names = ["pan_rev", "cen_rev", "flow_rev", "sum_all", "tmpl_all", "tmpl_people_flow", "logreg"]
        else:
            names = [k for k in r if not k.startswith("_")]
        for name in names:
            row = r[name]
            print(f"  {name:18s} r@1 {row['r@1']:.2f}  r@2 {row['r@2']:.2f}  r@4 {row['r@4']:.2f}  "
                  f"AUC {row['auc']:.3f}  err {row['err_med']} (IQR {row['err_iqr']})")
    if a.inspect:
        inspect(a.inspect, scores, segs, refs, use, delay or 0.0)
    if a.out:
        a.out.write_text(json.dumps({"log_delay_s": delay, "log_pairs": pairs, "results": results,
                                     "refs": {k: refs[k] for k in use}, "src": src}, indent=1))


if __name__ == "__main__":
    main()
