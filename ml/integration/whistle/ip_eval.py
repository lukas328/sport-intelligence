# ruff: noqa: N812
"""Whistle as a «ball not in play» signal on LLM in-play labels (pre-registered before scoring).
merge: seconds where in-play passes A and B agree are truth (disagreements left out, reported).
rule: a second counts as dead when it starts within DEAD_AFTER_S after a detected whistle start
(round 1 whistle.detect and round 2 whistle2 with the setting chosen on mue; 8 and 16 kHz). Scores: precision / recall of dead, pooled over
both clips, 20 s block bootstrap CI of precision. «brauchbar»: precision of dead at least 0.70
with the CI lower bound at least 0.60 (motion and clock reached 0.2 to 0.5 on Horgen).
usage: python ip_eval.py"""

import collections
import hashlib
import itertools
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import whistle as W
import whistle2 as W2
from wh_eval import AUDIO, CLIPS

D = Path(__file__).parent
DEAD_AFTER_S = 5.0


def secs(segs, n):
    out = [None] * n
    for s in segs:
        for t in range(n):
            if s["start"] <= t + 0.5 < s["end"]:
                out[t] = s["state"]
    return out


def main():
    truth = {}
    for c, n in CLIPS.items():
        a = secs(json.loads((D / f"ipA/{c}.json").read_text()), n)
        b = secs(json.loads((D / f"ipB/{c}.json").read_text()), n)
        truth[c] = [x if x == y else None for x, y in zip(a, b, strict=True)]
        print(
            c,
            "agree",
            sum(x is not None for x in truth[c]),
            "of",
            n,
            "dead",
            truth[c].count("dead"),
        )
    raw = json.dumps(truth, sort_keys=True).encode()
    (D / "ip_truth.json").write_bytes(raw)
    res = {"ip_truth_sha256": hashlib.sha256(raw).hexdigest(), "dead_after_s": DEAD_AFTER_S}
    chosen = json.loads((D / "wh2_eval.json").read_text())
    for sr, det_name in itertools.product((8000, 16000), ("round1", "round2")):
        rows = []
        for c, n in CLIPS.items():
            x, r = W.load_wav(D / AUDIO[(c, sr)])
            if det_name == "round1":
                starts = [e[0] for e in W.detect(x, r)]
            else:
                ch = chosen[str(sr)]["chosen_on_mue"]
                starts = [
                    e[0] for e in W2.detect(x, r, tuple(ch["band_hz"]), ch["c_db"], ch["min_s"])
                ]
            for t in range(n):
                if truth[c][t] is None:
                    continue
                flag = any(s <= t < s + DEAD_AFTER_S for s in starts)
                rows.append((c, t, truth[c][t] == "dead", flag))
        tp = sum(d and f for _, _, d, f in rows)
        fl = sum(f for *_, f in rows)
        dd = sum(d for _, _, d, _ in rows)
        blocks = collections.defaultdict(list)
        for c, t, d, f in rows:
            if f:
                blocks[(c, t // 20)].append(d)
        keys = list(blocks)
        rng = np.random.default_rng(0)
        boots = []
        for _ in range(2000):
            v = [
                x
                for k in (keys[i] for i in rng.integers(0, len(keys), len(keys)))
                for x in blocks[k]
            ]
            boots.append(np.mean(v) if v else 0.0)
        prec = tp / max(1, fl)
        ci = [
            round(float(np.percentile(boots, 2.5)), 3),
            round(float(np.percentile(boots, 97.5)), 3),
        ]
        res[f"{det_name}_{sr}"] = {
            "seconds": len(rows),
            "dead": dd,
            "flagged": fl,
            "precision": round(prec, 3),
            "precision_ci95": ci,
            "recall": round(tp / max(1, dd), 3),
            "brauchbar": bool(prec >= 0.70 and ci[0] >= 0.60),
        }
    print(json.dumps(res, indent=1))
    (D / "ip_eval.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
