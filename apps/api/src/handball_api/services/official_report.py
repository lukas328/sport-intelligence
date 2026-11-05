"""Official match reports imported into a match (source "official_report").

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

`apply` stores the log as events of the match. Rules:
- a re-import replaces the earlier official_report events of the match;
- home/away become own/opponent via `match.is_home`; own players are linked by shirt number;
- the match minute is the clock: the first half is before `match.period_s` (30:00 in adults);
  an event exactly at the end of the half belongs to it while the score is the half-time score;
- goals are matched with the goals already stored, same side, at most 20 s of match clock apart:
  * a goal a person entered (tagging, feed, correction) wins: no official goal is added for it;
  * an automatic goal (score overlay, heuristic, a confirmed goal candidate) is the same goal
    seen on video: the official goal takes over its video time and shot position
    (attributes.video keeps what the video read) and the automatic row is dropped, so nothing is
    counted twice. Automatic goals without an official counterpart are kept when read from the
    overlay or confirmed by the coach (they show where the video and the report disagree) and
    dropped when only estimated (heuristic);
  * the other shots (saves, misses) the same way against the shots the coach confirmed on a
    shot candidate (same side and outcome): the official entry takes over the video time and the
    candidate now points to it; an entry confirmed on the video before a re-import keeps it;
  * entries without a video time from the video get theirs from the match clock
    (match_clock: the overlay clock of the analysis, entries with a known video time, the
    throw-offs), not counted linearly from the throw-off of the half;
  * suspensions, time-outs and the other entries are added as they are.

`comparison` lists the official goals next to what the video found (the import's video data, or an
automatic goal within the same 20 s) and the video goals without an official one; goals before
or after the main video (a clip of part of the game) are "outside", not missing. The coach
confirms or dismisses each row (`review`, kept in attributes.review, kept by a re-import).
"""

from __future__ import annotations

import asyncio
import contextlib
import re
import tempfile
import uuid
from dataclasses import dataclass, field
from dataclasses import replace as dc_replace
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit

import httpx
from sqlalchemy import delete, select

from handball_api.core.errors import ProblemError
from handball_api.integrations import handball_ch
from handball_api.models import Event, GoalCandidate, Match, Opponent, RosterEntry
from handball_api.services import audit, match_clock, org_verification
from handball_api.services.auto_events import CANDIDATE, OFFICIAL, OVERLAY
from handball_api.services.context import Ctx
from handball_api.services.events import video_from_clock
from handball_api.services.matches import duration_ms, get_match, timeline_video
from handball_api.services.policies import Action

SOURCE = OFFICIAL
# goals seen on video: an official goal takes over their video time (a confirmed goal candidate
# has no scorer; the report has)
AUTO_GOALS = ("heuristic", "model", OVERLAY, CANDIDATE)
REVIEW = ("confirmed", "dismissed")
MATCH_WINDOW_S = 20.0  # the overlay changes a few seconds after the goal; minutes are rounded
TIMEOUT = httpx.Timeout(15.0, connect=5.0)
HEADERS = {"User-Agent": "handball-ai/1.0 (official match report import)", "Accept-Language": "de"}
MAX_PDF_BYTES = 5_000_000
PDFTOTEXT_TIMEOUT_S = 20.0

MAX_HTML_BYTES = 2_000_000
MAX_REDIRECTS = 3

HANDBALL_CH = "handball_ch"
DHB = "dhb"
NULIGA = "nuliga"
HLA = "hla"
PROVIDERS = (HANDBALL_CH, DHB, NULIGA, HLA)
ID_PROVIDERS = (HANDBALL_CH, DHB, HLA)  # a plain game id names the game (nuLiga needs the host)
CH_PAGE = handball_ch.GAME_PAGE
DHB_PDF = "https://dhbdata.fmp.sportradar.com/match/{}/pressReport.pdf"
HLA_PDF = "https://infographics.sportradar.com/hla/pageSnapshot/pdf/de/{}"
# nuLiga portals of the handball associations (bhv-, hhv-, hvnb-, …, oehb-handball.liga.nu)
NULIGA_HOST = re.compile(r"[a-z]{2,12}-handball\.liga\.nu")
_NULIGA_PATH = re.compile(
    r"/cgi-bin/WebObjects/nuLiga(?P<doc>Dokument)?HB(?P<land>DE|AT)\.woa/wa/"
    r"(?P<action>groupMeetingReport|nuDokument)/?",
    re.IGNORECASE,
)
_NULIGA_CHAMPIONSHIP = re.compile(r"[\w .+/()-]{1,80}")


