"""handball.ch match centre game report (game log of the GraphQL API)."""

from __future__ import annotations

from typing import Any

from handball_api.core.errors import ProblemError
from handball_api.integrations import handball_ch
from handball_api.integrations.official_reports.base import (
    HANDBALL_CH,
    OfficialEntry,
    OfficialReport,
    parse_number,
    parse_score,
)

CH_PAGE = handball_ch.GAME_PAGE

# role of each side in a handball.ch log entry (homeTeamActionLCID / awayTeamActionLCID)
_GK_ROLES = {"bParade"}


def _ch_kind(text: str) -> str | None:
    t = text.strip().lower()
    if t.startswith("7m"):
        if "tor" in t:
            return "penalty_goal"
        if "parade" in t:
            return "penalty_saved"
        if "pfosten" in t:
            return "penalty_post"
        return "penalty_missed"
    if t == "tor":
        return "goal"
    if t.startswith("wurf"):
        if "parade" in t:
            return "shot_saved"
        if "pfosten" in t:
            return "shot_post"
        return "shot_missed"
    if "techn" in t:
        return "turnover"
    if "zeitstrafe" in t or "2 min" in t:
        return "suspension"
    if "verwarnung" in t:
        return "warning"
    if "disq" in t or "rot" in t:
        return "disqualification"
    if "time-out" in t or "timeout" in t:
        return "timeout"
    return None  # empty goal, goalkeeper in, ...


def parse_handball_ch(game_id: int, data: dict[str, Any]) -> OfficialReport:
    games = data.get("game") or []
    if not games:
        raise ProblemError(404, "report-not-found", f"handball.ch has no game {game_id}")
    game = games[0]
    keepers = {
        ("home" if p.get("isHome") else "away", parse_number(p.get("dressNr")))
        for p in data.get("gamePlayerStats") or []
        if p.get("function") == "goalkeeper"
    }
    entries: list[OfficialEntry] = []
    for e in data.get("gameLog") or []:
        kind = _ch_kind(str(e.get("actionText") or ""))
        if kind is None or e.get("timeInt") is None:
            continue
        people = {
            side: (
                parse_number(e.get(f"{side}TeamPlayerStaffNrDesc")),
                str(e.get(f"{side}TeamPlayerStaffName") or "").strip() or None,
            )
            for side in ("home", "away")
        }
        roles = {side: str(e.get(f"{side}TeamActionLCID") or "") for side in ("home", "away")}
        acting = [s for s in ("home", "away") if roles[s]] or [
            s for s in ("home", "away") if people[s][1]
        ]
        team: str | None = acting[0] if len(acting) == 1 else None
        keeper: int | None = None
        if len(acting) == 2:  # a save names the shooter and the goalkeeper
            gk = [s for s in acting if roles[s] in _GK_ROLES] or [
                s for s in acting if (s, people[s][0]) in keepers
            ]
            if len(gk) == 1:
                team = "away" if gk[0] == "home" else "home"
                keeper = people[gk[0]][0]
        number, name = people[team] if team else (None, None)
        entries.append(
            OfficialEntry(
                clock_s=int(e["timeInt"]),
                kind=kind,
                team=team,
                number=number,
                name=name,
                score=parse_score(e.get("result")),
                goalkeeper_number=keeper,
            )
        )
    final = (game.get("homeTeamScore"), game.get("awayTeamScore"))
    half = (game.get("homeTeamScoreInterval"), game.get("awayTeamScoreInterval"))
    return OfficialReport(
        provider=HANDBALL_CH,
        game_id=game_id,
        source_url=CH_PAGE.format(game_id),
        home=game.get("homeTeamName"),
        away=game.get("awayTeamName"),
        competition=game.get("leagueName"),
        date=str(game.get("gameDateTime") or "")[:10] or None,
        final=(int(final[0]), int(final[1])) if None not in final else None,
        half_time=(int(half[0]), int(half[1])) if None not in half else None,
        entries=sorted(entries, key=lambda x: x.clock_s),
    )


async def fetch_handball_ch(game_id: int) -> dict[str, Any]:
    """Raw GraphQL data of a handball.ch game (replaced by recorded data in tests)."""
    try:
        return await handball_ch.report(game_id)
    except handball_ch.UpstreamUnavailableError as exc:
        raise ProblemError(
            502, "report-unavailable", "handball.ch did not answer, try again later"
        ) from exc
