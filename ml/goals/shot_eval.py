"""Shot candidates: how well do the goal-candidate signals, and simple variants, find shots (goals,
saves, misses) on the labelled club segments? Labels are the official log entries per segment
(`ml/data/segment_labels/*.json`, `segment_clock.py --labels`): every goal, saved and missed shot,
turnover and time-out with its time in the segment (accurate to a few seconds).

Signals per segment (10 Hz, `handball_vision.goalcandidates.signals`, the product channels):
from the stored observation pass (`product_path.py observe`) when there is one, else from the
research cache (`seg_extract.py`, through `goal_template.cache_signals`). The research cache adds
the research cues (`seg_cues`: flow, energy, play position) where it has people.

Scores (all on the product channels unless marked research):
- `goal`: the shipped goal-candidate score (template + lull), `goal_tmpl` / `lull` its two parts;
- `shot_tmpl`: the same matched filter, its profile learned leave-one-game-out from the shots
  (`--shift` s after the log time); `shot_tmpl_sm` only from saves and misses;
- `end`: the play is at one end of the court (people centroid near the extremes the camera
  covered) and then turns round: how a shot ends an attack (`end_cue`);
- sums of those; research cues `pan_rev`, `pan_after`, `cen_rev`, `play_rev`, `lull_after`;
- `logreg`: logistic regression on the cue values, leave-one-game-out.

Measures: recall at 1 / 2 / 4 / 6 candidates per minute (top peaks per segment, 8 s suppression;
a shot is found by a candidate 3 s before to 8 s after its log time, the goal rule), for all
shots, goals, saves and misses; random candidates as the baseline; candidate - shot (median, IQR);
per game; and at the labelled moments: shots against turnovers and goals against saves and misses
(AUC of the best score in the same window).

usage: uv run --project packages/vision python ml/goals/shot_eval.py <labels dir> \
         --obs <scratch>/gc_bench/obs <scratch>/gc_bench/obs_l --cache <scratch>/goals_raw/cache \
         [--store <scratch>/shots/sig.pkl] [--out results.json]
"""

from __future__ import annotations

import argparse
import json
import pickle
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages/vision"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import evaluate as ev  # noqa: E402
import goal_template as gt  # noqa: E402
import seg_cues as sc  # noqa: E402
import seg_eval as se  # noqa: E402

from handball_vision import goalcandidates as gc  # noqa: E402

GOAL = ("goal", "penalty_goal")
SAVE = ("shot_saved", "penalty_saved")
MISS = ("shot_missed", "penalty_missed", "shot_post", "penalty_post")
SHOT = GOAL + SAVE + MISS
NEG = ("turnover",)
CLASSES = {"shots": SHOT, "goals": GOAL, "saves": SAVE, "misses": MISS}
RATES = (1, 2, 4, 6)
EDGE_S = 6.0
MAX_ANCHOR_GAP_S = 5.0
HIT = se.HIT  # candidate - event, (-3, +8) s
RESEARCH = ("pan_rev", "pan_after", "cen_rev", "play_rev", "lull_after")


# --- data -----------------------------------------------------------------------------------------


def load_segments(label_dir: Path) -> dict[str, dict[str, Any]]:
    """Labelled segments with a clock: game, entries (kind, t in the segment, team, number)."""
    out: dict[str, dict[str, Any]] = {}
    for f in sorted(label_dir.glob("*.json")):
        d = json.loads(f.read_text())
        for s in d["segments"]:
            if not s.get("clock_source"):
                continue
            ents = [
                {
                    "kind": e["kind"],
                    "t": e["segment_ms"] / 1000,
                    "team": e.get("team"),
                    "number": e.get("number"),
                }
                for e in d["entries"]
                if e["segment"] == s["file"] and (e.get("anchor_gap_s") or 0) <= MAX_ANCHOR_GAP_S
            ]
            out[s["file"][:-4]] = {"game": d["name"], "entries": ents}
    return out