@dataclass(frozen=True)
class OfficialEntry:
    clock_s: int  # match second, 0..3600 (second half continues at 30:00)
    kind: str  # goal, penalty_goal, shot_saved, shot_missed, shot_post, penalty_saved, ...
    team: str | None  # home | away
    number: int | None = None
    name: str | None = None
    score: tuple[int, int] | None = None  # home, away after the entry
    goalkeeper_number: int | None = None  # saves: the keeper of the other team


@dataclass
class OfficialReport:
    provider: str
    game_id: int
    source_url: str
    home: str | None = None
    away: str | None = None
    competition: str | None = None
    date: str | None = None
    final: tuple[int, int] | None = None
    half_time: tuple[int, int] | None = None
    entries: list[OfficialEntry] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)  # shown as warnings of the import


@dataclass(frozen=True)
class ReportLink:
    """The one report to fetch: built from the checked parts of the given link."""

    provider: str
    game_id: int
    url: str
    pdf: bool = False


# ---- source detection ----------------------------------------------------------------------


_UNSUPPORTED = (
    "Use a handball.ch match centre link (…/matchcenter/spiele/<id>), a DHB press report link "
    "(dhbdata.fmp.sportradar.com/match/<id>/pressReport.pdf), a nuLiga game report "
    "(<association>-handball.liga.nu/…/groupMeetingReport?meeting=<id>&championship=…, or its "
    "PDF …/nuDokument?dokument=meetingReportHB&meeting=<id>) or an HLA report "
    "(infographics.sportradar.com/hla/pageSnapshot/pdf/de/<id>)"
)


def _nuliga_link(host: str, path: str, query: str) -> ReportLink | None:
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
        link = _nuliga_link(host, parts.path, parts.query)
        if link is not None:
            return link
    raise ProblemError(422, "report-url-unsupported", _UNSUPPORTED)


def detect(source: str, provider: str | None = None) -> tuple[str, int]:
    """(provider, game id) from a match centre / report URL, or a plain id + provider."""
    link = locate(source, provider)
    return link.provider, link.game_id


# ---- handball.ch ---------------------------------------------------------------------------

# role of each side in a handball.ch log entry (homeTeamActionLCID / awayTeamActionLCID)
_GK_ROLES = {"bParade"}


