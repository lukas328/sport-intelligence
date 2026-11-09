"""HLA match report PDF (Sportradar infographic): result, half-time and missed 7-metres."""

from __future__ import annotations

import re

from handball_api.core.errors import ProblemError
from handball_api.integrations.official_reports import http
from handball_api.integrations.official_reports.base import (
    HLA,
    OfficialEntry,
    OfficialReport,
    parse_clock,
)

HLA_PDF = "https://infographics.sportradar.com/hla/pageSnapshot/pdf/de/{}"

_HLA_TEAMS = re.compile(r"^\s*(\S.*?)\s{2,}(\d{1,3}) : (\d{1,3})\s{2,}(\S.*?)\s*$")
_HLA_PLAYER = re.compile(r"^\s*(\d{1,3})\s{2,}(\S.*?)\s{2,}[A-Z]{2}\s")
_HLA_MISS = re.compile(r"(\d{1,2}:\d{2}) \| (\d{1,3}) (.+?) \((\w+)\)")
HLA_NOTE = (
    "The HLA report has no timed log of the goals: only the result and the missed 7-metres "
    "were imported. The ÖHB nuLiga report of the game (oehb.at) has the full log."
)


def parse_hla(match_id: int, text: str) -> OfficialReport:
    """Text of an HLA match report (Sportradar infographic, `pdftotext -layout`)."""
    lines = text.splitlines()
    teams = next((m for ln in lines if (m := _HLA_TEAMS.match(ln))), None)
    if teams is None or "SPIELBERICHT" not in text:
        raise ProblemError(422, "report-unreadable", "The PDF is not an HLA match report")
    home, away = teams.group(1), teams.group(4)
    final = (int(teams.group(2)), int(teams.group(3)))
    half_m = re.search(r"\(\s*(\d{1,3}) : (\d{1,3})\s*\)", text[teams.end() :])
    date = re.search(r"Datum:\s*(\d{2})/(\d{2})/(\d{2})", text)
    competition = re.search(r"Saison: \S+\s{2,}(\S.*?)\s*$", text, re.MULTILINE)
    # players per team (the first player table is the home team's): full names for the 7 m
    names: dict[tuple[str, int], str] = {}
    team = None
    for ln in lines:
        if re.match(r"^\s*Nr\s+Name\s+Pos\.", ln):
            team = "home" if team is None else "away"
        elif team and (p := _HLA_PLAYER.match(ln)):
            names.setdefault((team, int(p.group(1))), p.group(2))
    entries: list[OfficialEntry] = []
    for i, ln in enumerate(lines):
        if "7m verworfen:" not in ln:
            continue
        cols = [m.start() for m in re.finditer(r"7m verworfen:", ln)]
        for below in lines[i + 1 : i + 8]:
            if "Würfe geblockt" in below:
                break
            for m in _HLA_MISS.finditer(below):
                col = min(range(len(cols)), key=lambda c: abs(cols[c] - m.start()))
                side = "home" if col == 0 else "away"
                number = int(m.group(2))
                how = m.group(4).upper()
                kind = (
                    "penalty_saved"
                    if how in ("SAVE", "GEHALTEN", "PARADE")
                    else "penalty_post"
                    if how in ("POST", "PFOSTEN", "LATTE")
                    else "penalty_missed"
                )
                entries.append(
                    OfficialEntry(
                        clock_s=parse_clock(m.group(1)) or 0,
                        kind=kind,
                        team=side,
                        number=number,
                        name=names.get((side, number), m.group(3).strip()),
                    )
                )
        break
    return OfficialReport(
        provider=HLA,
        game_id=match_id,
        source_url=HLA_PDF.format(match_id),
        home=home,
        away=away,
        competition=competition.group(1) if competition else "HLA",
        date=f"20{date.group(3)}-{date.group(2)}-{date.group(1)}" if date else None,
        final=final,
        half_time=(int(half_m.group(1)), int(half_m.group(2))) if half_m else None,
        entries=sorted(entries, key=lambda x: x.clock_s),
        notes=[HLA_NOTE],
    )


async def fetch_hla(match_id: int, pdf_text: http.PdfText = http.pdf_text) -> str:
    """Text of an HLA match report PDF (replaced by recorded text in tests)."""
    pdf = await http.download(HLA_PDF.format(match_id), http.MAX_PDF_BYTES, "Sportradar (HLA)")
    if not pdf.startswith(b"%PDF"):
        raise ProblemError(422, "report-unreadable", "The HLA link did not return a PDF")
    return await pdf_text(pdf)
