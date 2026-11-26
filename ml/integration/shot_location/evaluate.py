"""Score both shot-location methods against the frozen LLM truth (truth.json, hash checked).
Pre-registered decision «klar besser»: ball path (with today's rule as fallback) has a median
error at least 1.0 m lower than today's, the paired bootstrap 95 % CI of the difference
excludes 0, zone accuracy is not lower, and coverage is not lower."""

import hashlib
import json
import math
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import methods as m
from handball_api_free_zones import zone

SP = Path(os.environ["SHOT_LOC_DIR"])  # wo/: clips and out_h1, out_h2; wl/: labels
raw = (SP / "wl" / "truth.json").read_bytes()
digest = hashlib.sha256(raw).hexdigest()
assert digest == (SP / "wl" / "truth.sha256").read_text().split()[0], "truth changed after freezing"
truth = json.loads(raw)
TEAM = {"yellow": "home", "red": "away"}
rows = []
for h, shots in truth.items():
    clip = m.Clip(SP / "wo" / f"out_{h}")
    for s in shots:
        for off in (1.5, 3.0):
            p = m.predict(clip, s["release_t"], TEAM[s["team"]], off)
            gx = p["gx"]
            tc = s["court"]
            if gx is None:
                tn = None
            else:
                tn = (tc[0], tc[1]) if gx == 40.0 else (40.0 - tc[0], 20.0 - tc[1])
            rows.append(
                {
                    "clip": h,
                    "t": s["release_t"],
                    "kind": s["kind"],
                    "offset": off,
                    "truth": tn,
                    **{k: p[k] for k in ("today", "ball", "ball_or_today")},
                    "ball_release_t": p.get("ball_release_t"),
                }
            )


def truth_zone(r):
    if r["kind"] == "penalty":
        return "m7"
    return zone(*r["truth"])


def pred_zone(q):
    if math.dist(q, (33.0, 10.0)) <= 1.5:
        return "m7"
    return zone(*q)


rng = np.random.default_rng(0)
res = {"truth_sha256": digest, "n_shots": sum(len(v) for v in truth.values()), "by_offset": {}}
for off in (1.5, 3.0):
    R = [r for r in rows if r["offset"] == off and r["truth"] is not None]
    out = {}
    for meth in ("today", "ball", "ball_or_today"):
        err = [math.dist(r[meth], r["truth"]) if r[meth] else None for r in R]
        cov = [e is not None for e in err]
        zr = [r for r in R if r[meth] and r["kind"] != "fast_break"]
        zacc = [pred_zone(r[meth]) == truth_zone(r) for r in zr]
        out[meth] = {
            "coverage": round(float(np.mean(cov)), 3),
            "n": len(R),
            "median_err_m": round(float(np.median([e for e in err if e is not None])), 2)
            if any(cov)
            else None,
            "zone_acc": round(float(np.mean(zacc)), 3) if zacc else None,
            "zone_n": len(zacc),
        }
    # paired: shots both today and ball_or_today cover
    P = [r for r in R if r["today"] and r["ball_or_today"]]
    d = np.array(
        [math.dist(r["ball_or_today"], r["truth"]) - math.dist(r["today"], r["truth"]) for r in P]
    )
    et = np.array([math.dist(r["today"], r["truth"]) for r in P])
    eb = np.array([math.dist(r["ball_or_today"], r["truth"]) for r in P])
    boots = []
    for _ in range(2000):
        i = rng.integers(0, len(P), len(P))
        boots.append(np.median(eb[i]) - np.median(et[i]))
    out["paired"] = {
        "n": len(P),
        "median_diff_m": round(float(np.median(eb) - np.median(et)), 2),
        "ci95": [
            round(float(np.percentile(boots, 2.5)), 2),
            round(float(np.percentile(boots, 97.5)), 2),
        ],
    }
    PB = [r for r in R if r["ball"] and r["today"]]
    out["paired_ball_only"] = {
        "n": len(PB),
        "median_today_m": round(
            float(np.median([math.dist(r["today"], r["truth"]) for r in PB])), 2
        )
        if PB
        else None,
        "median_ball_m": round(float(np.median([math.dist(r["ball"], r["truth"]) for r in PB])), 2)
        if PB
        else None,
    }
    t, b = out["today"], out["ball_or_today"]
    out["klar_besser"] = bool(
        out["paired"]["median_diff_m"] <= -1.0
        and out["paired"]["ci95"][1] < 0
        and (b["zone_acc"] or 0) >= (t["zone_acc"] or 0)
        and b["coverage"] >= t["coverage"]
    )
    res["by_offset"][str(off)] = out
res["rows"] = rows
(SP / "wo" / "shot_location_eval.json").write_text(json.dumps(res, indent=1))
print(json.dumps({k: v for k, v in res.items() if k != "rows"}, indent=1))
