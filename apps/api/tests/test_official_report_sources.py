"""Official match reports from nuLiga (German associations on nuLiga, Austria) and the HLA
(Sportradar) imported into a match.

The network is never used: the fetchers are replaced by pages recorded from the real sources
(tests/fixtures/official_report, player and official names replaced by fake ones), and the
download itself runs against an httpx mock transport."""

from __future__ import annotations

import re
import uuid
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest

from handball_api.core.errors import ProblemError
from handball_api.services import official_report as service

from .conftest import Api, setup_club
from .test_matches import new_match
from .test_official_report import _roster

FIXTURES = Path(__file__).parent / "fixtures" / "official_report"
BHV = "https://bhv-handball.liga.nu/cgi-bin/WebObjects/nuLigaHBDE.woa/wa/"
BHV_URL = BHV + "groupMeetingReport?meeting=8390512&championship=BHV+2026%2F27&group=495716"
OEHB = "https://oehb-handball.liga.nu/cgi-bin/WebObjects/"
OEHB_URL = (
    OEHB + "nuLigaHBAT.woa/wa/groupMeetingReport?meeting=81811&championship=%C3%96HB+25%2F26"
    "&group=216486"
)
OEHB_PDF = OEHB + "nuLigaDokumentHBAT.woa/wa/nuDokument?dokument=meetingReportHB&meeting=92532"
HLA_URL = "https://infographics.sportradar.com/hla/pageSnapshot/pdf/de/70984286"


def page(name: str) -> str:
    return (FIXTURES / name).read_text()


def counts(report: service.OfficialReport) -> Counter[tuple[str, str | None]]:
    return Counter((e.kind, e.team) for e in report.entries)


