# ruff: noqa: N812
"""«Ball nicht im Spiel» from whistle + motion. Fixed before running:
- whistles: round-2 detector, 16 kHz (whistle2, setting chosen on mue for the whistle task).
- motion: the product's people speed (goalcandidates.signals "speed", canvas, no court needed),
  mean per second, then a 3 s rolling mean; "still" = below the clip's own Q-th percentile.
- rule C(W, Q): a second is dead when a whistle started within the last W s AND the players are
  still. Also reported: motion alone M(Q), whistle alone (W s after a whistle).
- (W, Q) chosen on mue ONLY (W in {5, 10, 15, 20} s, Q in {20, 30, 40, 50}): highest F1 of dead.
  Then ONE score on lei.
- «brauchbar» on lei: precision of dead at least 0.70 with the 20 s block bootstrap CI lower
  bound at least 0.60 (the bar of the whistle-only rule).
Truth: aud/ip_truth.json (LLM in-play labels, seconds where both passes agree)."""

import collections
import itertools
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "aud"))
import whistle as W
import whistle2 as W2

from handball_vision import observe as ob
from handball_vision.goalcandidates import inputs_from_observations, signals
from handball_vision.motion import CameraMotion

D = Path(__file__).parent
AUD = D.parent / "aud"
GRID = {"w": [5.0, 10.0, 15.0, 20.0], "q": [20, 30, 40, 50]}
N = {"mue": 480, "lei": 600}


def speed_per_second(clip):
    m = CameraMotion.load(D / clip / "motion.npz")
    obs = ob.load_observations(D / clip / "observations.npz", m)
    s = signals(*inputs_from_observations(obs))
    sp = s["speed"]
    t = s["t"]
    per = np.array(
        [
            np.nanmean(sp[(t >= k) & (t < k + 1)]) if np.any((t >= k) & (t < k + 1)) else np.nan
            for k in range(N[clip])
        ]
    )
    return np.array([np.nanmean(per[max(0, k - 1) : k + 2]) for k in range(N[clip])])


def whistles(clip):
    ch = json.loads((AUD / "wh2_eval.json").read_text())["16000"]["chosen_on_mue"]
    x, r = W.load_wav(AUD / f"{clip}_16000.wav")
    return [e[0] for e in W2.detect(x, r, tuple(ch["band_hz"]), ch["c_db"], ch["min_s"])]


def flags(sp, ws, w, q, mode):
    thr = np.nanpercentile(sp, q)
    still = [bool(np.isfinite(v) and v < thr) for v in sp]
    after = [any(s <= k < s + w for s in ws) for k in range(len(sp))]
    return {
        "combo": [a and b for a, b in zip(after, still, strict=True)],
        "motion": still,
        "whistle": after,
    }[mode]


def score(f, truth, clip, boot=False):
    rows = [(k, truth[k] == "dead", f[k]) for k in range(len(f)) if truth[k] is not None]
    tp = sum(d and x for _, d, x in rows)
    fl = sum(x for *_, x in rows)
    dd = sum(d for _, d, _ in rows)
    p, r = tp / max(1, fl), tp / max(1, dd)
    out = {
        "flagged": fl,
        "dead": dd,
        "precision": round(p, 3),
        "recall": round(r, 3),
        "f1": round(2 * p * r / max(1e-9, p + r), 3),
    }
    if boot:
        blocks = collections.defaultdict(list)
        for k, d, x in rows:
            if x:
                blocks[k // 20].append(d)
        keys = list(blocks)
        rng = np.random.default_rng(0)
        bs = []
        for _ in range(2000):
            v = [
                y
                for kk in (keys[i] for i in rng.integers(0, len(keys), len(keys)))
                for y in blocks[kk]
            ]
            bs.append(np.mean(v) if v else 0.0)
        out["precision_ci95"] = [
            round(float(np.percentile(bs, 2.5)), 3),
            round(float(np.percentile(bs, 97.5)), 3),
        ]
    return out


def main():
    truth = json.loads((AUD / "ip_truth.json").read_text())
    sp = {c: speed_per_second(c) for c in N}
    ws = {c: whistles(c) for c in N}
    best = None
    for w, q in itertools.product(GRID["w"], GRID["q"]):
        s = score(flags(sp["mue"], ws["mue"], w, q, "combo"), truth["mue"], "mue")
        if best is None or s["f1"] > best[0]["f1"]:
            best = (s, (w, q))
    sm, (w, q) = best
    res = {"chosen_on_mue": {"w_s": w, "q": q}, "mue_combo": sm}
    for mode in ("combo", "motion", "whistle"):
        res[f"lei_{mode}"] = score(
            flags(sp["lei"], ws["lei"], w, q, mode), truth["lei"], "lei", boot=True
        )
    lc = res["lei_combo"]
    res["brauchbar"] = bool(lc["precision"] >= 0.70 and lc["precision_ci95"][0] >= 0.60)
    print(json.dumps(res, indent=1))
    (D / "dead_combo.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
