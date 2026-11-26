# ruff: noqa: E741
"""Truth = agreed shots + disputed shots where the third look agrees with a pass (release within
0.4 s, floor point within 1.5 m, same team): mean of the third look and that pass. Writes
truth.json and its sha256 (frozen before evaluate.py runs)."""

import hashlib
import json
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import methods as m

SP = Path(os.environ["SHOT_LOC_DIR"])  # wo/: clips and out_h1, out_h2; wl/: labels
merged = json.loads((SP / "wl/merged.json").read_text())
third = json.loads((SP / "wl/passC/third.json").read_text())
truth, log = {}, []
for h, shots in merged.items():
    clip = m.Clip(SP / "wo" / f"out_{h}")
    out = []
    for i, x in enumerate(shots):
        if x["agreed"]:
            t = dict(x["truth"])
            t["source"] = "A+B"
            out.append(t)
            continue
        c = third.get(f"{h}_{i}")
        if not c or not c.get("shot") or c.get("release_t") is None or not c.get("floor_px"):
            log.append((h, i, "dropped: third look no shot/point"))
            continue
        cc = clip.to_court(round(c["release_t"] * clip.fps), c["floor_px"])
        best = None
        for key in ("A", "B"):
            p, pc = x[key], x["court_" + key]
            if (
                p
                and pc
                and p.get("team") == c["team"]
                and abs(p["release_t"] - c["release_t"]) <= 0.4
                and math.dist(pc, cc) <= 1.5
            ):
                best = (key, p, pc)
                break
        if best is None:
            log.append((h, i, "dropped: third look agrees with no pass"))
            continue
        key, p, pc = best
        out.append(
            {
                "release_t": round((p["release_t"] + c["release_t"]) / 2, 2),
                "court": [(pc[0] + cc[0]) / 2, (pc[1] + cc[1]) / 2],
                "team": c["team"],
                "kind": c["kind"]
                if c["kind"] == p["kind"]
                else "disputed_kind:" + p["kind"] + "/" + c["kind"],
                "source": key + "+C",
            }
        )
    truth[h] = out
raw = json.dumps(truth, indent=1, sort_keys=True).encode()
(SP / "wl/truth.json").write_bytes(raw)
d = hashlib.sha256(raw).hexdigest()
(SP / "wl/truth.sha256").write_text(d + "  truth.json\n")
print(d, {h: len(v) for h, v in truth.items()})
[print(*l) for l in log]