@pytest.fixture
def recorded(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    calls: list[str] = []
    pages = {
        BHV_URL: "nuliga_bhv_8390512.html",
        OEHB_URL: "nuliga_oehb_81811.html",
        OEHB_PDF: "nuliga_oehb_92532.txt",
    }

    async def nuliga(link: service.ReportLink) -> str:
        calls.append(link.url)
        return page(pages[link.url]) if link.url in pages else "<html><h1>nuLiga</h1></html>"

    async def hla(match_id: int) -> str:
        calls.append(service.HLA_PDF.format(match_id))
        return page("hla_70984286.txt") if match_id == 70984286 else "not a report"

    monkeypatch.setattr(service, "fetch_nuliga", nuliga)
    monkeypatch.setattr(service, "fetch_hla", hla)
    return calls


# ---- links -----------------------------------------------------------------------------------


def test_locate_nuliga_and_hla() -> None:
    link = service.locate(BHV_URL + "&preferredLanguage=English&foo=bar")
    # the page is fetched from the given association's host, rebuilt from the checked parts
    assert link == service.ReportLink("nuliga", 8390512, BHV_URL)
    assert service.detect(OEHB_URL) == ("nuliga", 81811)
    pdf = service.locate(OEHB_PDF + "&preferredLanguage=German&etag=b1b5")
    assert (pdf.provider, pdf.game_id, pdf.url, pdf.pdf) == ("nuliga", 92532, OEHB_PDF, True)
    # the page needs the championship: without it the PDF of the game is read
    bare = service.locate(BHV + "groupMeetingReport?meeting=8390512")
    assert (bare.url, bare.pdf) == (
        "https://bhv-handball.liga.nu/cgi-bin/WebObjects/nuLigaDokumentHBDE.woa/wa/nuDokument"
        "?dokument=meetingReportHB&meeting=8390512",
        True,
    )
    assert service.detect(HLA_URL) == ("hla", 70984286)
    assert service.detect("infographics.sportradar.com/hla/pageSnapshot/pdf/en/70984286") == (
        "hla",
        70984286,
    )
    assert service.locate("70984286", "hla").url == HLA_URL
    for bad, provider in (
        ("8390512", "nuliga"),  # a nuLiga id alone does not say which association
        (BHV + "groupPage?championship=BHV+2026%2F27&group=495716", None),  # no game report
        (BHV + "groupMeetingReport?championship=BHV+2026%2F27", None),
        (OEHB + "nuLigaDokumentHBAT.woa/wa/nuDokument?dokument=groupPage&meeting=1", None),
        (BHV_URL.replace("bhv-handball.liga.nu", "bhv-tennis.liga.nu"), None),
        (BHV_URL.replace("bhv-handball.liga.nu", "bhv-handball.liga.nu.evil.example"), None),
        (BHV_URL.replace("bhv-handball.liga.nu", "bhv-handball.liga.nu@evil.example"), None),
        (BHV_URL.replace("bhv-handball.liga.nu", "bhv-handball.liga.nu:8443"), None),
        ("https://infographics.sportradar.com/hbl/pageSnapshot/pdf/de/1", None),
    ):
        with pytest.raises(ProblemError) as err:
            service.locate(bad, provider)
        assert (err.value.status, err.value.code) == (422, "report-url-unsupported"), bad


# ---- parsing (no database) -------------------------------------------------------------------


def test_parse_nuliga_page_germany() -> None:
    r = service.parse_nuliga(8390512, BHV_URL, page("nuliga_bhv_8390512.html"))
    assert (r.provider, r.game_id, r.source_url) == ("nuliga", 8390512, BHV_URL)
    assert (r.home, r.away, r.final, r.half_time) == (
        "HC Erlangen III",
        "TSV Lohr",
        (39, 28),
        (18, 14),
    )
    assert (r.competition, r.date, len(r.entries)) == ("Regionalliga Männer", "2026-10-24", 78)
    assert counts(r) == {
        ("goal", "home"): 39,
        ("goal", "away"): 25,
        ("penalty_goal", "away"): 3,
        ("penalty_missed", "away"): 2,
        ("penalty_missed", "home"): 1,
        ("suspension", "away"): 3,
        ("timeout", "home"): 2,
        ("timeout", "away"): 3,
    }
    first = r.entries[0]  # 00:37 Heim, 1:0, Tor, 44
    assert (first.clock_s, first.kind, first.team, first.number, first.score) == (
        37,
        "goal",
        "home",
        44,
        (1, 0),
    )
    assert first.name and re.fullmatch(r"\w+, \w+", first.name)
    seven = next(e for e in r.entries if e.kind == "penalty_goal")
    assert (seven.clock_s, seven.team, seven.number, seven.score) == (247, "away", 25, (2, 3))
    susp = next(e for e in r.entries if e.kind == "suspension")
    assert (susp.clock_s, susp.team, susp.number, susp.score) == (1249, "away", 8, None)
    timeouts = [(e.clock_s, e.team) for e in r.entries if e.kind == "timeout"]
    assert timeouts == [
        (1320, "away"),
        (1785, "home"),
        (2724, "home"),
        (2892, "away"),
        (3202, "away"),
    ]
    assert r.entries[-1].score == (39, 28) and r.entries[-1].clock_s == 3590


def test_parse_nuliga_page_austria() -> None:
    """ÖHB (English labels in part, team names with a slash)."""
    r = service.parse_nuliga(81811, OEHB_URL, page("nuliga_oehb_81811.html"))
    assert (r.home, r.away, r.final, r.half_time, r.date) == (
        "HIB Handball Graz",
        "SG TV Gleisdorf/HC Weiz",
        (28, 36),
        (11, 18),
        "2026-05-02",
    )
    goals = Counter(e.team for e in r.entries if e.kind in ("goal", "penalty_goal"))
    assert goals == {"home": 28, "away": 36}
    assert Counter(e.team for e in r.entries if e.kind == "suspension") == {"home": 5, "away": 3}
    # the same 2 minutes from the roster when the log does not list them
    html = re.sub(
        r"<tr>\s*<td>\w+</td>\s*<td>[\d:]+</td>\s*<td>\s*</td>\s*<td>2 Minuten</td>.*?</tr>",
        "",
        page("nuliga_oehb_81811.html"),
        flags=re.DOTALL,
    )
    alone = service.parse_nuliga(81811, OEHB_URL, html)
    assert len(alone.entries) == len(r.entries)
    assert [(e.clock_s, e.team, e.number) for e in alone.entries if e.kind == "suspension"] == [
        (e.clock_s, e.team, e.number) for e in r.entries if e.kind == "suspension"
    ]
    for bad in ("<html><h1>nuLiga</h1></html>", page("dhb_76839.txt")):
        with pytest.raises(ProblemError) as err:
            service.parse_nuliga(1, OEHB_URL, bad)
        assert (err.value.status, err.value.code) == (422, "report-unreadable")


def test_parse_nuliga_pdf() -> None:
    """The PDF (oehb.at links it for every game): two log columns, long names wrap."""
    r = service.parse_nuliga_pdf(92532, OEHB_PDF, page("nuliga_oehb_92532.txt"))
    assert (r.home, r.away, r.final, r.half_time) == (
        "HC LINZ AG",
        "HSG Holding Graz",
        (36, 29),
        (17, 16),
    )
    assert (r.competition, r.date, len(r.entries)) == (
        "MEHRLEBEN HLA MEISTERLIGA",
        "2026-09-26",
        78,
    )
    goals = Counter(e.team for e in r.entries if e.kind in ("goal", "penalty_goal"))
    assert goals == {"home": 36, "away": 29}
    totals = [sum(e.score or ()) for e in r.entries if e.kind in ("goal", "penalty_goal")]
    assert totals == list(range(1, 66))  # every goal once, in order
    timeouts = [(e.clock_s, e.team) for e in r.entries if e.kind == "timeout"]
    assert timeouts == [
        (1224, "away"),
        (1613, "home"),
        (2360, "away"),
        (3003, "away"),
        (3188, "home"),
    ]
    warning = next(e for e in r.entries if e.kind == "warning")
    assert (warning.clock_s, warning.team, warning.number) == (2898, "away", 16)
    # a name wrapped onto the next line, in the right column
    wrapped = next(e for e in r.entries if e.clock_s == 2462)
    assert (wrapped.kind, wrapped.number) == ("penalty_goal", 29)
    assert wrapped.name and re.fullmatch(r"[A-Z]+, [A-Z][a-z]+", wrapped.name)
    last = next(e for e in r.entries if e.clock_s == 3600)
    assert (last.team, last.number, last.score) == ("away", 30, (36, 29))
    with pytest.raises(ProblemError) as err:
        service.parse_nuliga_pdf(1, OEHB_PDF, page("dhb_76839.txt"))
    assert (err.value.status, err.value.code) == (422, "report-unreadable")


def test_parse_hla_report() -> None:
    r = service.parse_hla(70984286, page("hla_70984286.txt"))
    assert (r.home, r.away, r.final, r.half_time) == (
        "JAGS Voslau",
        "HSG Lipizzanerheimat",
        (30, 25),
        (15, 12),
    )
    assert (r.competition, r.date, r.source_url) == ("HLA Meisterliga", "2026-05-02", HLA_URL)
    # no timed goals in this report: the two saved 7-metres, the full name from the roster
    assert [(e.clock_s, e.kind, e.team, e.number) for e in r.entries] == [
        (2641, "penalty_saved", "away", 4),
        (2754, "penalty_saved", "home", 68),
    ]
    assert all(e.name and ", " in e.name for e in r.entries)
    assert r.notes == [service.HLA_NOTE]
    with pytest.raises(ProblemError) as err:
        service.parse_hla(1, page("dhb_76839.txt"))
    assert (err.value.status, err.value.code) == (422, "report-unreadable")


# ---- download: one request, same host only, timeouts ----------------------------------------


@pytest.fixture
def transport(monkeypatch: pytest.MonkeyPatch) -> list[httpx.Request]:
    """httpx answers from a table instead of the network."""
    seen: list[httpx.Request] = []
    pdf_url = OEHB_PDF + "&preferredLanguage=German&etag=1"

    def answer(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        url = str(request.url)
        if url == OEHB_PDF:
            return httpx.Response(
                302, headers={"location": pdf_url.removeprefix("https://oehb-handball.liga.nu")}
            )
        if url == pdf_url:
            return httpx.Response(200, content=b"%PDF-1.4 recorded")
        if "meeting=666" in url:
            return httpx.Response(302, headers={"location": "https://evil.example/x.pdf"})
        if "meeting=404" in url:
            return httpx.Response(404)
        return httpx.Response(200, content=page("nuliga_bhv_8390512.html").encode())

    real = httpx.AsyncClient

    def client(**kwargs: Any) -> httpx.AsyncClient:
        assert isinstance(kwargs["timeout"], httpx.Timeout) and not kwargs["follow_redirects"]
        return real(**kwargs, transport=httpx.MockTransport(answer))

    async def pdf_text(pdf: bytes) -> str:
        return pdf.decode()

    monkeypatch.setattr(httpx, "AsyncClient", client)
    monkeypatch.setattr(service, "_pdf_text", pdf_text)
    return seen


async def test_download_follows_redirects_on_the_same_host_only(
    transport: list[httpx.Request],
) -> None:
    assert await service.fetch_nuliga(service.locate(OEHB_PDF)) == "%PDF-1.4 recorded"
    assert [r.url.host for r in transport] == ["oehb-handball.liga.nu"] * 2
    html = await service.fetch_nuliga(service.locate(BHV_URL))
    assert "Spielverlauf" in html and str(transport[-1].url) == BHV_URL
    for meeting, status, code in ((666, 502, "report-unavailable"), (404, 404, "report-not-found")):
        with pytest.raises(ProblemError) as err:
            await service.fetch_nuliga(service.locate(OEHB_PDF.replace("92532", str(meeting))))
        assert (err.value.status, err.value.code) == (status, code)
    assert all(r.url.host == "oehb-handball.liga.nu" for r in transport[3:])
    with pytest.raises(ProblemError) as err:  # HTML where the PDF should be
        await service.fetch_hla(1)
    assert (err.value.status, err.value.code) == (422, "report-unreadable")


# ---- import into a match ---------------------------------------------------------------------


@pytest.mark.usefixtures("clean_db")
async def test_import_nuliga_report(
    make_api: Callable[[], Api], recorded: list[str], owner_conn: Any
) -> None:
    """We are TSV Lohr (away). The unverified club then sees only the numbers of the other team."""
    api = make_api()
    ids = await setup_club(api)
    players = await _roster(api, ids, {5: "Gerd", 24: "Lino", 25: "Paddy"})
    m = await new_match(api, ids, opponent_name="HC Erlangen III", is_home=False)
    org = ids["org"]
    url = f"/v1/orgs/{org}/matches/{m['id']}/official-report"
    r = await api.post(url, json={"url": BHV_URL})
    assert r.status_code == 200, r.text
    res = r.json()
    assert (res["provider"], res["game_id"], res["source_url"], res["final"]) == (
        "nuliga",
        8390512,
        BHV_URL,
        [39, 28],
    )
    assert (res["created"], res["replaced"], res["skipped"]) == (78, 0, 0)
    assert res["warnings"] == ["numbers not in the roster: [3, 6, 7, 8, 23, 28]"]
    ev_url = f"/v1/orgs/{org}/matches/{m['id']}/events"
    events = (await api.get(ev_url)).json()
    goals = [e for e in events if e["type"] == "shot" and e["outcome"] == "goal"]
    assert Counter(e["side"] for e in goals) == {"own": 28, "opponent": 39}
    penalty = next(e for e in goals if e["shot_type"] == "penalty")
    assert (penalty["side"], penalty["clock_s"], penalty["player_id"]) == ("own", 247, players[25])
    assert penalty["attributes"]["score"] == [3, 2]  # own first
    second_half = next(e for e in goals if e["clock_s"] == 1871)  # 31:11, Lohr
    assert (second_half["period"], second_half["player_id"]) == (2, players[5])
    misses = [e for e in events if e["type"] == "shot" and e["outcome"] == "miss"]
    assert Counter(e["side"] for e in misses) == {"own": 2, "opponent": 1}
    assert Counter(e["side"] for e in events if e["type"] == "timeout") == {
        "own": 3,
        "opponent": 2,
    }
    assert {e["side"] for e in events if e["type"] == "suspension_2min"} == {"own"}
    assert all(e["attributes"].get("name") for e in goals)
    match = (await api.get(f"/v1/orgs/{org}/matches/{m['id']}")).json()
    assert (match["score_own"], match["score_opponent"]) == (28, 39)
    assert (match["halftime_own"], match["halftime_opponent"]) == (14, 18)
    assert match["report_extra"]["official_report"] == {
        "provider": "nuliga",
        "game_id": 8390512,
        "url": BHV_URL,
        "home": "HC Erlangen III",
        "away": "TSV Lohr",
    }
    comparison = (await api.get(f"{url}/comparison")).json()
    assert (comparison["provider"], comparison["counts"]["official"]) == ("nuliga", 67)

    # a club not verified yet: the other team's players by number only
    await owner_conn.execute(
        "UPDATE organizations SET verification = 'unverified' WHERE id = $1", uuid.UUID(org)
    )
    again = (await api.post(url, json={"url": BHV_URL})).json()
    assert (again["created"], again["replaced"]) == (78, 78)
    events = (await api.get(ev_url)).json()
    theirs = [e for e in events if e["side"] == "opponent" and e["number"] is not None]
    assert theirs and all("name" not in e["attributes"] for e in theirs)
    ours = [e for e in events if e["side"] == "own" and e["number"] is not None]
    assert ours and all(e["attributes"].get("name") for e in ours)
    assert recorded == [BHV_URL, BHV_URL]


@pytest.mark.usefixtures("clean_db")
async def test_import_nuliga_pdf_and_hla_report(
    make_api: Callable[[], Api], recorded: list[str]
) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    m = await new_match(api, ids, opponent_name="HSG Holding Graz")  # we are HC Linz (home)
    url = f"/v1/orgs/{org}/matches/{m['id']}/official-report"
    res = (await api.post(url, json={"url": OEHB_PDF})).json()
    assert (res["provider"], res["game_id"], res["created"], res["final"]) == (
        "nuliga",
        92532,
        78,
        [36, 29],
    )
    events = (await api.get(f"/v1/orgs/{org}/matches/{m['id']}/events")).json()
    assert next(e for e in events if e["type"] == "yellow_card")["side"] == "opponent"
    # the last goal at 60:00 is in the second half
    last = next(e for e in events if e["clock_s"] == 3600)
    assert (last["period"], last["side"]) == (2, "opponent")

    # HLA: the result and the missed 7-metres, with a note that the log is missing
    hla = await new_match(api, ids, opponent_name="HSG Lipizzanerheimat")  # we: Vöslau, home
    hla_url = f"/v1/orgs/{org}/matches/{hla['id']}/official-report"
    r = await api.post(hla_url, json={"url": "70984286", "provider": "hla"})
    assert r.status_code == 200, r.text
    res = r.json()
    assert (res["provider"], res["source_url"], res["created"], res["final"]) == (
        "hla",
        HLA_URL,
        2,
        [30, 25],
    )
    assert res["warnings"][0] == service.HLA_NOTE
    saves = (await api.get(f"/v1/orgs/{org}/matches/{hla['id']}/events")).json()
    assert sorted((e["side"], e["outcome"], e["shot_type"]) for e in saves) == [
        ("opponent", "save", "penalty"),
        ("own", "save", "penalty"),
    ]
    match = (await api.get(f"/v1/orgs/{org}/matches/{hla['id']}")).json()
    assert (match["score_own"], match["halftime_own"]) == (30, 15)

    # nothing to read: not fetched or not a report
    for body, status, code in (
        ({"url": "8390512", "provider": "nuliga"}, 422, "validation-error"),
        ({"url": BHV + "groupMeetingReport?meeting=1&championship=BHV"}, 422, "report-unreadable"),
        (
            {"url": "https://infographics.sportradar.com/hla/pageSnapshot/pdf/de/1"},
            422,
            "report-unreadable",
        ),
    ):
        r = await api.post(url, json=body)
        assert r.status_code == status and r.json()["type"].endswith(code), (body, r.text)
    assert recorded[-2:] == [
        BHV + "groupMeetingReport?meeting=1&championship=BHV",
        service.HLA_PDF.format(1),
    ]
