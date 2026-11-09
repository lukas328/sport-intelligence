"""DHB press report PDF (Sportradar), read as text with `pdftotext -layout`."""

from __future__ import annotations

import re

from handball_api.core.errors import ProblemError
from handball_api.integrations.official_reports import http
from handball_api.integrations.official_reports.base import (
    DHB,
    OfficialEntry,
    OfficialReport,
    parse_number,
)

DHB_PDF = "https://dhbdata.fmp.sportradar.com/match/{}/pressReport.pdf"

_WHO = re.compile(r"(.+?) \(Nr\.\s*(\w+) (.+?)\)")
_DHB_KINDS = (
    ("7-Meter-Tor durch ", "penalty_goal"),
    ("7-Meter-Versuch durch ", "penalty_missed"),
    ("Tor durch ", "goal"),
)


def parse_dhb(match_id: int, text: str) -> OfficialReport:
    """Text of the press report (`pdftotext -layout`)."""
    lines = text.splitlines()
    head = [ln.strip() for ln in lines[:6]]
    if len(head) < 2 or " - " not in head[1]:
        raise ProblemError(422, "report-unreadable", "The PDF is not a DHB press report")
    home, away = (x.strip() for x in head[1].split(" - ", 1))
    final = re.search(r"Endstand:\s*(\d+)\s*:\s*(\d+)\s*\((\d+)\s*:\s*(\d+)\)", text)
    date = re.search(r"am (\d{2})\.(\d{2})\.(\d{4})", text)
    entries: list[OfficialEntry] = []
    for ln in lines:
        m = re.match(r"^\s*(\d{1,2}):(\d{2})\s+(\S.*)$", ln)
        if not m:
            continue
        body = m.group(3).rstrip()
        score = re.search(r"(\d+)\s*:\s*(\d+)\s*$", body)
        text_part = body[: score.start()].strip() if score else body.strip()
        kind, who = None, text_part
        for prefix, k in _DHB_KINDS:
            if text_part.startswith(prefix):
                kind, who = k, text_part[len(prefix) :]
                break
        if kind is None:
            if "Zeitstrafe" in text_part:
                kind = "suspension"
            elif "verwarnt" in text_part:
                kind = "warning"
            elif "Disqualifikation" in text_part or "disqualifiziert" in text_part:
                kind = "disqualification"
            elif "Team-Timeout" in text_part:
                kind = "timeout"
            else:
                continue
        w = _WHO.search(who)
        team = None
        if w:
            club = w.group(3).strip()
            team = "home" if club == home else "away" if club == away else None
        elif kind == "timeout":
            team = (
                "home"
                if text_part.startswith(home)
                else "away"
                if text_part.startswith(away)
                else None
            )
        entries.append(
            OfficialEntry(
                clock_s=int(m.group(1)) * 60 + int(m.group(2)),
                kind=kind,
                team=team,
                number=parse_number(w.group(2)) if w else None,
                name=w.group(1).strip() if w else None,
                score=(int(score.group(1)), int(score.group(2))) if score else None,
            )
        )
    if not entries and not final:
        raise ProblemError(422, "report-unreadable", "No game log found in the press report")
    return OfficialReport(
        provider=DHB,
        game_id=match_id,
        source_url=DHB_PDF.format(match_id),
        home=home,
        away=away,
        competition=head[0] or None,
        date=f"{date.group(3)}-{date.group(2)}-{date.group(1)}" if date else None,
        final=(int(final.group(1)), int(final.group(2))) if final else None,
        half_time=(int(final.group(3)), int(final.group(4))) if final else None,
        entries=sorted(entries, key=lambda x: x.clock_s),
    )


async def fetch_dhb(match_id: int, pdf_text: http.PdfText = http.pdf_text) -> str:
    """Text of a DHB press report (replaced by recorded text in tests)."""
    pdf = await http.download(DHB_PDF.format(match_id), http.MAX_PDF_BYTES, "DHB")
    if not pdf.startswith(b"%PDF"):
        raise ProblemError(422, "report-unreadable", "The DHB link did not return a PDF")
    return await pdf_text(pdf)
