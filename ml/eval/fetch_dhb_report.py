"""Official DHB match report (press report PDF, dhbdata.fmp.sportradar.com) -> JSON in the same
shape as `fetch_handball_ch.py`: the game log (every goal, 7-metre, suspension, warning, time-out
with match time, shirt number, name, team and score) and the rosters with goals.

usage: python ml/eval/fetch_dhb_report.py <matchId> <out.json>      (needs pdftotext, poppler)"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any

URL = "https://dhbdata.fmp.sportradar.com/match/{}/pressReport.pdf"
WHO = re.compile(r"(.+?) \(Nr\.(\d+) (.+?)\)")
KINDS = [
    ("7-Meter-Tor durch ", "7m Tor"),
    ("7-Meter-Versuch durch ", "7m Fehlwurf"),
    ("Tor durch ", "Tor"),
]


def parse(text: str) -> dict[str, Any]:
    lines = text.splitlines()
    head = [ln.strip() for ln in lines[:6]]
    teams = head[1].split(" - ")
    final = re.search(r"Endstand:\s*(\d+)\s*:\s*(\d+)\s*\((\d+)\s*:\s*(\d+)\)", text)
    log: list[dict[str, Any]] = []
    for ln in lines:
        m = re.match(r"^\s*(\d{1,2}):(\d{2})\s+(.+)$", ln)
        if not m:
            continue
        body = m.group(3).rstrip()
        score = re.search(r"(\d+)\s*:\s*(\d+)\s*$", body)
        text_part = body[: score.start()].strip() if score else body.strip()
        action, who = None, text_part
        for prefix, kind in KINDS:
            if text_part.startswith(prefix):
                action, who = kind, text_part[len(prefix) :]
                break
        if action is None:
            if "Zeitstrafe" in text_part:
                action = "Zeitstrafe"
            elif "verwarnt" in text_part:
                action = "Verwarnung"
            elif "Disqualifikation" in text_part or "disqualifiziert" in text_part:
                action = "Disqualifikation"
            elif "Team-Timeout" in text_part:
                action = "Team Time-Out"
            else:
                continue
        w = WHO.search(who)
        team = None
        if w:
            team = "home" if w.group(3).strip() == teams[0] else "away"
        elif action == "Team Time-Out":
            team = "home" if text_part.startswith(teams[0]) else "away"
        log.append(
            {
                "timeInt": int(m.group(1)) * 60 + int(m.group(2)),
                "timeString": f"{m.group(1)}:{m.group(2)}",
                "actionText": action,
                "team": team,
                "number": int(w.group(2)) if w else None,
                "name": w.group(1).strip() if w else None,
                "result": f"{score.group(1)}:{score.group(2)}" if score else None,
            }
        )
    return {
        "competition": head[0],
        "home": teams[0],
        "away": teams[1] if len(teams) > 1 else None,
        "date": (re.search(r"am (\d{2}\.\d{2}\.\d{4})", text) or [None, None])[1],
        "final": [int(final.group(1)), int(final.group(2))] if final else None,
        "half_time": [int(final.group(3)), int(final.group(4))] if final else None,
        "log": sorted(log, key=lambda x: x["timeInt"]),
    }


if __name__ == "__main__":
    mid = int(sys.argv[1])
    pdf = Path(sys.argv[2]).with_suffix(".pdf")
    urllib.request.urlretrieve(URL.format(mid), pdf)  # noqa: S310 - fixed https URL
    text = subprocess.run(
        ["pdftotext", "-layout", str(pdf), "-"],  # noqa: S607
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    out = {"source": URL.format(mid), "match_id": mid, **parse(text)}
    pdf.unlink()
    with Path(sys.argv[2]).open("w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    goals = [e for e in out["log"] if e["actionText"] in ("Tor", "7m Tor")]
    print(
        mid,
        out["home"],
        "-",
        out["away"],
        out["final"],
        len(out["log"]),
        "events,",
        len(goals),
        "goals",
    )
