"""usage: uv run --project packages/vision python ml/integration/goal_offset_dev.py ml/gold/data/shot_release_dev_llm.json <dev observations dir>

Peak - goal on the frozen dev release labels (ml/gold/data/shot_release_dev_llm.json, LLM, not
the end test). Fixed before running: goals = kind goal / penalty_goal / empty_goal with status ok;
candidates = today's goal candidates (goalcandidates.from_observations, all rates, no clock) per
dev segment; per goal the candidate whose peak (t_ms) lies within release - 3 s to release + 12 s,
nearest to release + 1.5 s. Reported: peak - release (median, quartiles), bootstrap over games of
the median. «klare Abweichung»: median at least 1.5 s away from GOAL_OFFSET_S (1.5 s) and the 95 %
CI not containing 1.5 s."""

import collections
import json
import sys
from pathlib import Path

import numpy as np

from handball_vision import observe as ob
from handball_vision.goalcandidates import GOAL_OFFSET_S, from_observations
from handball_vision.motion import CameraMotion

LAB = Path(sys.argv[1])
OBS = Path(sys.argv[2])
d = json.loads(LAB.read_text())
goals = [
    s
    for s in d["shots"]
    if s["kind"] in ("goal", "penalty_goal", "empty_goal")
    and s["status"] == "ok"
    and s["t_s"] is not None
]
by_seg = collections.defaultdict(list)
for g in goals:
    by_seg[g["seg"]].append(g)
rows, unmatched = [], 0
for seg, gs in sorted(by_seg.items()):
    m = CameraMotion.load(OBS / seg / "motion.npz")
    obs = ob.load_observations(OBS / seg / "observations.npz", m)
    gc = from_observations(obs, play=None)
    peaks = [c["t_ms"] / 1000 for c in (gc or {}).get("candidates", [])]
    for g in gs:
        r = g["t_s"]
        near = [p for p in peaks if r - 3 <= p <= r + 12]
        if not near:
            unmatched += 1
            continue
        p = min(near, key=lambda p: abs(p - (r + 1.5)))
        rows.append((seg.rsplit("_s", 1)[0], p - r))
v = np.array([x for _, x in rows])
games = sorted({g for g, _ in rows})
rng = np.random.default_rng(0)
boots = []
for _ in range(2000):
    pick = [games[i] for i in rng.integers(0, len(games), len(games))]
    boots.append(np.median([x for gm in pick for g, x in rows if g == gm]))
med = float(np.median(v))
ci = [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))]
res = {
    "goals": len(goals),
    "matched": len(rows),
    "unmatched": unmatched,
    "games": len(games),
    "peak_minus_release_s": {
        "median": round(med, 2),
        "q25": round(float(np.percentile(v, 25)), 2),
        "q75": round(float(np.percentile(v, 75)), 2),
        "ci95_median": [round(ci[0], 2), round(ci[1], 2)],
    },
    "goal_offset_s_today": GOAL_OFFSET_S,
    "klare_abweichung": bool(
        abs(med - GOAL_OFFSET_S) >= 1.5 and not (ci[0] <= GOAL_OFFSET_S <= ci[1])
    ),
}
print(json.dumps(res, indent=1))
