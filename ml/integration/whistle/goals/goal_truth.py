"""Goal truth from two LLM passes: goals within MATCH_S in both passes count (mean time);
one-pass goals count when the third look (gC/<clip>.json) says goal (time: mean of that pass and
the third look). Frozen as goals_truth.json + sha256."""

import hashlib
import json
from pathlib import Path

D = Path(__file__).parent
MATCH_S = 3.0
truth, log = {}, []
for c in ("mue", "lei"):
    a = json.loads((D / f"gA/{c}.json").read_text())
    b = json.loads((D / f"gB/{c}.json").read_text())
    third_p = D / f"gC/{c}.json"
    third = json.loads(third_p.read_text()) if third_p.exists() else []
    used, out = set(), []
    for x in a:
        j = min(
            (k for k in range(len(b)) if k not in used and abs(b[k]["t"] - x["t"]) <= MATCH_S),
            key=lambda k: abs(b[k]["t"] - x["t"]),
            default=None,
        )
        if j is not None:
            used.add(j)
            out.append({"t": round((x["t"] + b[j]["t"]) / 2, 2), "source": "A+B"})
        else:
            log.append((c, "A only", x["t"]))
            hit = [y for y in third if abs(y["t_given"] - x["t"]) <= 0.5 and y["goal"]]
            if hit:
                out.append({"t": round((x["t"] + (hit[0]["t"] or x["t"])) / 2, 2), "source": "A+C"})
    for k, y in enumerate(b):
        if k in used:
            continue
        log.append((c, "B only", y["t"]))
        hit = [z for z in third if abs(z["t_given"] - y["t"]) <= 0.5 and z["goal"]]
        if hit:
            out.append({"t": round((y["t"] + (hit[0]["t"] or y["t"])) / 2, 2), "source": "B+C"})
    truth[c] = sorted(out, key=lambda g: g["t"])
raw = json.dumps(truth, indent=1, sort_keys=True).encode()
(D / "goals_truth.json").write_bytes(raw)
(D / "goals_truth.sha256").write_text(hashlib.sha256(raw).hexdigest() + "  goals_truth.json\n")
print(hashlib.sha256(raw).hexdigest(), {c: [g["t"] for g in v] for c, v in truth.items()})
for line in log:
    print(*line)
