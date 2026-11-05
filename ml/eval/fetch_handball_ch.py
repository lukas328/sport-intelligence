"""Official game data from handball.ch (public match centre API): the game log (every goal, shot,
save, suspension with match time, shirt number and name) and per-player stats. Used as ground truth
for goals, scorers, shirt numbers and shots on the test videos.

usage: python ml/eval/fetch_handball_ch.py <gameId> <out.json>"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path
from typing import Any

URL = "https://www.handball.ch/Umbraco/Api/MatchCenter/Query"
LOG = """query getGameLog($gameId: Int, $isLive: Boolean){ gameLog(gameId: $gameId, isLive: $isLive) {
  actionGroup actionText homeTeamPlayerStaffName homeTeamPlayerStaffNrDesc awayTeamPlayerStaffName
  awayTeamPlayerStaffNrDesc result timeInt timeString } }"""
PLAYERS = """query getGamePlayerStats($gameId: Int, $isLive: Boolean){ gamePlayerStats(gameId: $gameId,
  isLive: $isLive) { teamName dressNr playerName totalScore totalShots totalScore7m totalShots7m
  totalSaves totalShotsGK total2Minutes isHome function } }"""


def query(q: str, game_id: int) -> dict[str, Any]:
    body = json.dumps({"query": q, "variables": {"gameId": game_id, "isLive": False}}).encode()
    req = urllib.request.Request(
        URL, body, {"Content-Type": "application/json", "Accept-Language": "de"}
    )
    with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310
        data: dict[str, Any] = json.load(r)["data"]
        return data


if __name__ == "__main__":
    gid = int(sys.argv[1])
    log: list[dict[str, Any]] = query(LOG, gid)["gameLog"] or []
    players: list[dict[str, Any]] = query(PLAYERS, gid)["gamePlayerStats"] or []
    out = {
        "source": f"https://www.handball.ch/de/matchcenter/spiele/{gid}",
        "game_id": gid,
        "log": sorted(log, key=lambda x: x["timeInt"]),
        "players": players,
    }
    with Path(sys.argv[2]).open("w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(gid, len(log), "log entries,", len(players), "players")
