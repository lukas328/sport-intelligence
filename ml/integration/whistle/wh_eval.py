# ruff: noqa: N806, N812
"""Whistle detector against LLM whistle labels (pre-registered before the labels were seen).
merge: label whistles of pass A and B match when their starts are within MATCH_S; matched ones
are truth; one-pass-only whistles go to a third look (third.json: clip -> list of {start, end,
whistle: bool}) and count when it says whistle. Horns are kept apart (not whistles).
score: detector events (whistle.detect) on the product's 8 kHz audio and on 16 kHz: a detection
is right when its start is within MATCH_S of a truth whistle start (one-to-one, greedy by time).
Precision, recall per clip and pooled. Dead seconds (needs inplay truth): a second counts as
dead by the whistle rule when it starts within DEAD_AFTER_S after a detected whistle.
usage: python wh_eval.py merge|score"""

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import whistle as W

D = Path(__file__).parent
MATCH_S = 0.5
DEAD_AFTER_S = 5.0
CLIPS = {"mue": 480, "lei": 600}
AUDIO = {
    ("mue", 8000): "a1.wav",
    ("mue", 16000): "mue_16000.wav",
    ("lei", 8000): "lei_8000.wav",
    ("lei", 16000): "lei_16000.wav",
}


def pair(a, b, tol=MATCH_S):
    used, out = set(), []
    for i, x in enumerate(a):
        j = min(
            (k for k in range(len(b)) if k not in used and abs(b[k] - x) <= tol),
            key=lambda k: abs(b[k] - x),
            default=None,
        )
        if j is not None:
            used.add(j)
            out.append((i, j))
    return out


def merge():
    third_p = D / "passC/third.json"
    third = json.loads(third_p.read_text()) if third_p.exists() else None
    truth, todo = {}, {}
    for c in CLIPS:
        A = [e for e in json.loads((D / f"passA/{c}.json").read_text()) if e["kind"] == "whistle"]
        B = [e for e in json.loads((D / f"passB/{c}.json").read_text()) if e["kind"] == "whistle"]
        pr = pair([e["start"] for e in A], [e["start"] for e in B])
        both = [
            {
                "start": round((A[i]["start"] + B[j]["start"]) / 2, 2),
                "end": round((A[i]["end"] + B[j]["end"]) / 2, 2),
                "source": "A+B",
            }
            for i, j in pr
        ]
        ia, ib = {i for i, _ in pr}, {j for _, j in pr}
        single = [dict(A[i], p="A") for i in range(len(A)) if i not in ia] + [
            dict(B[j], p="B") for j in range(len(B)) if j not in ib
        ]
        todo[c] = sorted(
            [{"start": e["start"], "end": e["end"]} for e in single], key=lambda e: e["start"]
        )
        if third is not None:
            for e in third.get(c, []):
                if e.get("whistle"):
                    both.append({"start": e["start"], "end": e["end"], "source": "single+C"})
        truth[c] = sorted(both, key=lambda e: e["start"])
        print(c, "A", len(A), "B", len(B), "matched", len(pr), "single", len(single))
    (D / "third_todo.json").write_text(json.dumps(todo, indent=1))
    if third is not None:
        raw = json.dumps(truth, sort_keys=True).encode()
        (D / "wh_truth.json").write_bytes(raw)
        (D / "wh_truth.sha256").write_text(hashlib.sha256(raw).hexdigest() + "  wh_truth.json\n")
        print("frozen", hashlib.sha256(raw).hexdigest(), {c: len(v) for c, v in truth.items()})


def score():
    raw = (D / "wh_truth.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == (D / "wh_truth.sha256").read_text().split()[0]
    truth = json.loads(raw)
    res = {
        "truth_sha256": hashlib.sha256(raw).hexdigest(),
        "truth": {c: len(v) for c, v in truth.items()},
    }
    for sr in (8000, 16000):
        tot = {"det": 0, "tp": 0, "truth": 0}
        for c in CLIPS:
            x, r = W.load_wav(D / AUDIO[(c, sr)])
            det = [e[0] for e in W.detect(x, r)]
            t = [e["start"] for e in truth[c]]
            tp = len(pair(det, t))
            res[f"{c}_{sr}"] = {
                "detected": len(det),
                "truth": len(t),
                "precision": round(tp / max(1, len(det)), 3),
                "recall": round(tp / max(1, len(t)), 3),
            }
            tot["det"] += len(det)
            tot["tp"] += tp
            tot["truth"] += len(t)
        res[f"pooled_{sr}"] = {
            "precision": round(tot["tp"] / max(1, tot["det"]), 3),
            "recall": round(tot["tp"] / max(1, tot["truth"]), 3),
            **tot,
        }
    print(json.dumps(res, indent=1))
    (D / "wh_eval.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    {"merge": merge, "score": score}[sys.argv[1]]()
