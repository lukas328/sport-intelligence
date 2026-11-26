"""Score-reader goals against the frozen goal truth (rule fixed in the plan before the run).

python ml/integration/scoreboard/evaluate.py REPO_ROOT DIR_WITH_<clip>_sb.json
"""

import json
import sys
from pathlib import Path

W = Path(sys.argv[1])
SB = Path(sys.argv[2])
truth = json.loads((W / "ml/integration/whistle/goals/goals_truth.json").read_text())
out = {}


def match(a, b, lo, hi):
    """greedy nearest: a events, b truth; hit if lo <= a - b <= hi"""
    pairs = sorted(
        (abs(x - y), i, j) for i, x in enumerate(a) for j, y in enumerate(b) if lo <= x - y <= hi
    )
    ua, ub = set(), set()
    for _, i, j in pairs:
        if i in ua or j in ub:
            continue
        ua.add(i)
        ub.add(j)
    return ua, ub


for c in ("mue", "lei"):
    r = json.loads((SB / f"{c}_sb.json").read_text())
    if r["source"] == "overlay":
        goals = [g["t_ms"] / 1000 for g in (r["overlay"] or {}).get("goals") or []]
        reads = r.get("score_reads")
    else:
        goals = [g["t_ms"] / 1000 for g in (r["board"] or {}).get("goals") or []]
        reads = (r["board"] or {}).get("readings")
    t = [g["t"] for g in truth[c]]
    ug, ut = match(goals, t, -5, 60)
    cands = json.loads((W / f"ml/integration/whistle/goals/goal_candidates_{c}.json").read_text())[
        "candidates"
    ]
    gm = [x["goal_ms"] / 1000 for x in cands]
    hit_all, _ = match(gm, t, -6, 6)
    conf = [i for i, x in enumerate(gm) if any(-10 <= g - x <= 60 for g in goals)]
    hit_conf = [i for i in conf if i in hit_all]
    found_conf = len({j for j, y in enumerate(t) if any(abs(gm[i] - y) <= 6 for i in conf)})
    found_all = len({j for j, y in enumerate(t) if any(abs(g - y) <= 6 for g in gm)})
    out[c] = {
        "source": r["source"],
        "reads": reads,
        "board_goals": len(goals),
        "truth": len(t),
        "precision": round(len(ug) / max(1, len(goals)), 3),
        "recall": round(len(ut) / len(t), 3),
        "goal_times": [round(x, 1) for x in goals],
        "truth_times": t,
        "cands_all": {
            "n": len(gm),
            "precision": round(len(hit_all) / max(1, len(gm)), 3),
            "recall": round(found_all / len(t), 3),
        },
        "cands_confirmed": {
            "n": len(conf),
            "precision": round(len(hit_conf) / max(1, len(conf)), 3),
            "recall": round(found_conf / len(t), 3),
        },
    }
print(json.dumps(out, indent=1))
