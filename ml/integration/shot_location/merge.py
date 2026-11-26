# ruff: noqa: B023
"""Merge the two LLM passes into truth: shots matched by release time (<= 1.0 s). Agreed: both
visible, same team, release within 0.4 s, floor points within 1.5 m on the court. Everything
else goes to a third look (third.json: index -> {release_t, floor_px, team, kind} or null)."""

import json
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import methods as m

SP = Path(os.environ["SHOT_LOC_DIR"])  # wo/: clips and out_h1, out_h2; wl/: labels
out = {}
for h in ("h1", "h2"):
    clip = m.Clip(SP / "wo" / f"out_{h}")
    A = json.loads((SP / "wl/passA" / f"{h}.json").read_text())
    B = json.loads((SP / "wl/passB" / f"{h}.json").read_text())

    def court(s):
        if s.get("release_t") is None or not s.get("floor_px"):
            return None
        return clip.to_court(round(s["release_t"] * clip.fps), s["floor_px"])

    used, rows = set(), []
    for a in A:
        j = min(
            (
                k
                for k in range(len(B))
                if k not in used
                and a.get("release_t") is not None
                and B[k].get("release_t") is not None
            ),
            key=lambda k: abs(B[k]["release_t"] - a["release_t"]),
            default=None,
        )
        b = B[j] if j is not None and abs(B[j]["release_t"] - a["release_t"]) <= 1.0 else None
        if b is not None:
            used.add(j)
        rows.append((a, b))
    rows += [(None, B[k]) for k in range(len(B)) if k not in used]
    shots = []
    for a, b in sorted(rows, key=lambda r: (r[0] or r[1]).get("release_t") or 0):
        ca, cb = (court(a) if a else None), (court(b) if b else None)
        ok = (
            a
            and b
            and ca
            and cb
            and a["status"] != "not_visible"
            and b["status"] != "not_visible"
            and a["team"] == b["team"] != "unclear"
            and abs(a["release_t"] - b["release_t"]) <= 0.4
            and math.dist(ca, cb) <= 1.5
        )
        shot = {"A": a, "B": b, "court_A": ca, "court_B": cb, "agreed": bool(ok)}
        if ok:
            shot["truth"] = {
                "release_t": round((a["release_t"] + b["release_t"]) / 2, 2),
                "court": [(ca[0] + cb[0]) / 2, (ca[1] + cb[1]) / 2],
                "team": a["team"],
                "kind": a["kind"]
                if a["kind"] == b["kind"]
                else "disputed_kind:" + a["kind"] + "/" + b["kind"],
            }
        shots.append(shot)
    out[h] = shots
(SP / "wl" / "merged.json").write_text(json.dumps(out, indent=1))
for h, s in out.items():
    print(h, "shots", len(s), "agreed", sum(x["agreed"] for x in s))
    for i, x in enumerate(s):
        if not x["agreed"]:
            a, b = x["A"] or {}, x["B"] or {}
            d = math.dist(x["court_A"], x["court_B"]) if x["court_A"] and x["court_B"] else None
            print(
                " ",
                i,
                "A",
                a.get("release_t"),
                a.get("status"),
                a.get("team"),
                a.get("floor_px"),
                "| B",
                b.get("release_t"),
                b.get("status"),
                b.get("team"),
                b.get("floor_px"),
                "| d_m",
                None if d is None else round(d, 1),
            )