def _num(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    return int(value) if isinstance(value, str) and value.strip().isdigit() else None


def _score(value: Any) -> tuple[int, int] | None:
    m = re.fullmatch(r"\s*(\d+)\s*:\s*(\d+)\s*", str(value or ""))
    return (int(m.group(1)), int(m.group(2))) if m else None


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
        ("home" if p.get("isHome") else "away", _num(p.get("dressNr")))
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
                _num(e.get(f"{side}TeamPlayerStaffNrDesc")),
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
                score=_score(e.get("result")),
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


def without_opponent_names(report: OfficialReport, is_home: bool) -> OfficialReport:
    """Numbers only for the other team (clubs not verified yet see no names of other teams'
    players, services/org_verification.py)."""
    opponent = "away" if is_home else "home"
    return dc_replace(
        report,
        entries=[dc_replace(e, name=None) if e.team == opponent else e for e in report.entries],
    )


# ---- DHB press report ----------------------------------------------------------------------

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
                number=_num(w.group(2)) if w else None,
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


async def _pdf_text(pdf: bytes) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "report.pdf"
        path.write_bytes(pdf)
        try:
            proc = await asyncio.create_subprocess_exec(
                "pdftotext",
                "-layout",
                "-enc",
                "UTF-8",
                str(path),
                "-",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
        except FileNotFoundError as exc:
            raise ProblemError(
                503, "report-unavailable", "Reading PDF reports is not set up (pdftotext)"
            ) from exc
        try:
            out, _ = await asyncio.wait_for(proc.communicate(), PDFTOTEXT_TIMEOUT_S)
        except TimeoutError as exc:
            with contextlib.suppress(ProcessLookupError):
                proc.kill()
            raise ProblemError(422, "report-unreadable", "The PDF could not be read") from exc
    if proc.returncode != 0:
        raise ProblemError(422, "report-unreadable", "The PDF could not be read")
    return out.decode("utf-8", errors="replace")


async def fetch_dhb(match_id: int) -> str:
    """Text of a DHB press report (replaced by recorded text in tests)."""
    url = DHB_PDF.format(match_id)
    try:
        async with (
            httpx.AsyncClient(
                timeout=TIMEOUT, headers=HEADERS, follow_redirects=True, max_redirects=3
            ) as client,
            client.stream("GET", url) as r,
        ):
            if r.status_code == 404:
                raise ProblemError(404, "report-not-found", f"DHB has no press report {match_id}")
            r.raise_for_status()
            pdf = bytearray()
            async for chunk in r.aiter_bytes():
                pdf += chunk
                if len(pdf) > MAX_PDF_BYTES:
                    raise ProblemError(422, "report-unreadable", "The PDF is too large")
    except httpx.HTTPError as exc:
        raise ProblemError(
            502, "report-unavailable", "The DHB server did not answer, try again later"
        ) from exc
    if not pdf.startswith(b"%PDF"):
        raise ProblemError(422, "report-unreadable", "The DHB link did not return a PDF")
    return await _pdf_text(bytes(pdf))


# ---- nuLiga game report --------------------------------------------------------------------


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


_CLOCK = re.compile(r"(\d{1,2}):(\d{2})")
_NU_SIDES = {"heim": "home", "home": "home", "gast": "away", "guest": "away", "away": "away"}
_NU_PERSON = re.compile(r"(?P<nr>\d{1,3}|[A-Z])\s+(?P<name>\S.*)")


def _clock_s(value: str) -> int | None:
    m = _CLOCK.fullmatch(value.strip())
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


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
    clock = _clock_s(time)
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
        number=_num(p.group("nr")) if p else None,  # team officials (A-D) have no number
        name=name or None,
        score=_score(score),
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
            clock = _clock_s(row[col])
            if clock is not None:
                out.setdefault(kind, []).append(
                    OfficialEntry(
                        clock_s=clock,
                        kind=kind,
                        team=team,
                        number=_num(row[0]),
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
        if len(row) >= 5 and _CLOCK.fullmatch(row[1]) and row[0].strip().lower() in ("", *_NU_SIDES)
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


async def _download(url: str, max_bytes: int, what: str) -> bytes:
    """One GET with timeouts and a size limit; redirects are followed on the same host only."""
    host = urlsplit(url).hostname
    try:
        async with httpx.AsyncClient(
            timeout=TIMEOUT, headers=HEADERS, follow_redirects=False
        ) as client:
            for _ in range(MAX_REDIRECTS + 1):
                async with client.stream("GET", url) as r:
                    if r.is_redirect:
                        target = urljoin(url, r.headers.get("location", ""))
                        parts = urlsplit(target)
                        if parts.scheme != "https" or parts.hostname != host:
                            raise ProblemError(
                                502, "report-unavailable", f"{what} sent the report elsewhere"
                            )
                        url = target
                        continue
                    if r.status_code == 404:
                        raise ProblemError(404, "report-not-found", f"{what} has no such report")
                    r.raise_for_status()
                    body = bytearray()
                    async for chunk in r.aiter_bytes():
                        body += chunk
                        if len(body) > max_bytes:
                            raise ProblemError(422, "report-unreadable", "The report is too large")
                    return bytes(body)
    except httpx.HTTPError as exc:
        raise ProblemError(
            502, "report-unavailable", f"{what} did not answer, try again later"
        ) from exc
    raise ProblemError(502, "report-unavailable", f"{what} redirected too often")


async def fetch_nuliga(link: ReportLink) -> str:
    """HTML of a nuLiga game report, or the text of its PDF (replaced by recorded data in
    tests)."""
    body = await _download(link.url, MAX_PDF_BYTES if link.pdf else MAX_HTML_BYTES, "nuLiga")
    if link.pdf:
        if not body.startswith(b"%PDF"):
            raise ProblemError(422, "report-unreadable", "The nuLiga link did not return a PDF")
        return await _pdf_text(body)
    return body.decode("utf-8", errors="replace")


# ---- HLA (Sportradar) match report ---------------------------------------------------------

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
                        clock_s=_clock_s(m.group(1)) or 0,
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


async def fetch_hla(match_id: int) -> str:
    """Text of an HLA match report PDF (replaced by recorded text in tests)."""
    pdf = await _download(HLA_PDF.format(match_id), MAX_PDF_BYTES, "Sportradar (HLA)")
    if not pdf.startswith(b"%PDF"):
        raise ProblemError(422, "report-unreadable", "The HLA link did not return a PDF")
    return await _pdf_text(pdf)


async def fetch(source: str, provider: str | None = None) -> OfficialReport:
    link = locate(source, provider)
    if link.provider == HANDBALL_CH:
        report = parse_handball_ch(link.game_id, await fetch_handball_ch(link.game_id))
    elif link.provider == DHB:
        report = parse_dhb(link.game_id, await fetch_dhb(link.game_id))
    elif link.provider == NULIGA:
        page = await fetch_nuliga(link)
        report = (
            parse_nuliga_pdf(link.game_id, link.url, page)
            if link.pdf
            else parse_nuliga(link.game_id, link.url, page)
        )
    else:
        report = parse_hla(link.game_id, await fetch_hla(link.game_id))
    # the HLA report has no timed goals: its result alone is still worth importing
    if not report.entries and not (report.provider == HLA and report.final):
        raise ProblemError(
            422, "report-empty", "The report has no game log yet (not played or no live ticker)"
        )
    return report


# ---- apply to a match ----------------------------------------------------------------------

# kind -> event fields
_EVENTS: dict[str, dict[str, str]] = {
    "goal": {"type": "shot", "outcome": "goal"},
    "shot_saved": {"type": "shot", "outcome": "save"},
    "shot_missed": {"type": "shot", "outcome": "miss"},
    "shot_post": {"type": "shot", "outcome": "post"},
    "penalty_goal": {"type": "shot", "outcome": "goal", "shot_type": "penalty"},
    "penalty_saved": {"type": "shot", "outcome": "save", "shot_type": "penalty"},
    "penalty_missed": {"type": "shot", "outcome": "miss", "shot_type": "penalty"},
    "penalty_post": {"type": "shot", "outcome": "post", "shot_type": "penalty"},
    "turnover": {"type": "turnover"},
    "suspension": {"type": "suspension_2min"},
    "warning": {"type": "yellow_card"},
    "disqualification": {"type": "red_card"},
    "timeout": {"type": "timeout"},
}


@dataclass
class _Seen:
    """A goal already known from video: an automatic event, or the video data an earlier import
    took over from one."""

    side: str
    clock_s: float
    t_ms: int | None
    x: float | None
    y: float | None
    source: str
    confidence: float
    event: Event | None = None
    outcome: str = "goal"
    candidate_id: str | None = None  # the video candidate it was confirmed on


def _candidate_of(e: Event) -> str | None:
    """The candidate an event was confirmed on: its own event, or a report entry it pinned."""
    attrs = e.attributes or {}
    v = attrs.get("video")
    if isinstance(v, dict) and v.get("candidate_id"):
        return str(v["candidate_id"])
    c = attrs.get("goal_candidate")
    return str(c) if c else None


def _period(e: OfficialEntry, period_s: int, half_time: tuple[int, int] | None) -> int:
    if e.clock_s < period_s:
        return 1
    # an entry right at the end of the half (a last goal at 30:00): first half while the score
    # is still the half-time score
    at_end = e.clock_s == period_s and half_time is not None
    if at_end and (e.score is None or sum(e.score) <= sum(half_time or (0, 0))):
        return 1
    return 2


def _words(name: str | None) -> set[str]:
    return {w for w in re.split(r"[^\w]+", (name or "").casefold()) if len(w) >= 4}


def _nearest(cands: list[Any], side: str, clock: float, outcome: str = "goal") -> Any | None:
    best = [
        c
        for c in cands
        if c.side == side
        and getattr(c, "outcome", "goal") == outcome
        and abs(c.clock_s - clock) <= MATCH_WINDOW_S
    ]
    return min(best, key=lambda c: abs(c.clock_s - clock)) if best else None


async def _analysis(ctx: Ctx, match: Match) -> dict[str, Any] | None:
    """The analysis of the match's timeline video (its overlay clock maps the report)."""
    video = await timeline_video(ctx, match.id)
    return video.analysis if video is not None else None


def _clock_time(cm: match_clock.ClockMap, match: Match, period: int, clock: float) -> int | None:
    t, _ = cm.video_ms(period, clock) if period in (1, 2) else (None, None)
    return t if t is not None else video_from_clock(match, period, clock)


async def apply(ctx: Ctx, match: Match, report: OfficialReport) -> dict[str, Any]:
    previous = (
        await ctx.db.scalars(
            select(Event).where(Event.match_id == match.id, Event.source == SOURCE)
        )
    ).all()
    seen: list[_Seen] = []
    reviewed = {  # the coach's check of a goal survives a re-import of the same report
        (p.side, p.clock_s): r
        for p in previous
        if p.outcome == "goal" and (r := (p.attributes or {}).get("review")) in REVIEW
    }
    for p in previous:  # video data an earlier import took over: matched again below
        v = (p.attributes or {}).get("video")
        if isinstance(v, dict) and v.get("clock_s") is not None:
            seen.append(
                _Seen(
                    side=p.side,
                    clock_s=float(v["clock_s"]),
                    t_ms=v.get("t_ms"),
                    x=p.x,
                    y=p.y,
                    source=str(v.get("source", OVERLAY)),
                    confidence=float(v.get("confidence", 0.9)),
                    outcome=p.outcome or "goal",
                    candidate_id=_candidate_of(p),
                )
            )
    await ctx.db.execute(delete(Event).where(Event.match_id == match.id, Event.source == SOURCE))
    goals = (
        await ctx.db.scalars(
            select(Event).where(
                Event.match_id == match.id, Event.type == "shot", Event.outcome == "goal"
            )
        )
    ).all()
    auto = [g for g in goals if g.source in AUTO_GOALS]
    seen += [
        _Seen(
            g.side,
            float(g.clock_s),
            g.t_ms,
            g.x,
            g.y,
            g.source,
            g.confidence,
            g,
            candidate_id=_candidate_of(g),
        )
        for g in auto
        if g.clock_s is not None
    ]
    # saves and misses the coach confirmed on a shot candidate: matched like automatic goals
    confirmed_shots = (
        await ctx.db.scalars(
            select(Event).where(
                Event.match_id == match.id,
                Event.type == "shot",
                Event.outcome != "goal",
                Event.source == CANDIDATE,
                Event.clock_s.is_not(None),
            )
        )
    ).all()
    seen += [
        _Seen(
            g.side,
            float(g.clock_s or 0.0),
            g.t_ms,
            g.x,
            g.y,
            g.source,
            g.confidence,
            g,
            outcome=g.outcome or "miss",
            candidate_id=_candidate_of(g),
        )
        for g in confirmed_shots
    ]
    clock_map = match_clock.build(match, await _analysis(ctx, match), [])
    manual = [
        _Seen(g.side, float(g.clock_s), g.t_ms, g.x, g.y, g.source, g.confidence, g)
        for g in goals
        if g.source not in AUTO_GOALS and g.clock_s is not None
    ]
    roster = {
        n: pid
        for n, pid in (
            await ctx.db.execute(
                select(RosterEntry.jersey_number, RosterEntry.player_id).where(
                    RosterEntry.season_id == match.season_id,
                    RosterEntry.team_id == match.team_id,
                    RosterEntry.active.is_(True),
                )
            )
        ).all()
        if n is not None
    }
    own_team = "home" if match.is_home else "away"

    created, matched, kept_manual, skipped = 0, 0, 0, 0
    unknown_numbers: set[int] = set()
    used: set[int] = set()  # ids of matched candidates
    relink: list[tuple[str, Event]] = []  # video candidate -> the new official event
    for e in report.entries:
        spec = _EVENTS.get(e.kind)
        if spec is None or e.team is None:
            skipped += 1
            continue
        side = "own" if e.team == own_team else "opponent"
        period = _period(e, match.period_s, report.half_time)
        clock = float(e.clock_s)
        attrs: dict[str, Any] = {"official_time": f"{e.clock_s // 60:02d}:{e.clock_s % 60:02d}"}
        if e.name:
            attrs["name"] = e.name[:80]
        if e.score:
            attrs["score"] = list(e.score if own_team == "home" else e.score[::-1])
        t_ms, x, y = _clock_time(clock_map, match, period, clock), None, None
        pinned: _Seen | None = None
        if spec.get("type") == "shot" and spec.get("outcome") != "goal":
            pinned = _nearest(
                [c for c in seen if id(c) not in used], side, clock, str(spec["outcome"])
            )
            if pinned is not None:
                used.add(id(pinned))
                if pinned.t_ms is not None:
                    t_ms = int(pinned.t_ms)
                attrs["video"] = {
                    "source": pinned.source,
                    "clock_s": pinned.clock_s,
                    "t_ms": pinned.t_ms,
                    "confidence": round(pinned.confidence, 3),
                    **({"candidate_id": pinned.candidate_id} if pinned.candidate_id else {}),
                }
        if spec.get("outcome") == "goal":
            free = [c for c in manual if id(c) not in used]
            hit = _nearest(free, side, clock)
            if hit is not None:  # entered by a person: theirs wins
                used.add(id(hit))
                kept_manual += 1
                continue
            vid = _nearest([c for c in seen if id(c) not in used], side, clock)
            if vid is not None:
                used.add(id(vid))
                matched += 1
                if vid.t_ms is not None:
                    t_ms = int(vid.t_ms)
                x, y = vid.x, vid.y
                attrs["video"] = {
                    "source": vid.source,
                    "clock_s": vid.clock_s,
                    "t_ms": vid.t_ms,
                    "confidence": round(vid.confidence, 3),
                    **({"candidate_id": vid.candidate_id} if vid.candidate_id else {}),
                }
                pinned = vid
            if (side, clock) in reviewed:
                attrs["review"] = reviewed[(side, clock)]
        if spec.get("outcome") == "save" and e.goalkeeper_number is not None:
            gk = roster.get(e.goalkeeper_number) if side == "opponent" else None
            attrs.update(
                {"goalkeeper_id": str(gk)} if gk else {"goalkeeper_number": e.goalkeeper_number}
            )
        player = roster.get(e.number) if side == "own" and e.number is not None else None
        if side == "own" and e.number is not None and player is None:
            unknown_numbers.add(e.number)
        new = Event(
            organization_id=match.organization_id,
            match_id=match.id,
            type=spec["type"],
            side=side,
            period=period,
            clock_s=clock,
            t_ms=t_ms,
            number=e.number,
            player_id=player,
            outcome=spec.get("outcome"),
            shot_type=spec.get("shot_type"),
            shot_zone="penalty" if spec.get("shot_type") == "penalty" else None,
            x=x,
            y=y,
            source=SOURCE,
            confidence=1.0,
            attributes=attrs,
        )
        ctx.db.add(new)
        if pinned is not None and pinned.candidate_id:
            relink.append((pinned.candidate_id, new))
        created += 1

    # automatic goals: the matched ones are now official goals; estimates without a counterpart
    # are dropped (the report has every goal), overlay readings and goals the coach confirmed
    # from a candidate without one stay for checking
    taken = {id(c.event) for c in seen if c.event is not None and id(c) in used}
    unmatched_video = 0
    for g in auto:
        if id(g) in taken or g.source not in (OVERLAY, CANDIDATE):
            await ctx.db.delete(g)
        else:
            unmatched_video += 1
    for g in confirmed_shots:  # the official entry took over: one shot, not two
        if id(g) in taken:
            await ctx.db.delete(g)
    await ctx.db.flush()
    for cand_id, ev in relink:  # the candidate now points to the official entry
        with contextlib.suppress(ValueError):
            c = await ctx.db.get(GoalCandidate, uuid.UUID(cand_id))
            if c is not None and c.match_id == match.id and c.status == "confirmed":
                c.event_id = ev.id

    warnings: list[str] = list(report.notes)
    final = report.final
    if final is not None:
        own, opp = final if own_team == "home" else final[::-1]
        half = report.half_time
        if match.score_own is None and match.score_opponent is None:
            match.score_own, match.score_opponent = own, opp
            if half is not None and match.halftime_own is None:
                match.halftime_own, match.halftime_opponent = (
                    half if own_team == "home" else half[::-1]
                )
        elif (match.score_own, match.score_opponent) != (own, opp):
            warnings.append(
                f"stored result {match.score_own}:{match.score_opponent} differs from the "
                f"report ({own}:{opp})"
            )
    if unknown_numbers:
        warnings.append(f"numbers not in the roster: {sorted(unknown_numbers)}")
    opp_name = (
        await ctx.db.scalar(select(Opponent.name).where(Opponent.id == match.opponent_id))
        if match.opponent_id
        else None
    )
    their = report.away if own_team == "home" else report.home
    ours = report.home if own_team == "home" else report.away
    if opp_name and not _words(opp_name) & _words(their) and _words(opp_name) & _words(ours):
        warnings.append(
            f"'{opp_name}' is the {own_team} team in the report: check home/away of the match"
        )
    match.report_extra = {
        **(match.report_extra or {}),
        "official_report": {
            "provider": report.provider,
            "game_id": report.game_id,
            "url": report.source_url,
            "home": report.home,
            "away": report.away,
        },
    }
    await ctx.db.flush()
    result = {
        "provider": report.provider,
        "game_id": report.game_id,
        "source_url": report.source_url,
        "home": report.home,
        "away": report.away,
        "final": list(report.final) if report.final else None,
        "created": created,
        "replaced": len(previous),
        "matched_video_goals": matched,
        "unmatched_video_goals": unmatched_video,
        "kept_manual_goals": kept_manual,
        "skipped": skipped,
        "warnings": warnings,
    }
    await audit.record(
        ctx,
        "match.official_report_imported",
        target_type="match",
        target_id=match.id,
        data={k: result[k] for k in ("provider", "game_id", "created", "matched_video_goals")},
    )
    return result


async def import_report(
    ctx: Ctx, match_id: uuid.UUID, source: str, provider: str | None = None
) -> dict[str, Any]:
    """Checks the rights before anything is fetched."""
    match = await get_match(ctx, match_id, Action.EVENT_WRITE)
    report = await fetch(source, provider)
    if await org_verification.is_unverified(ctx, match.organization_id):
        report = without_opponent_names(report, match.is_home)
    return await apply(ctx, match, report)


# ---- official goals compared with the video ------------------------------------------------


def _official_time(clock_s: float | None) -> str | None:
    if clock_s is None:
        return None
    c = int(clock_s)
    return f"{c // 60:02d}:{c % 60:02d}"


def _review(e: Event) -> str | None:
    r = (e.attributes or {}).get("review")
    return r if r in REVIEW else None


def _video_goal(e: Event) -> dict[str, Any]:
    attrs = e.attributes or {}
    return {
        "event_id": e.id,
        "side": e.side,
        "period": e.period,
        "clock_s": e.clock_s,
        "official_time": _official_time(e.clock_s),
        "t_ms": e.t_ms,
        "source": e.source,
        "confidence": round(e.confidence, 3),
        "number": e.number,
        "player_id": e.player_id,
        "name": attrs.get("scorer_name"),
        "score": attrs.get("score"),
        "review": _review(e),
    }


async def comparison(ctx: Ctx, match_id: uuid.UUID) -> dict[str, Any]:
    """Each official goal with what the video found: the video data the import took over (or the
    analysis noted), else an automatic goal of the same side within MATCH_WINDOW_S of match
    clock, as the import pairs them; then the automatic goals without an official counterpart.
    An official goal the video did not find whose time (from the match clock) lies before or after
    the main video is "outside": a clip of a few minutes is not missing the rest of the game."""
    match = await get_match(ctx, match_id)
    length_ms = duration_ms(await timeline_video(ctx, match.id, ready=True))
    goals = (
        await ctx.db.scalars(
            select(Event)
            .where(Event.match_id == match.id, Event.type == "shot", Event.outcome == "goal")
            .order_by(Event.period, Event.clock_s.nulls_last(), Event.t_ms.nulls_last())
        )
    ).all()
    official = [g for g in goals if g.source == SOURCE]
    auto = [g for g in goals if g.source in AUTO_GOALS]
    cands = [
        _Seen(g.side, float(g.clock_s), g.t_ms, g.x, g.y, g.source, g.confidence, g)
        for g in auto
        if g.clock_s is not None
    ]
    used: set[int] = set()
    rows: list[dict[str, Any]] = []
    for o in official:
        stored = (o.attributes or {}).get("video")
        video: dict[str, Any] | None = None
        if isinstance(stored, dict):
            video = {
                "source": str(stored.get("source", OVERLAY)),
                "t_ms": stored.get("t_ms"),
                "clock_s": stored.get("clock_s"),
                "confidence": stored.get("confidence"),
                "event_id": None,
            }
        elif o.clock_s is not None:
            hit = _nearest([c for c in cands if id(c) not in used], o.side, float(o.clock_s))
            if hit is not None and hit.event is not None:
                used.add(id(hit))
                video = {
                    "source": hit.source,
                    "t_ms": hit.t_ms,
                    "clock_s": hit.clock_s,
                    "confidence": round(hit.confidence, 3),
                    "event_id": hit.event.id,
                }
        video_t = video.get("t_ms") if video else None
        t_ms = int(video_t) if video_t is not None else o.t_ms
        status = "found" if video else "missing"
        if (
            status == "missing"
            and t_ms is not None
            and length_ms is not None
            and not 0 <= t_ms <= length_ms
        ):
            status = "outside"
        attrs = o.attributes or {}
        rows.append(
            {
                "event_id": o.id,
                "side": o.side,
                "period": o.period,
                "clock_s": o.clock_s,
                "official_time": attrs.get("official_time") or _official_time(o.clock_s),
                # where the video shows it: the video reading, else the time from the clock
                "t_ms": t_ms,
                "estimated": video_t is None,
                "number": o.number,
                "player_id": o.player_id,
                "name": attrs.get("name"),
                "score": attrs.get("score"),
                "penalty": o.shot_type == "penalty",
                "status": status,
                "video": video,
                "review": _review(o),
            }
        )
    paired = {id(c.event) for c in cands if id(c) in used}
    extra = [_video_goal(g) for g in auto if id(g) not in paired]
    found = sum(1 for r in rows if r["status"] == "found")
    outside = sum(1 for r in rows if r["status"] == "outside")
    report = (match.report_extra or {}).get("official_report") or {}
    return {
        "imported": bool(report) or bool(official),
        "provider": report.get("provider"),
        "source_url": report.get("url"),
        "home": report.get("home"),
        "away": report.get("away"),
        "window_s": MATCH_WINDOW_S,
        "counts": {
            "official": len(rows),
            "found": found,
            "missing": len(rows) - found - outside,
            "outside": outside,
            "extra": len(extra),
            "open": sum(1 for r in rows if r["status"] == "missing" and r["review"] is None)
            + sum(1 for r in extra if r["review"] is None),
        },
        "goals": rows,
        "extra": extra,
    }


async def review(ctx: Ctx, match_id: uuid.UUID, event_id: uuid.UUID, status: str | None) -> None:
    """The coach checked a row of the comparison: an official goal (its video time is right, or
    not) or a video goal without an official one (a real goal, or a misreading)."""
    match = await get_match(ctx, match_id, Action.EVENT_WRITE)
    ev = await ctx.db.get(Event, event_id)
    if (
        ev is None
        or ev.match_id != match.id
        or ev.type != "shot"
        or ev.outcome != "goal"
        or ev.source not in (SOURCE, *AUTO_GOALS)
    ):
        raise ProblemError(404, "not-found", "Goal not found in the comparison")
    attrs = {k: v for k, v in (ev.attributes or {}).items() if k != "review"}
    if status is not None:
        attrs["review"] = status
    ev.attributes = attrs
    await audit.record(
        ctx,
        "match.official_goal_reviewed",
        target_type="match",
        target_id=match.id,
        data={"event_id": str(ev.id), "source": ev.source, "review": status},
    )
