"""Merge the LLM release marks of the dev shots into one file (2026-11-26).

Source: two independent passes (A, B) by Claude subagents looking at frame sheets of the 175 dev
shot clips (page "Abwürfe Dev", ml/gold/release_dev_clips.py), different sampling grids and order,
no access to each other's files; a third look (C) on every shot where A and B differ by more than
0.4 s or only one found the shot. NOT human marks: the owner did not mark the dev shots.

Final per shot:
- A and B within 0.4 s: their mean; status "ok" when both said ok, else "unsure";
- otherwise the third look's time and status;
- no time anywhere: not_visible (often a log entry with no shot to see, e.g. "empty_goal").

    python ml/gold/merge_release_marks.py PASS_A PASS_B PASS_C ITEMS.json OUT.json
ITEMS.json: the page's item list (seg, log_t, kind per shot n).
"""

import hashlib
import json
import sys
from pathlib import Path


def load(d: Path, n: int) -> dict | None:
    f = d / f"{n}.json"
    return json.loads(f.read_text()) if f.exists() else None


def main() -> None:
    pa, pb, pc, items_path, out = (Path(x) for x in sys.argv[1:6])
    items = json.loads(items_path.read_text())
    shots = []
    for n, it in enumerate(items):
        a, b, c = load(pa, n), load(pb, n), load(pc, n)
        ta, tb = (a or {}).get("release_t"), (b or {}).get("release_t")
        if ta is not None and tb is not None and abs(ta - tb) <= 0.4:
            t = round((ta + tb) / 2, 2)
            st = "ok" if a["status"] == "ok" and b["status"] == "ok" else "unsure"
            how = "A+B"
        elif c is not None:
            t, st, how = c.get("release_t"), c["status"], "C"
        else:
            t, st, how = None, "not_visible", "A+B"
        if t is None:
            st = "not_visible"
        shots.append(
            {
                "n": n,
                "seg": it["seg"],
                "kind": it["kind"],
                "log_t": it["log_t"],
                "t_s": t,
                "status": st,
                "decided_by": how,
                "pass_a": ta,
                "pass_b": tb,
                "pass_c": (c or {}).get("release_t"),
            }
        )
    body = {
        "note": "LLM release marks (Claude subagents, two independent passes plus a third look on "
        "disagreements), NOT the owner's marks. Dev shots only (ml/gold/release_dev_clips.py). t_s: "
        "release (last frame with the ball in the shooter's hand) in segment seconds. Use status ok "
        "for choosing methods; unsure and not_visible are left out. Frozen: see sha256.",
        "shots": shots,
    }
    text = json.dumps(body, indent=1, ensure_ascii=False)
    out.write_text(text)
    print(out, hashlib.sha256(text.encode()).hexdigest())
    from collections import Counter

    print(Counter(s["status"] for s in shots), Counter(s["decided_by"] for s in shots))


if __name__ == "__main__":
    main()
