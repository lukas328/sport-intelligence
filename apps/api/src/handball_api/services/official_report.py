"""Official match reports imported into a match (source "official_report").

Two public sources, read by URL:
- handball.ch match centre (GraphQL behind https://www.handball.ch/de/matchcenter/spiele/<id>):
  game, game log (every goal, shot, save, technical error, suspension, time-out with match time,
  shirt number and name) and player stats;
- DHB press report PDF (https://dhbdata.fmp.sportradar.com/match/<id>/pressReport.pdf), turned
  into text with `pdftotext -layout` (poppler-utils): goals, 7-metres, warnings, suspensions,
  disqualifications and time-outs.
Only these fixed hosts are contacted; the given URL only names the game.

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
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx
from sqlalchemy import delete, select

from handball_api.core.errors import ProblemError
from handball_api.models import Event, Match, Opponent, RosterEntry, VideoAsset
from handball_api.models.enums import VideoRole, VideoStatus
from handball_api.services import audit
from handball_api.services.auto_events import CANDIDATE, OFFICIAL, OVERLAY
from handball_api.services.context import Ctx
from handball_api.services.events import video_from_clock
from handball_api.services.matches import get_match
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

HANDBALL_CH = "handball_ch"
DHB = "dhb"
PROVIDERS = (HANDBALL_CH, DHB)
CH_API = "https://www.handball.ch/Umbraco/Api/MatchCenter/Query"
CH_PAGE = "https://www.handball.ch/de/matchcenter/spiele/{}"
DHB_PDF = "https://dhbdata.fmp.sportradar.com/match/{}/pressReport.pdf"
CH_QUERY = """query getReport($gameId: Int, $isLive: Boolean) {
  game(gameId: $gameId) { homeTeamName awayTeamName homeTeamScore awayTeamScore
    homeTeamScoreInterval awayTeamScoreInterval gameDateTime leagueName }
  gameLog(gameId: $gameId, isLive: $isLive) { actionText homeTeamActionLCID awayTeamActionLCID
    homeTeamPlayerStaffName homeTeamPlayerStaffNrDesc awayTeamPlayerStaffName
    awayTeamPlayerStaffNrDesc result timeInt timeString }
  gamePlayerStats(gameId: $gameId, isLive: $isLive) { dressNr isHome function } }"""


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


# ---- source detection ----------------------------------------------------------------------


def detect(source: str, provider: str | None = None) -> tuple[str, int]:
    """(provider, game id) from a match centre / press report URL, or a plain id + provider."""
    s = source.strip()
    if s.isdigit():
        if provider not in PROVIDERS:
            raise ProblemError(
                422, "report-url-unsupported", "A plain game id needs a provider (handball_ch, dhb)"
            )
        return str(provider), int(s)
    parts = urlsplit(s if "://" in s else f"https://{s}")
    host = (parts.hostname or "").lower()
    if host in ("handball.ch", "www.handball.ch"):
        m = re.search(r"/matchcenter/[^/]+/(\d{1,9})(?:/|$)", parts.path, re.IGNORECASE)
        if m:
            return HANDBALL_CH, int(m.group(1))
    if host in ("dhbdata.fmp.sportradar.com", "dhb.fmp.sportradar.com"):
        m = re.search(r"/match/(\d{1,9})(?:/|$)", parts.path)
        if m:
            return DHB, int(m.group(1))
    raise ProblemError(
        422,
        "report-url-unsupported",
        "Use a handball.ch match centre link (…/matchcenter/spiele/<id>) or a DHB press report "
        "link (dhbdata.fmp.sportradar.com/match/<id>/pressReport.pdf)",
    )


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
    body = {"query": CH_QUERY, "variables": {"gameId": game_id, "isLive": False}}
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, headers=HEADERS) as client:
            r = await client.post(CH_API, json=body)
            r.raise_for_status()
            payload = r.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise ProblemError(
            502, "report-unavailable", "handball.ch did not answer, try again later"
        ) from exc
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        raise ProblemError(502, "report-unavailable", "handball.ch answered without data")
    return data


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


async def fetch(source: str, provider: str | None = None) -> OfficialReport:
    kind, game_id = detect(source, provider)
    if kind == HANDBALL_CH:
        report = parse_handball_ch(game_id, await fetch_handball_ch(game_id))
    else:
        report = parse_dhb(game_id, await fetch_dhb(game_id))
    if not report.entries:
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


def _nearest(cands: list[Any], side: str, clock: float) -> Any | None:
    best = [c for c in cands if c.side == side and abs(c.clock_s - clock) <= MATCH_WINDOW_S]
    return min(best, key=lambda c: abs(c.clock_s - clock)) if best else None


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
        _Seen(g.side, float(g.clock_s), g.t_ms, g.x, g.y, g.source, g.confidence, g)
        for g in auto
        if g.clock_s is not None
    ]
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
        t_ms, x, y = video_from_clock(match, period, clock), None, None
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
                }
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
        ctx.db.add(
            Event(
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
        )
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

    warnings: list[str] = []
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
    duration_s = await ctx.db.scalar(
        select(VideoAsset.duration_s)
        .where(
            VideoAsset.match_id == match.id,
            VideoAsset.role == VideoRole.MAIN,
            VideoAsset.status == VideoStatus.READY,
        )
        .order_by(VideoAsset.created_at.desc())
        .limit(1)
    )
    length_ms = int(duration_s * 1000) if duration_s else None
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
