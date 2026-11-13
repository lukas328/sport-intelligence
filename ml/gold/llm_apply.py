"""Turn answers on the llm_sheets.py contact sheets into gold labels (precise, src "llm").

Answer per row: candidate number ("2"), a point in the 300 px crop ("170,155"), either with a
trailing "h" for in hand, "-" for no ball visible, "?" for not decided (left open).

    python ml/gold/llm_apply.py SHEETS_DIR CLIP ANSWERS_JSON OUT_JSON [EXISTING_DOC_JSON]
OUT_JSON is the clip's gold document (rough labels of the existing document kept).
"""

import json
import sys
from pathlib import Path

Z = 1.5


def main() -> None:
    sheets, clip, answers, out = (
        Path(sys.argv[1]),
        sys.argv[2],
        Path(sys.argv[3]),
        Path(sys.argv[4]),
    )
    meta = json.loads((sheets / f"{clip}.json").read_text())["rows"]
    ans = json.loads(answers.read_text())
    doc = {"labels": {}, "shots": [], "done": False, "pdone": False}
    if len(sys.argv) > 5:
        d = json.loads(Path(sys.argv[5]).read_text())
        doc |= d.get("data", d)
    # keep the owner's rough points and own precise clicks; earlier llm labels are replaced
    labels = {k: v for k, v in doc["labels"].items() if v.get("src") != "llm"}
    n = 0
    for r in meta:
        a = ans.get(str(r["row"]), "?").strip()
        if a == "?":
            continue
        f = str(r["frame"])
        if labels.get(f, {}).get("p"):
            continue  # the owner clicked this frame precisely
        if a == "-":
            labels[f] = {"s": "out", "p": 1, "src": "llm"}
            n += 1
            continue
        s = "held" if a.endswith("h") else "free"
        a = a.rstrip("h")
        if "," in a:
            u, v = (float(t) for t in a.split(","))
            x, y = r["x0"] + u / Z, r["y0"] + v / Z
        else:
            x, y = r["cands"][int(a) - 1]
        labels[f] = {"x": round(x, 1), "y": round(y, 1), "s": s, "p": 1, "src": "llm"}
        n += 1
    doc["labels"] = labels
    out.write_text(
        json.dumps({k: doc[k] for k in ("labels", "shots", "done", "pdone")} | {"at": 0})
    )
    print(clip, n, "llm labels of", len(meta), "rows")


if __name__ == "__main__":
    main()