def product_inputs(stem: str, obs_dirs: list[Path], cache_dirs: list[Path]) -> tuple[Any, str]:
    """`goalcandidates` inputs of a segment: the observation pass if stored, else the research
    cache (camera = minus the accumulated content shift, YOLOX-m people at 2 Hz)."""
    from handball_vision import observe
    from handball_vision.motion import CameraMotion

    for d in obs_dirs:
        if (d / f"{stem}.obs.npz").exists():
            obs = observe.load_observations(
                d / f"{stem}.obs.npz", CameraMotion.load(d / f"{stem}.motion.npz")
            )
            return gc.inputs_from_observations(obs), "observe"
    for d in cache_dirs:
        f = d / f"{stem}.npz"
        if f.exists():
            z = np.load(f)
            if len(z["people"]) < 20:
                continue
            t = z["t"].astype(float)
            cam = -np.cumsum(z["pan"].astype(float), axis=0)
            pe = z["people"].astype(float)
            pt = pe[:, 0]
            px = (pe[:, 1] + pe[:, 3]) / 2 + np.interp(pt, t, cam[:, 0])
            py = pe[:, 4] + np.interp(pt, t, cam[:, 1])
            ph = pe[:, 4] - pe[:, 2]
            return (t, cam[:, 0], pt, px, py, ph, float(t[-1])), "research"
    return None, "none"


