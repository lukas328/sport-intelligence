"""Match the raw game videos (videos.csv, ingest state) to official handball.ch games and build a
catalog of all games.

For every game name (country_league..._home_away_date, CamelCase club names, "ca" = approximate
date) the handball.ch game id comes from the video description when it links the match centre
(".../matchcenter/spiele/484345"), otherwise from a search of the public match centre GraphQL API:
the season menu (`menuItem`) gives the groups and cups of the league in the name, `games(groupId)`
their games, `games(clubId, seasonId)` all games of a club, `natiGames(teamId)` the national teams.
Candidates are filtered by date (+-1 day; a season range for approximate dates, then the video's
upload/stream date as tie-break) and fuzzy team names (umlauts, prefixes such as SG/HSG/TV/HC).

Outputs (re-runnable; the ingest keeps adding games):
- ml/data/official/<name>.json: source, game_id, home, away, date, result, league, log, players
  (same shape as ml/eval/official/*.json from fetch_handball_ch.py)
- ml/data/catalog.json: one entry per game name: parsed name, game_id or null with a reason,
  log/goal counts, video resolution/fps/duration and the Kaggle batch from the ingest state.

API responses are cached under <scratch>/official_cache/ (0.5 s between network requests).

usage: python ml/data/match_official.py [--only SUBSTR] [--refresh-drive] [-v]
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

URL = "https://www.handball.ch/Umbraco/Api/MatchCenter/Query"
HEADERS = {
    "Content-Type": "application/json",
    "Accept-Language": "de",
    "User-Agent": "handball-ai/1.0 (research)",
}
GAME_URL = "https://www.handball.ch/de/matchcenter/spiele/{}"
ROOT = Path(__file__).resolve().parent
SCRATCH = Path(os.environ.get(
    "HANDBALL_SCRATCH",
    "/tmp/claude-0/-home-user/3dc450e2-2499-5e21-b252-1c4e366c6b5a/scratchpad",
))
NATI_TEAM = {"M": 1, "F": 5}  # data-team-id on handball.ch/de/nationalteams/a-team-*

GAME_FIELDS = """objectId gameNumber seasonId gameDateTime homeTeamId homeTeamName homeTeamClubId
  homeTeamScore awayTeamId awayTeamName awayTeamClubId awayTeamScore leagueShortName groupShortName
  gameTypeId gameStatusId gameGroupOrCupId"""
Q_SEASONS = "{ season { objectId name dateFrom dateTo isActual } }"
Q_CLUBS = "{ club { clubId name city } }"
Q_MENU = """query getSeasons($seasonId: Int){ menuItem(seasonId: $seasonId) {
  name objectId objectType menuItem { name objectId objectType
  menuItem { name objectId objectType } } } }"""
Q_GROUP_GAMES = f"query getGames($groupId: Int){{ games(groupId: $groupId) {{ {GAME_FIELDS} }} }}"
Q_CLUB_GAMES = ("query getGames($clubId: Int, $seasonId: Int){ games(clubId: $clubId, "
                f"seasonId: $seasonId) {{ {GAME_FIELDS} }} }}")
Q_NATI = """query getNatiGames($teamId: Int){ natiGames(teamId: $teamId) { games { objectId
  seasonId gameDateTime homeTeamName homeTeamScore awayTeamName awayTeamScore groupName } } }"""
Q_GAME = """query getGame($gameId: Int, $isLive: Boolean){ game(gameId: $gameId, isLive: $isLive) {
  gameId seasonId gameDateTime homeTeamName homeTeamClubId homeTeamScore awayTeamName awayTeamClubId
  awayTeamScore leagueShortName groupShortName gameStatusId } }"""
Q_LOG = """query getGameLog($gameId: Int, $isLive: Boolean){
  gameLog(gameId: $gameId, isLive: $isLive) { actionGroup actionText homeTeamPlayerStaffName
  homeTeamPlayerStaffNrDesc awayTeamPlayerStaffName awayTeamPlayerStaffNrDesc result timeInt
  timeString } }"""
Q_PLAYERS = """query getGamePlayerStats($gameId: Int, $isLive: Boolean){
  gamePlayerStats(gameId: $gameId, isLive: $isLive) { teamName dressNr playerName totalScore
  totalShots totalScore7m totalShots7m totalSaves totalShotsGK total2Minutes isHome function } }"""

LINK = re.compile(r"handball\.ch/[^\s\"'<>]*?(?:spiele|games?|matchs?|partite)/(\d{5,7})", re.I)
DAY = timedelta(days=1)


# --- API with disk cache ------------------------------------------------------------------------

class Api:
    def __init__(self, cache: Path, verbose: bool = False) -> None:
        self.cache = cache
        self.cache.mkdir(parents=True, exist_ok=True)
        self.verbose = verbose
        self.requests = 0
        self.last = 0.0

    def query(self, q: str, variables: dict[str, Any] | None = None,
              max_age_h: float | None = None) -> dict[str, Any]:
        """Cached POST; max_age_h None = keep forever (finished seasons, played games)."""
        variables = variables or {}
        name = (re.search(r"query (\w+)", q) or re.search(r"\{\s*(\w+)", q))
        key = hashlib.sha1(json.dumps([" ".join(q.split()), variables], sort_keys=True)
                           .encode()).hexdigest()[:16]
        path = self.cache / f"{name.group(1) if name else 'q'}_{key}.json"
        if path.exists():
            hit = json.loads(path.read_text())
            if max_age_h is None or time.time() - hit["fetched"] < max_age_h * 3600:
                return dict(hit["data"])
        wait = 0.5 - (time.time() - self.last)
        if wait > 0:
            time.sleep(wait)
        body = json.dumps({"query": q, "variables": variables}).encode()
        for attempt in range(3):
            try:
                req = urllib.request.Request(URL, body, HEADERS)
                with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310
                    res = json.load(r)
                break
            except (urllib.error.URLError, TimeoutError) as exc:
                if attempt == 2:
                    raise
                print(f"  retry after {exc}", file=sys.stderr)
                time.sleep(5 * (attempt + 1))
        self.last = time.time()
        self.requests += 1
        if self.verbose:
            print(f"  api {path.stem} {variables}", file=sys.stderr)
        data: dict[str, Any] = res.get("data") or {}
        if res.get("errors") and not any(data.values()):
            raise RuntimeError(f"{path.stem}: {res['errors']}")
        path.write_text(json.dumps({"fetched": time.time(), "variables": variables, "data": data},
                                   ensure_ascii=False))
        return data


# --- names ---------------------------------------------------------------------------------------

# tokens of the name that describe league, round or stage rather than a team
LEAGUE_WORDS = {
    "nla", "nlb", "qhl", "spl1", "spl2", "1liga", "2liga", "3liga", "frauen", "herren", "cup",
    "cupfinal", "supercup", "regiocup", "final", "final4", "finalissima", "halbf", "playofffinal",
    "playofffinal4", "playoffhf", "playofff1", "playofff2", "test", "aufstieg", "romandie",
    "europa", "nati", "u19e", "u17e", "u19p", "u15i", "u17i", "u19i", "u15e", "ram", "vs",
}
SUFFIX_WORDS = {"hz1", "hz2", "b", "frauen1", "frauen2"}
PREFIXES = {"sg", "hsg", "tv", "hc", "bsv", "gc"}
VARIANT = {"espoirs", "future", "u21", "u19", "u17", "u15", "u13", "academy", "junioren",
           "juniorinnen"}
ROMAN = {"ii": "2", "iii": "3", "iv": "4"}
ALIASES = {"niederlande": "holland"}


@dataclass
class Parsed:
    name: str
    country: str
    league: list[str]
    teams: list[str]
    day: date | None = None
    date_from: date | None = None
    date_to: date | None = None
    date_kind: str = "none"  # exact | month | year | approx | none
    date_text: str = ""
    women: bool = False
    tags: list[str] = field(default_factory=list)


def parse_name(name: str) -> Parsed:
    parts = name.split("_")
    country = parts[0]
    rest = parts[1:]
    p = Parsed(name, country, [], [])
    if rest:
        last = rest[-1]
        m = re.fullmatch(r"(ca)?(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?", last)
        if m:
            rest = rest[:-1]
            p.date_text = last
            y = int(m.group(2))
            if m.group(4):
                p.day = date(y, int(m.group(3)), int(m.group(4)))
                p.date_from = p.date_to = p.day
                p.date_kind = "approx" if m.group(1) else "exact"
            elif m.group(3):
                p.date_from = date(y, int(m.group(3)), 1)
                p.date_to = (p.date_from + timedelta(days=32)).replace(day=1) - DAY
                p.date_kind = "month"
            else:
                p.date_kind = "approx" if m.group(1) else "year"
                # a season straddles the year; approximate years are often off by one
                pad = 1 if m.group(1) else 0
                p.date_from = date(y - pad, 1, 1)
                p.date_to = date(y + pad, 12, 31)
    while rest and rest[-1].lower() in SUFFIX_WORDS:
        p.tags.append(rest.pop())
    for t in rest:
        (p.league if t.lower() in LEAGUE_WORDS else p.teams).append(t)
    p.women = "Frauen" in p.league
    return p


def fold(s: str) -> str:
    s = s.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("Ä", "Ae")
    s = s.replace("Ö", "Oe").replace("Ü", "Ue").replace("ß", "ss")
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def camel_tokens(t: str) -> list[str]:
    return [x.lower() for x in re.findall(r"[A-Z]+(?=[A-Z][a-z]|\d|$)|[A-Z]?[a-z]+|\d+", t)]


def api_tokens(name: str) -> list[str]:
    name = re.sub(r"\([^)]*\)", " ", fold(name or ""))
    return [ROMAN.get(t, t) for t in re.findall(r"[a-z0-9]+", name)]


def team_score(video_team: str, api_name: str) -> float:
    """0..1: weighted share of the video name's tokens found in the official team name, minus a
    penalty for second teams / youth teams the video name does not mention."""
    joined_v = fold(video_team)
    vt = camel_tokens(video_team)
    if joined_v in ALIASES:
        joined_v = ALIASES[joined_v]
        vt = [joined_v]
    at = api_tokens(api_name)
    joined_a = "".join(at)
    if not vt or not joined_a:
        return 0.0
    w_sum = hit = 0.0
    for t in vt:
        w = 0.5 if t in PREFIXES else 1.5 if t.isdigit() else 1.0
        if t.isdigit():
            found = t in at
        elif len(t) <= 2:
            found = t in at or any(a.startswith(t) for a in at)
        else:
            found = t in joined_a
        w_sum += w
        hit += w * found
    if hit == 0 and len(joined_v) >= 5 and joined_v in joined_a:
        hit = w_sum
    score = hit / w_sum
    vset = set(vt)
    for a in at:
        if (a.isdigit() and len(a) == 1 and a not in vset and a != "1") or (
                a in VARIANT and a not in vset):
            score -= 0.4
    return max(score, 0.0)


# --- league selection for the season menu ------------------------------------------------------

def league_filter(p: Parsed) -> list[re.Pattern[str]]:
    """Patterns on '<leagueorg> | <league or cup name>' entries of the season menu."""
    lg = {t.lower() for t in p.league}
    sex = "Frauen" if p.women else "M(ä|a)nner"
    pats: list[str] = []
    if lg & {"nla", "qhl", "finalissima", "playoffhf", "playofff1", "playofff2"} and not p.women:
        pats.append(r"^Quickline Handball League|NLA")
    if "nlb" in lg:
        pats.append(r"NLB")
    if lg & {"spl1", "spl2", "final4"} and p.women:
        pats.append(r"^SWISS Premium League")
    if "1liga" in lg:
        pats.append(rf"\| {sex} 1\. Liga")
    if "2liga" in lg:
        pats.append(rf"\| {sex} 2\. Liga")
    if lg & {"cup", "cupfinal"}:
        pats.append(rf"Handball Cup {sex}|Schweizer Cup {sex}")
    if "supercup" in lg:
        pats.append(rf"SuperCup {sex}")
    for t in lg:
        m = re.fullmatch(r"u(\d\d)([eip])", t)
        if m:
            level = {"e": "Elite", "i": "Inter", "p": "Promotion"}[m.group(2)]
            pats.append(rf"Junior\w* U{m.group(1)} {level}")
    return [re.compile(x) for x in pats]


def stage_filter(p: Parsed) -> re.Pattern[str] | None:
    """Round named in the video name, matched on 'groupShortName menu label' of a game."""
    lg = {t.lower() for t in p.league}
    if "supercup" in lg:
        return re.compile(r"SuperCup", re.I)
    if "cupfinal" in lg or (lg & {"cup"} and "final" in lg):
        return re.compile(r"Cup.* - Final\b")
    if "final4" in lg:
        return re.compile(
            r"F4|Final ?(4|Four)|-PHF|-PF\b|Playoff-(Halb)?final|Cup.* - (1/2-)?Final")
    if lg & {"final", "playofffinal", "playofff1", "playofff2", "finalissima"}:
        return re.compile(r"-PF\b|Playoff-Final|Cup.* - Final\b|Final ?(4|Four)")
    if "playoffhf" in lg:
        return re.compile(r"-PHF|Playoff-Halbfinal")
    if "cup" in lg:
        return re.compile(r"Cup")
    return None


def stage_text(g: dict[str, Any]) -> str:
    return " ".join(str(g.get(k) or "") for k in ("leagueShortName", "groupShortName", "groupName",
                                                  "_group"))


# --- data sources --------------------------------------------------------------------------------

class Official:
    def __init__(self, api: Api) -> None:
        self.api = api
        self.seasons = api.query(Q_SEASONS, max_age_h=24 * 7)["season"]
        self.current = max(s["objectId"] for s in self.seasons if s["isActual"])
        self.clubs: dict[int, set[str]] = {}
        for c in api.query(Q_CLUBS, max_age_h=24 * 7)["club"]:
            self.clubs.setdefault(c["clubId"], set()).add(c["name"])
        self._load_cached_clubs()

    def _age(self, season: int) -> float | None:
        return 12.0 if season >= self.current else None

    def _load_cached_clubs(self) -> None:
        for f in self.api.cache.glob("getGames_*.json"):
            try:
                self._add_clubs(json.loads(f.read_text())["data"].get("games") or [])
            except (OSError, ValueError, KeyError):
                continue

    def _add_clubs(self, games: list[dict[str, Any]]) -> None:
        for g in games:
            for side in ("home", "away"):
                cid, nm = g.get(f"{side}TeamClubId"), g.get(f"{side}TeamName")
                if cid and nm:
                    self.clubs.setdefault(int(cid), set()).add(nm.strip())

    def seasons_for(self, lo: date, hi: date) -> list[int]:
        out = []
        for s in self.seasons:
            a = datetime.fromisoformat(s["dateFrom"]).date()
            b = datetime.fromisoformat(s["dateTo"]).date()
            if a <= hi and lo <= b:
                out.append(int(s["objectId"]))
        return sorted(out)

    def menu_groups(self, season: int, pats: list[re.Pattern[str]]) -> list[tuple[int, str]]:
        """(group or cup id, menu label) of the season's menu entries matching a pattern; the
        label is 'leagueorg | league or cup organisation | group or cup'."""
        menu = self.api.query(Q_MENU, {"seasonId": season}, self._age(season))["menuItem"] or []
        out: list[tuple[int, str]] = []
        for org in menu:
            for lg in org.get("menuItem") or []:
                for gr in lg.get("menuItem") or []:
                    label = f"{org['name']} | {lg['name']} | {gr['name']}"
                    if gr["objectType"] in ("group", "cup") and any(p.search(label) for p in pats):
                        out.append((int(gr["objectId"]), " ".join(label.split())))
        return out

    def group_games(self, group: int, season: int, label: str = "") -> list[dict[str, Any]]:
        g = self.api.query(Q_GROUP_GAMES, {"groupId": group}, self._age(season))["games"] or []
        self._add_clubs(g)
        return [dict(x, _group=label) for x in g]

    def club_games(self, club: int, season: int) -> list[dict[str, Any]]:
        g = self.api.query(Q_CLUB_GAMES, {"clubId": club, "seasonId": season},
                           self._age(season))["games"] or []
        self._add_clubs(g)
        return g

    def nati_games(self, women: bool) -> list[dict[str, Any]]:
        res = self.api.query(Q_NATI, {"teamId": NATI_TEAM["F" if women else "M"]}, 24 * 7)
        nat = res.get("natiGames") or []
        return nat[0]["games"] if nat else []

    def clubs_like(self, team: str, limit: int = 3) -> list[int]:
        scored = []
        for cid, names in self.clubs.items():
            s = max(team_score(team, n) for n in names)
            if s >= 0.6:
                scored.append((s, cid))
        scored.sort(reverse=True)
        return [c for s, c in scored[:limit] if s >= scored[0][0] - 0.25]

    def game(self, gid: int) -> dict[str, Any] | None:
        res = self.api.query(Q_GAME, {"gameId": gid, "isLive": False}, None)
        g = res.get("game") or []
        return g[0] if g else None

    def log_players(self, gid: int, played: date | None) -> tuple[list[Any], list[Any]]:
        age = 12.0 if played is None or (date.today() - played).days < 14 else None
        v = {"gameId": gid, "isLive": False}
        log = self.api.query(Q_LOG, v, age).get("gameLog") or []
        players = self.api.query(Q_PLAYERS, v, age).get("gamePlayerStats") or []
        return log, players


# --- video info (descriptions) -------------------------------------------------------------------

class Infos:
    """yt-dlp info JSONs: ingest batch folders, a local copy cache and the Drive folder."""

    def __init__(self, ingest: Path, cache: Path, drive: str | None, refresh: bool) -> None:
        self.dir = cache / "info"
        self.dir.mkdir(parents=True, exist_ok=True)
        for f in ingest.glob("batch_*/*.info.json"):
            dst = self.dir / f.name
            if not dst.exists() or dst.stat().st_size != f.stat().st_size:
                dst.write_bytes(f.read_bytes())
        self.drive_ids: dict[str, str] = {}
        if drive:
            self.drive_ids = self._drive_listing(drive, cache / "drive_listing.json", refresh)

    @staticmethod
    def _drive_listing(folder: str, path: Path, refresh: bool) -> dict[str, str]:
        if path.exists() and not refresh and time.time() - path.stat().st_mtime < 1800:
            return dict(json.loads(path.read_text()))
        try:
            import gdown
        except ImportError:
            print("gdown not installed: info JSONs only from the ingest folders", file=sys.stderr)
            return dict(json.loads(path.read_text())) if path.exists() else {}
        try:
            files = gdown.download_folder(folder, skip_download=True, quiet=True) or []
        except Exception as exc:  # noqa: BLE001 - gdown raises many types; listing is optional
            print(f"Drive listing failed: {exc}", file=sys.stderr)
            return dict(json.loads(path.read_text())) if path.exists() else {}
        ids = {Path(f.path).name[: -len(".info.json")]: f.id for f in files
               if f.path.endswith(".info.json")}
        path.write_text(json.dumps(ids, indent=1))
        return ids

    def get(self, name: str) -> dict[str, Any] | None:
        f = self.dir / f"{name}.info.json"
        if not f.exists() and name in self.drive_ids:
            try:
                import gdown

                gdown.download(id=self.drive_ids[name], output=str(f), quiet=True)
            except Exception as exc:  # noqa: BLE001
                print(f"{name}: info download failed: {exc}", file=sys.stderr)
        if not f.exists():
            return None
        try:
            return dict(json.loads(f.read_text()))
        except ValueError:
            f.unlink(missing_ok=True)
            return None


def info_dates(info: dict[str, Any] | None) -> list[date]:
    out = []
    for k in ("release_date", "upload_date"):
        v = (info or {}).get(k)
        if v and re.fullmatch(r"\d{8}", str(v)):
            out.append(datetime.strptime(str(v), "%Y%m%d").date())
    for k in ("release_timestamp", "timestamp"):
        v = (info or {}).get(k)
        if isinstance(v, (int, float)):
            out.append(datetime.fromtimestamp(v).date())
    return sorted(set(out))


# --- matching ------------------------------------------------------------------------------------

@dataclass
class Match:
    game: dict[str, Any] | None
    method: str = ""
    reason: str = ""
    score: float = 0.0
    candidates: list[dict[str, Any]] = field(default_factory=list)
    pool: list[tuple[float, dict[str, Any]]] = field(default_factory=list)  # ambiguous ones


def gdate(g: dict[str, Any]) -> date:
    return datetime.fromisoformat(g["gameDateTime"]).date()


def gid_of(g: dict[str, Any]) -> int:
    return int(g.get("gameId") or g["objectId"])


def score_game(p: Parsed, g: dict[str, Any]) -> float:
    h, a = g.get("homeTeamName") or "", g.get("awayTeamName") or ""
    if len(p.teams) >= 2:
        t1, t2 = p.teams[-2], p.teams[-1]
        straight = (team_score(t1, h), team_score(t2, a))
        swapped = (team_score(t1, a), team_score(t2, h))
        best = max(min(straight), min(swapped) - 0.05)
        return best if best > 0 else 0.0
    if len(p.teams) == 1:
        return 0.85 * max(team_score(p.teams[0], h), team_score(p.teams[0], a))
    return 0.0


def in_window(p: Parsed, g: dict[str, Any]) -> bool:
    if p.date_from is None or p.date_to is None:
        return True
    d = gdate(g)
    pad = DAY if p.date_kind == "exact" else timedelta(days=0)
    return p.date_from - pad <= d <= min(p.date_to + pad, date.today())


MEN_LEAGUE = re.compile(r"^(M\d|MU|MNL|NLA|NLB|QHL)|\b(Cup|SuperCup) M\b")
WOMEN_LEAGUE = re.compile(r"^(F\d|FU|FNL|SPL)|\b(Cup|SuperCup) F\b")


def league_compatible(p: Parsed, g: dict[str, Any]) -> bool:
    """Rules out games of the other sex or of youth teams when the name says otherwise."""
    ls = g.get("leagueShortName") or ""
    if p.league and re.search(r"U\d\d", ls) and not any(
            re.fullmatch(r"U\d\d\w?", t) for t in p.league):
        return False
    if p.women:
        return not MEN_LEAGUE.search(ls)
    if p.league and "Nati" not in p.league:
        return not WOMEN_LEAGUE.search(ls)
    return True


def candidates(p: Parsed, off: Official) -> list[dict[str, Any]]:
    if p.date_from is None or p.date_to is None:
        lo, hi = date(2012, 6, 1), date.today()
    else:
        lo, hi = p.date_from - DAY, p.date_to + DAY
    seasons = off.seasons_for(lo, hi)
    games: dict[int, dict[str, Any]] = {}

    def add(gs: list[dict[str, Any]]) -> None:
        for g in gs:
            if g.get("gameDateTime") and in_window(p, g) and league_compatible(p, g):
                games.setdefault(gid_of(g), g)

    if "Nati" in p.league:
        add(off.nati_games(p.women))
        return list(games.values())
    pats = league_filter(p)
    if pats:
        for s in seasons:
            for grp, label in off.menu_groups(s, pats):
                add(off.group_games(grp, s, label))
    if not any(score_game(p, g) >= 0.5 for g in games.values()):
        clubs: list[int] = []
        for t in p.teams[-2:]:
            clubs += [c for c in off.clubs_like(t) if c not in clubs]
        for c in clubs[:4]:
            for s in seasons:
                add(off.club_games(c, s))
    return list(games.values())


def describe(g: dict[str, Any]) -> dict[str, Any]:
    return {"game_id": gid_of(g), "date": g["gameDateTime"][:10], "home": g["homeTeamName"].strip(),
            "away": g["awayTeamName"].strip(), "league": g.get("leagueShortName")}


def find_match(p: Parsed, off: Official, info: dict[str, Any] | None) -> Match:
    text = " ".join(str((info or {}).get(k) or "") for k in ("description", "title"))
    m = LINK.search(text)
    if m:
        gid = int(m.group(1))
        g = off.game(gid)
        if g:
            return Match(g, "description link", score=1.0)
    if p.country != "CH":
        return Match(None, reason="no handball.ch")
    if not p.teams:
        return Match(None, reason="no team names in the video name")
    cands = candidates(p, off)
    scored = sorted(((score_game(p, g), g) for g in cands), key=lambda x: -x[0])
    single = len(p.teams) < 2
    need = 0.6 if single else 0.5
    good = [(s, g) for s, g in scored if s >= need]
    if not good:
        near = [dict(describe(g), score=round(s, 2)) for s, g in scored[:3] if s > 0.2]
        why = "no game of these teams in the date window" if p.date_kind != "none" else \
            "no date in the name and no game found"
        if p.date_kind == "exact" and not single:
            # one of the two teams played that day: likely a wrong opponent or date in the name
            one = [g for g in cands if gdate(g) == p.day and max(
                team_score(t, g.get(f"{side}TeamName") or "")
                for t in p.teams[-2:] for side in ("home", "away")) >= 0.9]
            if one:
                near = [describe(g) for g in one[:3]]
                why += "; but " + ", ".join(
                    f"{d['home']} - {d['away']} ({d['date']})" for d in near)
        if not cands:
            why = "no candidate games (league/club not found in handball.ch for that period)"
        return Match(None, reason=why, candidates=near)
    st = stage_filter(p)
    if st:
        staged = [(s, g) for s, g in good if st.search(stage_text(g))]
        good = staged or good
    top = good[0][0]
    best = [(s, g) for s, g in good if s >= top - 0.03]
    series = next((m for t in p.league if (m := re.fullmatch(r"PlayoffF(\d)|Finalissima", t))),
                  None)
    if series and len(best) > 1 and p.date_kind != "exact" and st:
        # game n of a final series (or the last one); both orientations count
        fin = sorted((x for x in good if st.search(stage_text(x[1]))),
                     key=lambda x: str(x[1]["gameDateTime"]))
        n = int(series.group(1)) if series.group(1) else len(fin)
        if 0 < n <= len(fin):
            s_n, g_n = fin[n - 1]
            return Match(g_n, f"search + final game {n} of {len(fin)}", score=s_n)
    if len(best) > 1 and p.day is not None and p.date_kind in ("exact", "approx"):
        dmin = min(abs((gdate(g) - p.day).days) for _, g in best)
        best = [(s, g) for s, g in best if abs((gdate(g) - p.day).days) == dmin]
    if len(best) > 1:
        hints = info_dates(info)
        if hints:
            # streams are published on game day; uploads follow within days
            close = [(s, g) for s, g in best
                     if any(-1 <= (h - gdate(g)).days <= 3 for h in hints)]
            if len(close) == 1:
                return Match(close[0][1], "search + stream/upload date", score=close[0][0])
        best_s = [x for x in best if x[0] >= top - 1e-6]
        if len(best_s) == 1 and p.date_kind == "exact":
            return Match(best_s[0][1], "search", score=top)
        return Match(None, reason=f"ambiguous: {len(best)} candidate games",
                     candidates=[dict(describe(g), score=round(s, 2)) for s, g in best[:8]],
                     pool=best)
    s, g = best[0]
    if single and p.date_kind not in ("exact", "month"):
        return Match(None, reason="one team only and no exact date",
                     candidates=[dict(describe(g), score=round(s, 2))])
    return Match(g, "search", score=s)


# --- catalog -------------------------------------------------------------------------------------

def load_names(csv_path: Path, ingest: Path) -> tuple[list[str], dict[str, str], dict[str, Any]]:
    names: list[str] = []
    urls: dict[str, str] = {}
    with csv_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter=";"):
            n = (row.get("name") or "").strip()
            if n and n not in urls:
                names.append(n)
                urls[n] = (row.get("url") or "").strip()
    state: dict[str, Any] = {}
    sp = ingest / "state.json"
    if sp.exists():
        state = dict(json.loads(sp.read_text()).get("games", {}))
    for idx in sorted((ingest / "uploaded").glob("*.index.json")):
        for n, g in json.loads(idx.read_text()).items():
            state.setdefault(n, g)
    for n in sorted(state):
        if n not in urls:
            names.append(n)
            urls[n] = ""
    return names, urls, state


def video_entry(st: dict[str, Any] | None) -> dict[str, Any] | None:
    if not st:
        return None
    if "error" in st:
        return {"error": st["error"]}
    b = re.fullmatch(r"batch_(\d+)", st.get("batch", ""))
    return {
        "width": st.get("width"), "height": st.get("height"), "fps": st.get("fps"),
        "duration_s": st.get("duration_s"), "codec": st.get("codec"),
        "segments": len(st.get("segments") or []),
        "kaggle_dataset": f"handball-segs-b{int(b.group(1)):02d}" if b else None,
    }


def resolve_claims(todo: list[tuple[str, Parsed, dict[str, Any] | None, Match]]) -> None:
    """Approximate dates: candidates already matched by a video with an exact date are most
    likely other recordings, so an ambiguous name with one unclaimed candidate gets that one; a
    unique candidate another video also claims is dropped (no evidence which video it is)."""
    claimed: dict[int, list[str]] = {}
    for n, p, _, mt in todo:
        if mt.game and p.date_kind == "exact":
            claimed.setdefault(gid_of(mt.game), []).append(n)
    for i, (n, p, info, mt) in enumerate(todo):
        if mt.game is None and mt.pool and p.date_kind != "exact":
            free = [(s, g) for s, g in mt.pool if gid_of(g) not in claimed]
            if len(free) == 1:
                todo[i] = (n, p, info, Match(
                    free[0][1], "search + approximate date (other candidates have dated videos)",
                    score=free[0][0], candidates=mt.candidates))
    users: dict[int, list[str]] = {}
    for n, p, _, mt in todo:
        if mt.game and not p.tags:
            users.setdefault(gid_of(mt.game), []).append(n)
    for i, (n, p, info, mt) in enumerate(todo):
        if mt.game and p.date_kind != "exact" and len(users.get(gid_of(mt.game), [])) > 1:
            gid = gid_of(mt.game)
            others = ", ".join(x for x in users[gid] if x != n)
            todo[i] = (n, p, info, Match(None, reason=f"approximate date: game {gid} also "
                                         f"matches {others}", candidates=[describe(mt.game)]))


def catalog_entry(n: str, p: Parsed, info: dict[str, Any] | None, mt: Match, off: Official,
                  out: Path) -> dict[str, Any]:
    """Catalog entry; writes (or removes) out/<name>.json with the official log and players."""
    e: dict[str, Any] = {
        "name": n, "url": (info or {}).get("webpage_url"),
        "country": p.country, "league": "_".join(p.league) or None,
        "teams": p.teams, "date": p.date_text or None, "date_kind": p.date_kind,
        "info_json": info is not None, "game_id": None,
    }
    if p.tags:
        e["part"] = "_".join(p.tags)
    off_file = out / f"{n}.json"
    if mt.game is None:
        e["reason"] = mt.reason
        if mt.candidates:
            e["candidates"] = mt.candidates
        off_file.unlink(missing_ok=True)
        return e
    g = mt.game
    gid = gid_of(g)
    log, players = off.log_players(gid, gdate(g))
    rec = {
        "source": GAME_URL.format(gid), "game_id": gid,
        "home": g["homeTeamName"].strip(), "away": g["awayTeamName"].strip(),
        "date": g["gameDateTime"],
        "result": f"{g.get('homeTeamScore')}:{g.get('awayTeamScore')}",
        "league": g.get("leagueShortName"), "group": g.get("groupShortName"),
        "log": sorted(log, key=lambda x: x.get("timeInt") or 0), "players": players,
    }
    off_file.write_text(json.dumps(rec, ensure_ascii=False, indent=1))
    repo = ROOT.parent.parent
    e.update({
        "game_id": gid, "match": mt.method, "match_score": round(mt.score, 2),
        "official": {k: rec[k] for k in ("home", "away", "date", "result", "league")},
        "has_log": bool(log), "log_entries": len(log),
        "log_goals": sum(1 for x in log if x.get("actionGroup") == 1),
        "players": len(players),
        "file": str(off_file.relative_to(repo) if off_file.is_relative_to(repo) else off_file),
    })
    if mt.candidates:
        e["candidates"] = mt.candidates
    return e


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--csv", type=Path, default=ROOT / "videos.csv")
    ap.add_argument("--ingest", type=Path, default=SCRATCH / "ingest")
    ap.add_argument("--cache", type=Path, default=SCRATCH / "official_cache")
    ap.add_argument("--out", type=Path, default=ROOT / "official")
    ap.add_argument("--catalog", type=Path, default=ROOT / "catalog.json")
    ap.add_argument("--drive", default=os.environ.get("HANDBALL_DRIVE_FOLDER"),
                    help="Drive folder with the info JSONs (default: the URL in <ingest>/run.sh)")
    ap.add_argument("--refresh-drive", action="store_true", help="re-list the Drive folder now")
    ap.add_argument("--only", help="process only names containing this text (catalog keeps others)")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()

    if not a.drive and (a.ingest / "run.sh").exists():
        run_sh = (a.ingest / "run.sh").read_text()
        m = re.search(r"https://drive\.google\.com/drive/folders/[\w-]+", run_sh)
        a.drive = m.group(0) if m else None
    names, urls, state = load_names(a.csv, a.ingest)
    old: dict[str, Any] = {}
    if a.catalog.exists():
        old = {e["name"]: e for e in json.loads(a.catalog.read_text()).get("games", [])}
    api = Api(a.cache, a.verbose)
    off = Official(api)
    infos = Infos(a.ingest, a.cache, a.drive, a.refresh_drive)
    a.out.mkdir(parents=True, exist_ok=True)

    done: dict[str, dict[str, Any]] = {}
    todo: list[tuple[str, Parsed, dict[str, Any] | None, Match]] = []
    for n in names:
        p = parse_name(n)
        if a.only and a.only not in n:
            if n in old:
                old[n]["video"] = video_entry(state.get(n)) or old[n].get("video")
                done[n] = old[n]
            continue
        info = infos.get(n)
        try:
            mt = find_match(p, off, info)
        except (RuntimeError, urllib.error.URLError, TimeoutError) as exc:
            mt = Match(None, reason=f"api error: {exc}"[:200])
        todo.append((n, p, info, mt))
    resolve_claims(todo)
    for n, p, info, mt in todo:
        e = catalog_entry(n, p, info, mt, off, a.out)
        e["url"] = urls.get(n) or e["url"]
        e["video"] = video_entry(state.get(n))
        done[n] = e
        tag = f"{e['game_id']} ({e.get('log_goals', 0)} goals in log)" if e["game_id"] else \
            f"- {e['reason']}"
        print(f"{n}: {tag}", flush=True)

    entries = [done[n] for n in names if n in done]
    ch = [e for e in entries if e["country"] == "CH"]
    summary = {
        "games": len(entries), "swiss": len(ch),
        "swiss_matched": sum(1 for e in ch if e["game_id"]),
        "with_log": sum(1 for e in entries if e.get("has_log")),
        "in_ingest": sum(1 for e in entries if e.get("video")),
    }
    a.catalog.write_text(json.dumps({
        "generated": datetime.now().isoformat(timespec="seconds"),
        "source": "ml/data/match_official.py", "summary": summary, "games": entries,
    }, ensure_ascii=False, indent=1))
    print(json.dumps(summary), f"api requests: {api.requests}", flush=True)


if __name__ == "__main__":
    main()
