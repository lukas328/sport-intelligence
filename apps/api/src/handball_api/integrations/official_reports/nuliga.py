"""nuLiga game report (HTML page or PDF) of the associations on `<name>-handball.liga.nu`."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Any
from urllib.parse import parse_qs, urlencode

from handball_api.core.errors import ProblemError
from handball_api.integrations.official_reports import http
from handball_api.integrations.official_reports.base import (
    CLOCK,
    NULIGA,
    OfficialEntry,
    OfficialReport,
    ReportLink,
    parse_clock,
    parse_number,
    parse_score,
)

# nuLiga portals of the handball associations (bhv-, hhv-, hvnb-, …, oehb-handball.liga.nu)
NULIGA_HOST = re.compile(r"[a-z]{2,12}-handball\.liga\.nu")
_NULIGA_PATH = re.compile(
    r"/cgi-bin/WebObjects/nuLiga(?P<doc>Dokument)?HB(?P<land>DE|AT)\.woa/wa/"
    r"(?P<action>groupMeetingReport|nuDokument)/?",
    re.IGNORECASE,
)
_NULIGA_CHAMPIONSHIP = re.compile(r"[\w .+/()-]{1,80}")


def nuliga_link(host: str, path: str, query: str) -> ReportLink | None:
    m = _NULIGA_PATH.fullmatch(path)
    if not m:
        return None
    q = {k: v[0].strip() for k, v in parse_qs(query).items() if v}
    meeting = q.get("meeting", "")
    if not re.fullmatch(r"\d{1,10}", meeting):
        return None
    land = m.group("land").upper()
    base = f"https://{host}/cgi-bin/WebObjects"
    pdf_url = f"{base}/nuLigaDokumentHB{land}.woa/wa/nuDokument?" + urlencode(
        {"dokument": "meetingReportHB", "meeting": meeting}
    )
    if m.group("action").lower() == "nudokument":
        if q.get("dokument") != "meetingReportHB":
            return None
        return ReportLink(NULIGA, int(meeting), pdf_url, pdf=True)
    championship = q.get("championship", "")
    group = q.get("group", "")
    if not _NULIGA_CHAMPIONSHIP.fullmatch(championship):
        # the page needs the championship; the PDF of the game needs only the meeting
        return ReportLink(NULIGA, int(meeting), pdf_url, pdf=True)
    params = {"meeting": meeting, "championship": championship}
    if re.fullmatch(r"\d{1,10}", group):
        params["group"] = group
    url = f"{base}/nuLigaHB{land}.woa/wa/groupMeetingReport?{urlencode(params)}"
    return ReportLink(NULIGA, int(meeting), url)


class _Tables(HTMLParser):
    """Headings and tables of an HTML page, in document order: ("h1"|"h2"|"text", str) and
    ("table", rows of cell texts). Tables nested in a table (nuLiga's summary under a roster)
    come out on their own, before the enclosing one ends."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.items: list[tuple[str, Any]] = []
        self._tables: list[list[list[str]]] = []
        self._cell: list[str] | None = None
        self._heading: tuple[str, list[str]] | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self._flush_text()
            self._tables.append([])
        elif tag == "tr" and self._tables:
            self._tables[-1].append([])
        elif tag in ("td", "th") and self._tables and self._tables[-1]:
            self._cell = []
        elif tag in ("h1", "h2"):
            self._flush_text()
            self._heading = (tag, [])
        elif tag == "br":
            self._add("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("td", "th") and self._cell is not None and self._tables:
            text = re.sub(r"[ \t\r\f\v\xa0]+", " ", "".join(self._cell))
            self._tables[-1][-1].append(re.sub(r"\s*\n\s*", "\n", text).strip())
            self._cell = None
        elif tag == "table" and self._tables:
            self._cell = None
            self.items.append(("table", self._tables.pop()))
        elif tag in ("h1", "h2") and self._heading is not None:
            kind, parts = self._heading
            text = re.sub(r"[ \t\r\f\v\xa0]+", " ", "".join(parts))
            self.items.append((kind, re.sub(r"\s*\n\s*", "\n", text).strip()))
            self._heading = None

    def handle_data(self, data: str) -> None:
        self._add(data)

    def _add(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)
        elif self._heading is not None:
            self._heading[1].append(data)
        elif not self._tables:
            self._text.append(data)

    def _flush_text(self) -> None:
        text = " ".join("".join(self._text).split())
        if text:
            self.items.append(("text", text))
        self._text = []

    def close(self) -> None:
        super().close()
        self._flush_text()


_NU_SIDES = {"heim": "home", "home": "home", "gast": "away", "guest": "away", "away": "away"}
_NU_PERSON = re.compile(r"(?P<nr>\d{1,3}|[A-Z])\s+(?P<name>\S.*)")


def _nu_kind(text: str) -> tuple[str, str | None] | None:
    """(kind, side named in the event text) of a nuLiga log entry."""
    t = " ".join(text.lower().split())
    if t.startswith(("auszeit", "time-out", "timeout", "team-timeout")):
        side = next((_NU_SIDES[w] for w in t.split() if w in _NU_SIDES), None)
        return "timeout", side
    if t.startswith("7m") or t.startswith("7-m"):
        return ("penalty_missed" if "ohne" in t or "without" in t else "penalty_goal"), None
    if t in ("tor", "goal"):
        return "goal", None
    if "2 min" in t or "2-min" in t or "zeitstrafe" in t:
        return "suspension", None
    if "verwarnung" in t or "gelb" in t or "yellow" in t or "warning" in t:
        return "warning", None
    if "disq" in t or "rot" in t or "blau" in t or "red" in t or "blue" in t:
        return "disqualification", None
    return None


def _nu_entry(team: str, time: str, score: str, event: str, person: str) -> OfficialEntry | None:
    clock = parse_clock(time)
    kind = _nu_kind(event)
    if clock is None or kind is None:
        return None
    side = _NU_SIDES.get(team.strip().lower()) or kind[1]
    p = _NU_PERSON.fullmatch(person.strip())
    name = p.group("name").strip().rstrip(",") if p else None
    return OfficialEntry(
        clock_s=clock,
        kind=kind[0],
        team=side,
        number=parse_number(p.group("nr")) if p else None,  # team officials (A-D) have no number
        name=name or None,
        score=parse_score(score),
    )


def _result(text: str) -> tuple[tuple[int, int] | None, tuple[int, int] | None]:
    m = re.search(r"(\d{1,3})\s*:\s*(\d{1,3})(?:\s*\(\s*(\d{1,3})\s*:\s*(\d{1,3})\s*\))?", text)
    if not m:
        return None, None
    half = (int(m.group(3)), int(m.group(4))) if m.group(3) else None
    return (int(m.group(1)), int(m.group(2))), half


def _iso_date(text: str) -> str | None:
    m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", text)
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None


def _roster_entries(rows: list[list[str]], team: str) -> dict[str, list[OfficialEntry]]:
    """Warnings, 2 minutes and disqualifications with their time from a nuLiga roster table
    (columns: shirt, name, born, pass, goals, 7 m, yellow card, 2 min 1-3, disq. without /
    with report). Used for a kind the log does not list."""
    out: dict[str, list[OfficialEntry]] = {}
    columns = (
        (6, "warning"),
        (7, "suspension"),
        (8, "suspension"),
        (9, "suspension"),
        (10, "disqualification"),
        (11, "disqualification"),
    )
    for row in rows:
        if len(row) < 12 or not re.fullmatch(r"\d{1,3}|[A-Z]", row[0]):
            continue
        for col, kind in columns:
            clock = parse_clock(row[col])
            if clock is not None:
                out.setdefault(kind, []).append(
                    OfficialEntry(
                        clock_s=clock,
                        kind=kind,
                        team=team,
                        number=parse_number(row[0]),
                        name=row[1].strip() or None,
                    )
                )
    return out


def parse_nuliga(meeting: int, source_url: str, page: str) -> OfficialReport:
    """HTML of a nuLiga game report (groupMeetingReport)."""
    parser = _Tables()
    parser.feed(page)
    parser.close()
    h1 = next((v for k, v in parser.items if k == "h1"), "")
    tables = [v for k, v in parser.items if k == "table"]
    info: dict[str, str] = {}
    for rows in tables:
        for row in rows:
            for i in range(0, len(row) - 1):
                info.setdefault(row[i].strip().lower(), row[i + 1].strip())
    home = info.get("heimmannschaft") or info.get("home team")
    away = info.get("gastmannschaft") or info.get("guest team") or info.get("away team")
    head = [ln.strip() for ln in h1.splitlines() if ln.strip()]
    if (not home or not away) and len(head) >= 3 and " - " in head[2]:
        home, away = (x.strip() for x in head[2].split(",")[0].split(" - ", 1))
    log = [
        row
        for rows in tables
        for row in rows
        if len(row) >= 5 and CLOCK.fullmatch(row[1]) and row[0].strip().lower() in ("", *_NU_SIDES)
    ]
    if not home or not away or not (log or "ergebnis" in info or "result" in info):
        raise ProblemError(422, "report-unreadable", "The page is not a nuLiga game report")
    entries = [e for row in log if (e := _nu_entry(*row[:5])) is not None]
    rosters = [rows for rows in tables if any("Trikot" in r for r in rows[:2])]
    logged = {e.kind for e in entries}
    for rows, team in zip(rosters, ("home", "away"), strict=False):
        for kind, more in _roster_entries(rows, team).items():
            if kind not in logged:
                entries += more
    final, half = _result(info.get("ergebnis") or info.get("result") or "")
    return OfficialReport(
        provider=NULIGA,
        game_id=meeting,
        source_url=source_url,
        home=home,
        away=away,
        competition=(info.get("gruppe") or info.get("group") or (head[1] if len(head) > 1 else ""))
        or None,
        date=_iso_date(info.get("datum") or info.get("date") or h1),
        final=final,
        half_time=half,
        entries=sorted(entries, key=lambda x: x.clock_s),
    )


# a log entry in the PDF (two entries per line, names may wrap onto the next line)
_NU_PDF_ENTRY = re.compile(
    r"(?:(?P<team>Heim|Gast)\s+)?(?P<time>\d{1,2}:\d{2})\s+(?:(?P<score>\d{1,3}:\d{1,3})\s*)?"
    r"(?P<event>7m mit Tor|7m ohne Tor|Tor|2 ?-?Minuten|Verwarnung|"
    r"Disqualifikation(?: (?:mit|ohne) Bericht)?|Rote Karte|Blaue Karte|Auszeit (?:Heim|Gast))"
    r"(?=\s|$)"
)


def parse_nuliga_pdf(meeting: int, source_url: str, text: str) -> OfficialReport:
    """Text of a nuLiga game report PDF (meetingReportHB, `pdftotext -layout`)."""
    lines = text.splitlines()
    home = re.search(r"Heimmannschaft[ \t]{2,}(\S.*?)\s*$", text, re.MULTILINE)
    away = re.search(r"Gastmannschaft[ \t]{2,}(\S.*?)\s*$", text, re.MULTILINE)
    if not home or not away:
        raise ProblemError(422, "report-unreadable", "The PDF is not a nuLiga game report")
    group = re.search(r"Gruppe[ \t]{2,}(\S.*?)\s*$", text, re.MULTILINE)
    date = re.search(r"Datum[ \t]{2,}(\d{2}\.\d{2}\.\d{4})", text)
    result = re.search(r"^\s*Ergebnis[ \t]{2,}(\d.*)$", text, re.MULTILINE)
    final, half = _result(result.group(1)) if result else (None, None)
    start = next((i for i, ln in enumerate(lines) if ln.strip() == "Spielverlauf"), len(lines))
    rows: list[dict[str, Any]] = []
    previous: list[tuple[int, dict[str, Any]]] = []  # (column of the person, row) of last line
    for ln in lines[start + 1 :]:
        found = list(_NU_PDF_ENTRY.finditer(ln))
        current: list[tuple[int, dict[str, Any]]] = []
        rest: list[re.Match[str]] = []  # text that is no person of an entry of this line
        spans = [(0, found[0].start())] if found else [(0, len(ln))]
        for i, m in enumerate(found):
            end = found[i + 1].start() if i + 1 < len(found) else len(ln)
            chunks = list(re.finditer(r"\S+(?: \S+)*", ln[:end]))
            chunks = [c for c in chunks if c.start() >= m.end()]
            # the person follows the event closely; a chunk far right of it is a continuation
            person = chunks[0] if chunks and chunks[0].start() - m.end() <= 30 else None
            rest += [c for c in chunks if c is not person]
            row = {
                "team": m.group("team") or "",
                "time": m.group("time"),
                "score": m.group("score") or "",
                "event": m.group("event"),
                "person": person.group(0) if person else "",
            }
            rows.append(row)
            if person is not None:
                current.append((person.start(), row))
        for lo, hi in spans:
            rest += [c for c in re.finditer(r"\S+(?: \S+)*", ln) if lo <= c.start() < hi]
        # a name that did not fit goes on in the person column of the line above
        for chunk in rest:
            hit = [r for col, r in previous if abs(col - chunk.start()) <= 2]
            if hit and hit[0]["person"].endswith(","):
                hit[0]["person"] += " " + chunk.group(0)
        previous = current
    entries = [
        e
        for r in rows
        if (e := _nu_entry(r["team"], r["time"], r["score"], r["event"], r["person"])) is not None
    ]
    if not entries and not final:
        raise ProblemError(422, "report-unreadable", "No game log found in the nuLiga report")
    return OfficialReport(
        provider=NULIGA,
        game_id=meeting,
        source_url=source_url,
        home=home.group(1),
        away=away.group(1),
        competition=group.group(1) if group else (lines[0].strip() if lines else None) or None,
        date=_iso_date(date.group(1)) if date else None,
        final=final,
        half_time=half,
        entries=sorted(entries, key=lambda x: x.clock_s),
    )


async def fetch_nuliga(link: ReportLink, pdf_text: http.PdfText = http.pdf_text) -> str:
    """HTML of a nuLiga game report, or the text of its PDF (replaced by recorded data in
    tests)."""
    size = http.MAX_PDF_BYTES if link.pdf else http.MAX_HTML_BYTES
    body = await http.download(link.url, size, "nuLiga")
    if link.pdf:
        if not body.startswith(b"%PDF"):
            raise ProblemError(422, "report-unreadable", "The nuLiga link did not return a PDF")
        return await pdf_text(body)
    return body.decode("utf-8", errors="replace")