def extra_signals(inp: Any, s: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Camera azimuth and the people's canvas centroid on the grid (positions, not speeds)."""
    cam_t, cam_x, pt, px, py, ph, _ = inp
    tg = s["t"]
    ok = np.isfinite(cam_x)
    cam = np.interp(tg, cam_t[ok], cam_x[ok]) if ok.sum() >= 2 else np.zeros(len(tg))
    keep = (ph >= gc.MIN_BOX_PX) & ~gc.static_mask(pt, px, py)
    frames, med, _, _ = gc.people_motion(pt, px, py, ph, keep)
    cx = gc._interp(tg, frames, med, 1.0)
    return {"cam": cam, "cx": cx}


def load_all(
    segs: dict[str, dict[str, Any]],
    obs_dirs: list[Path],
    cache_dirs: list[Path],
    store: Path | None,
) -> dict[str, dict[str, Any]]:
    have: dict[str, dict[str, Any]] = {}
    if store is not None and store.exists():
        have = pickle.loads(store.read_bytes())  # noqa: S301  (our own scratch store)
    changed = False
    for stem in segs:
        if stem in have and have[stem]["src"] != "none":
            continue
        inp, src = product_inputs(stem, obs_dirs, cache_dirs)
        rec: dict[str, Any] = {"src": src}
        if inp is not None:
            s = gc.signals(*inp)
            rec["p"] = {**s, **extra_signals(inp, s)}
            rec["moving"] = True
        for d in cache_dirs:
            f = d / f"{stem}.npz"
            if f.exists():
                z = np.load(f)
                if len(z["people"]) >= 20:
                    rs = sc.signals(z)
                    rec["r"] = {**rs, **sc.compute(rs)}
                break
        have[stem] = rec
        changed = True
        print(f"  {stem}: signals from {src}{', research cues' if 'r' in rec else ''}", flush=True)
    if changed and store is not None:
        store.parent.mkdir(parents=True, exist_ok=True)
        store.write_bytes(pickle.dumps(have))
    return have


# --- cues -----------------------------------------------------------------------------------------


def end_cue(s: dict[str, np.ndarray], before_s: float = 3.0, after_s: float = 3.0) -> np.ndarray:
    """The attack ends at one end of the court and the play turns round: the people's canvas
    centroid in [t - before_s, t] near the segment's extremes (|p| close to 1, p from the 3rd and
    97th percentile of the centroid, as `seg_cues`), times the turn (the centroid velocity before
    t and after t point opposite ways, or the camera swings after t)."""
    cx = s["cx"]
    a, b = np.percentile(cx, [3, 97])
    c0, half = (a + b) / 2, max((b - a) / 2, 50.0)
    p = np.clip((cx - c0) / half, -1.5, 1.5)
    n = len(cx)
    kb, ka = round(before_s / gc.DT), round(after_s / gc.DT)
    c = np.r_[0.0, np.cumsum(np.abs(p))]
    idx = np.arange(n)
    lo, hi = np.clip(idx - kb, 0, n), idx
    at_end = (c[hi] - c[lo]) / np.maximum(hi - lo, 1)
    v = (s["cx_v"] + s["pan"]) / max(gc._robust_scale(s["cx_v"] + s["pan"]), 1e-6)
    cv = np.r_[0.0, np.cumsum(v)]
    vb = (cv[hi] - cv[lo]) / np.maximum(hi - lo, 1)
    hi2 = np.clip(idx + ka, 0, n)
    va = (cv[hi2] - cv[idx]) / np.maximum(hi2 - idx, 1)
    turn = np.sqrt(np.maximum(0.0, -vb * va)) + 0.5 * np.abs(va)
    return np.asarray(np.clip(at_end, 0, 1.5) * turn, dtype=np.float64)


def shot_profiles(
    sigs: dict[str, dict[str, np.ndarray]],
    refs: dict[str, list[float]],
    shift: float,
) -> list[np.ndarray]:
    out: list[np.ndarray] = []
    for k, s in sigs.items():
        ch = gc.channels(s, gt.CHANNELS)
        at = np.array([round((t + shift) / gc.DT) for t in refs.get(k, [])], int)
        at = at[(at >= 0) & (at < len(ch))]
        if len(at):
            sign = tuple(gt.CHANNELS.index(c) for c in gt.SIGN_CHANNELS)
            out += list(gc.windows(ch, at, gt.WINDOW_S, sign))
    return out


def template(prof: list[np.ndarray]) -> gc.Template:
    return gc.Template.from_dict(gt.template_dict(np.mean(prof, axis=0), "shots", {}))


def goal_templates(labels_path: Path, cache: Path, games: set[str]) -> dict[str, gc.Template]:
    """The goal template without the goals of each game (the shipped one learned from the overlay
    goals of 12 games, 4 of them labelled here): leave-one-game-out as in `goal_template.py`."""
    labels = json.loads(labels_path.read_text())
    delay, _ = se.log_delay(labels)
    prof: dict[str, list[np.ndarray]] = defaultdict(list)
    for stem, lab in sorted(labels.items()):
        f = cache / f"{stem}.npz"
        goals, src = se.reference(lab, delay)
        if not f.exists() or src == "none":
            continue
        dur = lab["duration_s"]
        goals = [g for g in goals if gt.EDGE_MARGIN_S <= g <= dur - gt.EDGE_MARGIN_S]
        game = lab["game"].replace(".f298", "")
        prof[game] += gt.profile(gt.cache_signals(np.load(f)), goals)
    out = {}
    for g in games:
        others = [p for gg, v in prof.items() if gg != g.replace(".f298", "") for p in v]
        out[g] = gc.Template.from_dict(gt.template_dict(np.mean(others, axis=0), "logo", {}))
    return out


def scores(
    data: dict[str, dict[str, Any]],
    segs: dict[str, dict[str, Any]],
    stems: list[str],
    shift: float,
    goal_tm: dict[str, gc.Template] | None = None,
) -> dict[str, dict[str, np.ndarray]]:
    shipped = gc.load_template()
    sigs = {k: data[k]["p"] for k in stems}
    game = {k: segs[k]["game"] for k in stems}
    shots = {k: [e["t"] for e in segs[k]["entries"] if e["kind"] in SHOT] for k in stems}
    sm = {k: [e["t"] for e in segs[k]["entries"] if e["kind"] in SAVE + MISS] for k in stems}
    out: dict[str, dict[str, np.ndarray]] = {}
    tm: dict[str, tuple[gc.Template, gc.Template]] = {}
    for g in set(game.values()):
        others = {k: v for k, v in sigs.items() if game[k] != g}
        tm[g] = (
            template(shot_profiles(others, shots, shift)),
            template(shot_profiles(others, sm, shift)),
        )
    for k in stems:
        s = sigs[k]
        goal_t = (goal_tm or {}).get(game[k], shipped)
        ch = gc.channels(s, gt.CHANNELS)
        g_t = gc.rolling_rz(gc.template_series(ch, goal_t))
        lull = gc.rolling_rz(gc.lull_series(s, goal_t))
        s_t = gc.rolling_rz(gc.template_series(ch, tm[game[k]][0]))
        s_sm = gc.rolling_rz(gc.template_series(ch, tm[game[k]][1]))
        end = gc.rolling_rz(end_cue(s))
        pan_after = gc.rolling_rz(_after(np.abs(s["pan"]), 2.0))
        row = {
            "goal": g_t + lull,
            "goal_tmpl": g_t,
            "lull": lull,
            "shot_tmpl": s_t,
            "shot_tmpl_sm": s_sm,
            "end": end,
            "pan_after": pan_after,
            "shot_tmpl+end": s_t + end,
            "goal_tmpl+end": g_t + end,
            "shot_tmpl+goal": s_t + g_t + lull,
        }
        r = data[k].get("r")
        if r is not None:
            n = len(s["t"])
            for c in RESEARCH:
                v = np.asarray(r[c], float)
                v = np.r_[v, np.full(max(0, n - len(v)), v[-1])][:n]
                row[f"r:{c}"] = gc.rolling_rz(v)
        out[k] = row
    return out


def _after(v: np.ndarray, sec: float) -> np.ndarray:
    k = round(sec / gc.DT)
    c = np.r_[0.0, np.cumsum(v)]
    idx = np.arange(len(v))
    hi = np.clip(idx + k, 0, len(v))
    return np.asarray((c[hi] - c[idx]) / np.maximum(hi - idx, 1), dtype=np.float64)


def add_logreg(
    ser: dict[str, dict[str, np.ndarray]], segs: dict[str, dict[str, Any]], feats: list[str]
) -> None:
    """Logistic regression on the cue values (grid points 0 to 3 s after a shot are positive,
    points 15 s from every logged event negative), leave-one-game-out."""
    rows: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    for k, row in ser.items():
        x = np.column_stack([row[f] for f in feats])
        t = np.arange(len(x)) * gc.DT
        shots = [e["t"] for e in segs[k]["entries"] if e["kind"] in SHOT]
        allev = [e["t"] for e in segs[k]["entries"]]
        pos = np.zeros(len(t), bool)
        for g in shots:
            pos |= (t >= g) & (t <= g + 3)
        neg = np.ones(len(t), bool)
        for g in allev:
            neg &= np.abs(t - g) > 15
        m = pos | neg
        rows[k] = (x, pos[m], m)
    games = sorted({segs[k]["game"] for k in ser})
    for g in games:
        tr = [k for k in ser if segs[k]["game"] != g]
        xs = np.vstack([rows[k][0][rows[k][2]][:: se.STEP] for k in tr])
        ys = np.concatenate([rows[k][1][:: se.STEP] for k in tr]).astype(float)
        w = ev.logreg(xs, ys, l2=10.0, iters=50)
        for k in ser:
            if segs[k]["game"] == g:
                ser[k]["logreg"] = rows[k][0] @ w[:-1]


# --- measures -------------------------------------------------------------------------------------


def refs_of(segs: dict, stems: list[str], kinds: tuple[str, ...], dur: dict) -> dict:
    return {
        k: [
            e["t"]
            for e in segs[k]["entries"]
            if e["kind"] in kinds and EDGE_S <= e["t"] <= dur[k] - EDGE_S
        ]
        for k in stems
    }


def recall(
    ser: dict[str, np.ndarray], data: dict, refs: dict, stems: list[str], dur: dict
) -> dict[str, Any]:
    n = sum(len(refs[k]) for k in stems)
    row: dict[str, Any] = {"n": n}
    for r in RATES:
        hits, errs = 0, []
        for k in stems:
            t = data[k]["p"]["t"][:: se.STEP]
            kk = round(r * dur[k] / 60)
            h, e = se.match(se.peaks(t, ser[k][:: se.STEP], kk), refs[k])
            hits += h
            errs += e
        row[f"r{r}"] = hits / max(n, 1)
        if r == 2:
            row["err"] = (
                (float(np.median(errs)), float(np.subtract(*np.percentile(errs, [75, 25]))))
                if errs
                else (float("nan"), float("nan"))
            )
    return row


def random_row(refs: dict, stems: list[str], dur: dict, rng: np.random.Generator) -> dict:
    n = sum(len(refs[k]) for k in stems)
    row: dict[str, Any] = {"n": n}
    for r in RATES:
        h = sum(
            se.random_recall(dur[k], refs[k], round(r * dur[k] / 60), rng, 60)
            for k in stems
            if refs[k]
        )
        row[f"r{r}"] = h / max(n, 1)
    return row


def moment_auc(
    ser: dict[str, np.ndarray], segs: dict, stems: list[str], pos_k: tuple, neg_k: tuple
) -> float:
    pos, neg = [], []
    for k in stems:
        t = np.arange(len(ser[k])) * gc.DT
        for e in segs[k]["entries"]:
            m = (t >= e["t"] + HIT[0]) & (t <= e["t"] + HIT[1])
            if not m.any():
                continue
            v = float(ser[k][m].max())
            if e["kind"] in pos_k:
                pos.append(v)
            elif e["kind"] in neg_k:
                neg.append(v)
    return ev.auc(np.array(pos), np.array(neg)) if pos and neg else float("nan")


def log_help(
    ser: dict[str, np.ndarray],
    data: dict,
    segs: dict,
    stems: list[str],
    dur: dict,
    rate: int,
    offset_s: float,
    window_s: float,
    shift_s: float = 0.0,
) -> dict[str, float]:
    """With an official log: what the candidates at `rate` per minute are, and how often the
    suggestion (the logged shot nearest to the candidate's estimated shot time, at most
    `window_s` away, each shot suggested once) is the shot the candidate shows. `shift_s` moves
    the log (an alignment error)."""
    n_c = near_shot = near_turn = 0
    n_shots = suggested = right = 0
    for k in stems:
        t = data[k]["p"]["t"][:: se.STEP]
        cands = se.peaks(t, ser[k][:: se.STEP], round(rate * dur[k] / 60))
        ents = [e for e in segs[k]["entries"] if EDGE_S <= e["t"] <= dur[k] - EDGE_S]
        shots = [e["t"] for e in ents if e["kind"] in SHOT]
        turns = [e["t"] for e in ents if e["kind"] in NEG]
        n_c += len(cands)
        near_shot += sum(any(HIT[0] <= c - g <= HIT[1] for g in shots) for c in cands)
        near_turn += sum(
            any(HIT[0] <= c - g <= HIT[1] for g in turns)
            and not any(HIT[0] <= c - g <= HIT[1] for g in shots)
            for c in cands
        )
        n_shots += len(shots)
        pairs = sorted(
            (abs(c - offset_s - (g + shift_s)), i, j)
            for i, c in enumerate(cands)
            for j, g in enumerate(shots)
            if abs(c - offset_s - (g + shift_s)) <= window_s
        )
        used_c: set[int] = set()
        used_g: set[int] = set()
        for _, i, j in pairs:
            if i in used_c or j in used_g:
                continue
            used_c.add(i)
            used_g.add(j)
            suggested += 1
            right += HIT[0] <= cands[i] - shots[j] <= HIT[1]
    return {
        "candidates": n_c,
        "near_shot": near_shot / max(n_c, 1),
        "near_turnover": near_turn / max(n_c, 1),
        "shots": n_shots,
        "suggested": suggested / max(n_shots, 1),
        "suggested_right": right / max(n_shots, 1),
        "wrong_share": (suggested - right) / max(suggested, 1),
    }


def fmt(r: dict) -> str:
    return " / ".join(f"{r[f'r{x}']:.2f}" for x in RATES)


def short(g: str) -> str:
    return (
        g.replace("CH_NLB_", "")
        .replace("CH_Cup_", "Cup ")
        .replace("SGWaedenswilHorgen", "SGWH")
        .replace("_", " ")
        .strip()
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("labels", type=Path, nargs="?", default=ROOT / "ml/data/segment_labels")
    ap.add_argument("--obs", type=Path, nargs="*", default=[])
    ap.add_argument("--cache", type=Path, nargs="*", default=[])
    ap.add_argument("--store", type=Path)
    ap.add_argument("--shift", type=float, default=1.0, help="shot template centre - log time")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--goal-labels", type=Path, help="goals_raw/labels.json: goal template LOGO")
    ap.add_argument("--goal-cache", type=Path, help="goals_raw/cache (with --goal-labels)")
    a = ap.parse_args()
    segs = load_segments(a.labels)
    data = load_all(segs, a.obs, a.cache, a.store)
    stems = [k for k in segs if data[k]["src"] != "none"]
    missing = [k for k in segs if data[k]["src"] == "none"]
    dur = {k: float(data[k]["p"]["t"][-1]) for k in stems}
    counts = defaultdict(int)
    for k in stems:
        for e in segs[k]["entries"]:
            if EDGE_S <= e["t"] <= dur[k] - EDGE_S:
                counts[e["kind"]] += 1
    games = sorted({segs[k]["game"] for k in stems})
    src = {s: sum(1 for k in stems if data[k]["src"] == s) for s in ("observe", "research")}
    print(
        f"{len(stems)} segments with signals ({sum(dur.values()) / 60:.1f} min, {len(games)} games;"
        f" sources {src}), without: {len(missing)} {missing}"
    )
    print(f"entries: {dict(sorted(counts.items()))}")
    goal_tm = (
        goal_templates(a.goal_labels, a.goal_cache, set(games))
        if a.goal_labels and a.goal_cache
        else None
    )
    ser = scores(data, segs, stems, a.shift, goal_tm)
    base = ["goal_tmpl", "lull", "shot_tmpl", "end", "pan_after"]
    add_logreg(ser, segs, base)
    for k in stems:
        ser[k]["logreg+goal"] = gc.rolling_rz(ser[k]["logreg"]) + ser[k]["goal"]
    rng = np.random.default_rng(0)
    results: dict[str, Any] = {
        "segments": len(stems),
        "minutes": sum(dur.values()) / 60,
        "counts": dict(counts),
        "classes": {},
        "games": {},
        "moments": {},
    }
    names = list(next(iter(ser.values())))
    for cname, kinds in CLASSES.items():
        refs = refs_of(segs, stems, kinds, dur)
        rnd = random_row(refs, stems, dur, rng)
        print(
            f"\n### {cname} ({rnd['n']}), recall @ {' / '.join(map(str, RATES))} per min, "
            "candidate - event at 2/min"
        )
        print(f"| score | recall | timing |\n|---|---|---|\n| random | {fmt(rnd)} | |")
        res = {"random": rnd}
        for nm in names:
            sub = [k for k in stems if nm in ser[k]]
            if len(sub) < len(stems):
                continue
            r = recall({k: ser[k][nm] for k in sub}, data, refs, sub, dur)
            res[nm] = r
            print(f"| {nm} | {fmt(r)} | {r['err'][0]:+.1f} s ({r['err'][1]:.1f}) |")
        results["classes"][cname] = res
    # research cues only where the research cache has people: separate table on that subset
    rsub = [k for k in stems if "r:pan_rev" in ser[k]]
    if rsub:
        refs = refs_of(segs, rsub, SHOT, dur)
        n_r = sum(len(v) for v in refs.values())
        print(f"\n### shots, research subset ({len(rsub)} segments, {n_r} shots)")
        print(
            f"| score | recall |\n|---|---|\n| random | {fmt(random_row(refs, rsub, dur, rng))} |"
        )
        for nm in ["goal", "shot_tmpl", "end", *[f"r:{c}" for c in RESEARCH]]:
            r = recall({k: ser[k][nm] for k in rsub}, data, refs, rsub, dur)
            print(f"| {nm} | {fmt(r)} |")
    print("\n### at the labelled moments: AUC of the best score 3 s before to 8 s after")
    print("| score | shots vs turnovers | saves+misses vs turnovers | goals vs saves+misses |")
    print("|---|---|---|---|")
    for nm in names:
        if any(nm not in ser[k] for k in stems):
            continue
        s_ = {k: ser[k][nm] for k in stems}
        a1 = moment_auc(s_, segs, stems, SHOT, NEG)
        a2 = moment_auc(s_, segs, stems, SAVE + MISS, NEG)
        a3 = moment_auc(s_, segs, stems, GOAL, SAVE + MISS)
        results["moments"][nm] = [a1, a2, a3]
        print(f"| {nm} | {a1:.2f} | {a2:.2f} | {a3:.2f} |")
    print(
        "\n### with an official log: candidates and suggestions (logged shot nearest the "
        "estimated shot time, peak - 1.5 s, within 8 s)"
    )
    print(
        "| score | rate | candidates | near a shot | near a turnover only | shots suggested | "
        "suggested, right candidate | wrong suggestions | same, log 10 s off |\n"
        "|---|---|---|---|---|---|---|---|---|"
    )
    results["log_help"] = {}
    for nm in ("goal", "shot_tmpl+goal", "logreg+goal"):
        for rate in (2, 4):
            h = log_help({k: ser[k][nm] for k in stems}, data, segs, stems, dur, rate, 1.5, 8.0)
            h10 = log_help(
                {k: ser[k][nm] for k in stems}, data, segs, stems, dur, rate, 1.5, 8.0, 10.0
            )
            results["log_help"][f"{nm}@{rate}"] = {"exact": h, "log_10s_late": h10}
            print(
                f"| {nm} | {rate} | {h['candidates']} | {h['near_shot']:.2f} | "
                f"{h['near_turnover']:.2f} | {h['suggested']:.2f} | {h['suggested_right']:.2f} | "
                f"{h['wrong_share']:.2f} | {h10['suggested_right']:.2f} / {h10['wrong_share']:.2f} |"
            )
    print("\n### per game, all shots, recall @ 1 / 2 / 4 / 6 per min")
    print(
        "| game | shots (goals / saves / misses) / min | goal score | shot_tmpl | logreg+goal |"
        " random |\n|---|---|---|---|---|---|"
    )
    for g in games:
        ks = [k for k in stems if segs[k]["game"] == g]
        refs = refs_of(segs, ks, SHOT, dur)
        cnt = [sum(len(refs_of(segs, ks, kk, dur)[k]) for k in ks) for kk in (GOAL, SAVE, MISS)]
        r1 = recall({k: ser[k]["goal"] for k in ks}, data, refs, ks, dur)
        r2 = recall({k: ser[k]["shot_tmpl"] for k in ks}, data, refs, ks, dur)
        r3 = recall({k: ser[k]["logreg+goal"] for k in ks}, data, refs, ks, dur)
        rr = random_row(refs, ks, dur, rng)
        results["games"][g] = {
            "counts": cnt,
            "goal": r1,
            "shot_tmpl": r2,
            "logreg+goal": r3,
            "random": rr,
            "minutes": sum(dur[k] for k in ks) / 60,
        }
        print(
            f"| {short(g)} | {r1['n']} ({cnt[0]} / {cnt[1]} / {cnt[2]}) / "
            f"{sum(dur[k] for k in ks) / 60:.0f} | {fmt(r1)} | {fmt(r2)} | {fmt(r3)} | {fmt(rr)} |"
        )
    if a.out:
        a.out.write_text(json.dumps(results, indent=1, default=float))


if __name__ == "__main__":
    main()
