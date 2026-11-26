# ruff: noqa: N812
"""Goal candidates with and without «whistle in the window after the candidate». Fixed before
the goal labels were seen:
- candidates: the product's goal_candidates (all rates); a candidate hits a truth goal when its
  goal_ms is within HIT_S of the goal (one-to-one, nearest first).
- whistles: round-2 detector (whistle2, setting chosen on mue for the whistle task), 16 kHz and
  8 kHz.
- gate: keep a candidate when at least K whistles start in [goal_ms + A, goal_ms + B].
- (A, B, K) chosen on mue ONLY: the highest precision over all candidates that keeps all but at
  most one of the candidates' hits; ties -> more hits, then the smaller window. Then ONE score on
  lei, no change afterwards.
- «klarer Gewinn» on lei: precision at least 15 points higher than without the gate, and at most
  10 % of the hit goals lost. Reported also for the default rate (rate <= 2).
Truth: goals_truth.json (LLM labels, two passes, frozen)."""

import hashlib
import itertools
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "aud"))
import whistle as W
import whistle2 as W2

D = Path(__file__).parent
AUD = D.parent / "aud"
HIT_S = 6.0
GRID = {"a": [0.0, 3.0, 5.0], "b": [15.0, 30.0, 45.0], "k": [1, 2]}
AUDIO = {
    ("mue", 16000): "mue_16000.wav",
    ("mue", 8000): "a1.wav",
    ("lei", 16000): "lei_16000.wav",
    ("lei", 8000): "lei_8000.wav",
}


def hits(cands, goals):
    used, n = set(), 0
    for c in sorted(cands, key=lambda c: c["goal_ms"]):
        g = min(
            (
                i
                for i in range(len(goals))
                if i not in used and abs(goals[i] - c["goal_ms"] / 1000) <= HIT_S
            ),
            key=lambda i: abs(goals[i] - c["goal_ms"] / 1000),
            default=None,
        )
        if g is not None:
            used.add(g)
            n += 1
    return n


def score(cands, goals):
    h = hits(cands, goals)
    return {
        "candidates": len(cands),
        "hits": h,
        "goals": len(goals),
        "precision": round(h / max(1, len(cands)), 3),
        "recall": round(h / max(1, len(goals)), 3),
    }


def gate(cands, whistles, a, b, k):
    return [
        c
        for c in cands
        if sum(c["goal_ms"] / 1000 + a <= w <= c["goal_ms"] / 1000 + b for w in whistles) >= k
    ]


def whistles(clip, sr):
    ch = json.loads((AUD / "wh2_eval.json").read_text())[str(sr)]["chosen_on_mue"]
    x, r = W.load_wav(AUD / AUDIO[(clip, sr)])
    return [e[0] for e in W2.detect(x, r, tuple(ch["band_hz"]), ch["c_db"], ch["min_s"])]


def main():
    raw = (D / "goals_truth.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == (D / "goals_truth.sha256").read_text().split()[0]
    truth = {c: [g["t"] for g in v] for c, v in json.loads(raw).items()}
    cands = {
        c: json.loads((D / c / "goal_candidates.json").read_text())["candidates"]
        for c in ("mue", "lei")
    }
    res = {"truth_sha256": hashlib.sha256(raw).hexdigest()}
    for sr in (16000, 8000):
        ws = {c: whistles(c, sr) for c in ("mue", "lei")}
        base_m = score(cands["mue"], truth["mue"])
        best = None
        for a, b, k in itertools.product(GRID["a"], GRID["b"], GRID["k"]):
            s = score(gate(cands["mue"], ws["mue"], a, b, k), truth["mue"])
            if s["hits"] < base_m["hits"] - 1:
                continue
            key = (s["precision"], s["hits"], -(b - a))
            if best is None or key > best[0]:
                best = (key, (a, b, k), s)
        _, (a, b, k), sm = best
        out = {
            "chosen_on_mue": {"a_s": a, "b_s": b, "k": k},
            "mue": {"without": base_m, "with": sm},
        }
        for name, sel in (("all", lambda c: True), ("default_rate", lambda c: c["rate"] <= 2)):
            cl = [c for c in cands["lei"] if sel(c)]
            wo, wi = score(cl, truth["lei"]), score(gate(cl, ws["lei"], a, b, k), truth["lei"])
            out[f"lei_{name}"] = {"without": wo, "with": wi}
        wo, wi = out["lei_all"]["without"], out["lei_all"]["with"]
        out["klarer_gewinn"] = bool(
            wi["precision"] - wo["precision"] >= 0.15 and wi["hits"] >= 0.9 * wo["hits"]
        )
        res[str(sr)] = out
    print(json.dumps(res, indent=1))
    (D / "goal_whistle.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
