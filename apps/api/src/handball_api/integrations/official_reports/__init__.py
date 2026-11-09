"""Official match reports: where each one is fetched and how it is read.

Public sources, read by URL (docs/plans/data-sources-de.md):
- handball.ch match centre (GraphQL behind https://www.handball.ch/de/matchcenter/spiele/<id>):
  game, game log (every goal, shot, save, technical error, suspension, time-out with match time,
  shirt number and name) and player stats;
- DHB press report PDF (https://dhbdata.fmp.sportradar.com/match/<id>/pressReport.pdf), turned
  into text with `pdftotext -layout` (poppler-utils): goals, 7-metres, warnings, suspensions,
  disqualifications and time-outs;
- nuLiga game report of the German associations still on nuLiga and of Austria (ÖHB), on
  `<association>-handball.liga.nu`: the HTML page (…/nuLigaHBDE.woa/wa/groupMeetingReport?
  meeting=<id>&championship=…&group=…) or its PDF (…/nuLigaDokumentHBAT.woa/wa/nuDokument?
  dokument=meetingReportHB&meeting=<id>, the link on oehb.at): both rosters, the result and the
  log ("Spielverlauf": goals with time, shirt number and scorer, 7 m, 2 minutes, warnings,
  disqualifications, time-outs);
- HLA match report PDF on Sportradar (https://infographics.sportradar.com/hla/pageSnapshot/pdf/
  de/<id>): teams, result, half-time and the missed 7-metres with time; it has no timed log of
  the goals, so the import says so (the ÖHB nuLiga report of the same game has it).
Only these fixed hosts are contacted (nuLiga: any `<name>-handball.liga.nu`, redirects only on
the same host), one request per import and only when a coach asks; the given URL only names the
game: the URL fetched is rebuilt from its checked parts, and no other link is followed.

Every module here is plain Python without database access: services/official_report.py fetches
through them and stores the result as events of a match.
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from handball_api.core.errors import ProblemError
from handball_api.integrations.official_reports.base import (
    DHB,
    HANDBALL_CH,
    HLA,
    ID_PROVIDERS,
    ReportLink,
)
from handball_api.integrations.official_reports.dhb import DHB_PDF
from handball_api.integrations.official_reports.handball_ch import CH_PAGE
from handball_api.integrations.official_reports.hla import HLA_PDF
from handball_api.integrations.official_reports.nuliga import NULIGA_HOST, nuliga_link

_UNSUPPORTED = (
    "Use a handball.ch match centre link (…/matchcenter/spiele/<id>), a DHB press report link "
    "(dhbdata.fmp.sportradar.com/match/<id>/pressReport.pdf), a nuLiga game report "
    "(<association>-handball.liga.nu/…/groupMeetingReport?meeting=<id>&championship=…, or its "
    "PDF …/nuDokument?dokument=meetingReportHB&meeting=<id>) or an HLA report "
    "(infographics.sportradar.com/hla/pageSnapshot/pdf/de/<id>)"
)


def locate(source: str, provider: str | None = None) -> ReportLink:
    """The report a match centre / report URL (or a plain id + provider) names. Only the fixed
    hosts are accepted, and the URL to fetch is rebuilt from the checked parts."""
    s = source.strip()
    if s.isdigit():
        if provider not in ID_PROVIDERS:
            raise ProblemError(
                422,
                "report-url-unsupported",
                "A plain game id needs a provider (handball_ch, dhb, hla); nuLiga needs the link",
            )
        game_id = int(s)
        url = {HANDBALL_CH: CH_PAGE, DHB: DHB_PDF, HLA: HLA_PDF}[str(provider)].format(game_id)
        return ReportLink(str(provider), game_id, url, pdf=provider != HANDBALL_CH)
    parts = urlsplit(s if "://" in s else f"https://{s}")
    host = (parts.hostname or "").lower()
    if host in ("handball.ch", "www.handball.ch"):
        m = re.search(r"/matchcenter/[^/]+/(\d{1,9})(?:/|$)", parts.path, re.IGNORECASE)
        if m:
            return ReportLink(HANDBALL_CH, int(m.group(1)), CH_PAGE.format(int(m.group(1))))
    if host in ("dhbdata.fmp.sportradar.com", "dhb.fmp.sportradar.com"):
        m = re.search(r"/match/(\d{1,9})(?:/|$)", parts.path)
        if m:
            return ReportLink(DHB, int(m.group(1)), DHB_PDF.format(int(m.group(1))), pdf=True)
    if host == "infographics.sportradar.com":
        m = re.fullmatch(r"/hla/pageSnapshot/(?:pdf/)?[a-z]{2}/(\d{1,12})/?", parts.path)
        if m:
            return ReportLink(HLA, int(m.group(1)), HLA_PDF.format(int(m.group(1))), pdf=True)
    if NULIGA_HOST.fullmatch(host) and parts.port is None:
        link = nuliga_link(host, parts.path, parts.query)
        if link is not None:
            return link
    raise ProblemError(422, "report-url-unsupported", _UNSUPPORTED)


def detect(source: str, provider: str | None = None) -> tuple[str, int]:
    """(provider, game id) from a match centre / report URL, or a plain id + provider."""
    link = locate(source, provider)
    return link.provider, link.game_id
