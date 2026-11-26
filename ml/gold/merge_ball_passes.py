"""Merge two ring-free LLM ball passes into frozen labels (rule of ball test 2):
- ball: both passes say ball or part within 12 px, position = mean; cat = the category both gave,
  else "disputed";
- no_ball: both say out; warmup: both say warmup; excluded: everything else.
usage: python ml/gold/merge_ball_passes.py FRAMES.json PASS_A_DIR PASS_B_DIR OUT.json NOTE
Writes OUT.json and prints its sha256 (freeze it before any model is measured on it)."""

from __future__ import annotations

import collections
import hashlib
import json
import math
import sys
from pathlib import Path

SEE = ("ball", "part")


def main() -> None:
    frames = json.loads(Path(sys.argv[1]).read_text())["frames"]
    pa, pb, out, note = Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]), sys.argv[5]
    labels = []
    for n, fr in enumerate(frames):
        a = json.loads((pa / f"{n}.json").read_text())
        b = json.loads((pb / f"{n}.json").read_text())
        row = {k: fr[k] for k in ("id", "game", "file", "frame", "fps")}
        row["pass_a"] = {k: a.get(k) for k in ("state", "x", "y", "cat")}
        row["pass_b"] = {k: b.get(k) for k in ("state", "x", "y", "cat")}
        label, x, y, cat = "excluded", None, None, None
        if a["state"] in SEE and b["state"] in SEE and None not in (a["x"], a["y"], b["x"], b["y"]):
            if math.dist((a["x"], a["y"]), (b["x"], b["y"])) <= 12:
                label = "ball"
                x, y = round((a["x"] + b["x"]) / 2, 1), round((a["y"] + b["y"]) / 2, 1)
                cat = a.get("cat") if a.get("cat") == b.get("cat") else "disputed"
        elif a["state"] == b["state"] == "out":
            label = "no_ball"
        elif a["state"] == b["state"] == "warmup":
            label = "warmup"
        row.update(label=label, x=x, y=y, cat=cat)
        labels.append(row)
    raw = json.dumps({"note": note, "labels": labels}, indent=1).encode()
    out.write_bytes(raw)
    print(
        hashlib.sha256(raw).hexdigest(),
        collections.Counter(r["label"] for r in labels),
        collections.Counter(r["cat"] for r in labels if r["label"] == "ball"),
    )


if __name__ == "__main__":
    main()
