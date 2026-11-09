"""Official match reports (handball.ch match centre, DHB press report) imported into a match.

The network is never used: the fetchers are replaced by data recorded from the real sources
(tests/fixtures/official_report, the games of ml/eval/official)."""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from handball_api.core.errors import ProblemError
from handball_api.services import official_report as service

from .conftest import Api, setup_club
from .test_matches import new_match

FIXTURES = Path(__file__).parent / "fixtures" / "official_report"
CH_URL = "https://www.handball.ch/de/matchcenter/spiele/484345"
DHB_URL = "https://dhbdata.fmp.sportradar.com/match/76839/pressReport.pdf"


def ch_data() -> dict[str, Any]:
    data: dict[str, Any] = json.loads((FIXTURES / "handball_ch_484345.json").read_text())
    return data


def dhb_text() -> str:
    return (FIXTURES / "dhb_76839.txt").read_text()


@pytest.fixture
def recorded(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, int]]:
    calls: list[tuple[str, int]] = []

    async def ch(game_id: int) -> dict[str, Any]:
        calls.append(("handball_ch", game_id))
        return ch_data() if game_id == 484345 else {"game": [], "gameLog": []}

    async def dhb(match_id: int) -> str:
        calls.append(("dhb", match_id))
        return dhb_text() if match_id == 76839 else "%PDF garbage that is no press report"

    monkeypatch.setattr(service, "fetch_handball_ch", ch)
    monkeypatch.setattr(service, "fetch_dhb", dhb)
    return calls


# ---- parsing (no database) -------------------------------------------------------------------


def test_detect_source() -> None:
    assert service.detect(CH_URL) == ("handball_ch", 484345)
    assert service.detect("www.handball.ch/fr/matchcenter/matchs/484345?x=1") == (
        "handball_ch",
        484345,
    )
    assert service.detect(DHB_URL) == ("dhb", 76839)
    assert service.detect(" 76839 ", "dhb") == ("dhb", 76839)
    for bad, provider in (
        ("76839", None),
        ("https://www.handball.net/spiele/123", None),
        ("https://evil.example/matchcenter/spiele/1", None),
        ("https://www.handball.ch/de/news", None),
    ):
        with pytest.raises(ProblemError) as err:
            service.detect(bad, provider)
        assert (err.value.status, err.value.code) == (422, "report-url-unsupported")


def test_parse_handball_ch_resolves_sides_and_keepers() -> None:
    r = service.parse_handball_ch(484345, ch_data())
    assert (r.home, r.away, r.final, r.half_time) == (
        "HSG Leimental",
        "HC Arbon",
        (25, 28),
        (12, 19),
    )
    assert r.date == "2024-09-21" and r.source_url == CH_URL
    first = r.entries[0]  # 00:42 save: the home keeper #1 stopped #6 of Arbon
    assert (first.kind, first.team, first.number, first.goalkeeper_number) == (
        "shot_saved",
        "away",
        6,
        1,
    )
    timeout = next(e for e in r.entries if e.kind == "timeout")
    assert (timeout.clock_s, timeout.team, timeout.number) == (761, "home", None)
    goal = next(e for e in r.entries if e.kind == "goal")
    assert (goal.clock_s, goal.team, goal.number, goal.name, goal.score) == (
        93,
        "home",
        32,
        "PROBSTER Seraina",
        (1, 0),
    )
    assert {e.kind for e in r.entries} >= {"penalty_goal", "suspension", "turnover", "shot_missed"}
    with pytest.raises(ProblemError) as err:
        service.parse_handball_ch(1, {"game": [], "gameLog": []})
    assert (err.value.status, err.value.code) == (404, "report-not-found")


def test_parse_dhb_press_report() -> None:
    r = service.parse_dhb(76839, dhb_text())
    assert (r.home, r.away, r.final, r.half_time) == (
        "SC Magdeburg II",
        "HC Empor Rostock",
        (26, 26),
        (13, 13),
    )
    assert (r.competition, r.date, len(r.entries)) == ("3. Liga Männer", "2024-02-04", 65)
    goals = [e for e in r.entries if e.kind in ("goal", "penalty_goal")]
    assert len(goals) == 52 and goals[-1].score == (26, 26)
    timeouts = [(e.clock_s, e.team) for e in r.entries if e.kind == "timeout"]
    assert timeouts[:2] == [(949, "away"), (1368, "home")]
    susp = next(e for e in r.entries if e.kind == "suspension")
    assert (susp.clock_s, susp.team, susp.number, susp.name) == (
        322,
        "away",
        26,
        "Alexander Schütze",
    )
    # the last goal of the first half falls at 30:00 exactly
    last = next(e for e in r.entries if e.clock_s == 1800)
    assert service._period(last, 1800, r.half_time) == 1
    after = service.OfficialEntry(clock_s=1800, kind="goal", team="home", score=(14, 13))
    assert service._period(after, 1800, r.half_time) == 2
    with pytest.raises(ProblemError) as err:
        service.parse_dhb(1, "Hello\nworld\n")
    assert (err.value.status, err.value.code) == (422, "report-unreadable")


@pytest.mark.skipif(shutil.which("pdftotext") is None, reason="needs poppler-utils")
async def test_broken_pdf_is_unreadable() -> None:
    with pytest.raises(ProblemError) as err:
        await service._pdf_text(b"%PDF-1.3 broken")
    assert (err.value.status, err.value.code) == (422, "report-unreadable")


# ---- import into a match ---------------------------------------------------------------------


async def ingest(api: Api, job_id: str, prefix: str, duration_s: float | None) -> None:
    """The ingest job of a video finished (worker callback), with the video's length."""
    token = {"x-internal-token": api.app.state.settings.internal_token.get_secret_value()}
    r = await api.http.post(
        f"/internal/jobs/{job_id}",
        headers=token,
        json={
            "status": "succeeded",
            "progress": 1,
            "result": {
                "proxy_key": prefix + "proxy.mp4",
                "hls_prefix": prefix + "hls/",
                "duration_s": duration_s,
            },
        },
    )
    assert r.status_code == 200, r.text


async def reported_clip(api: Api, ids: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """Real club footage: the official report of the whole game (handball.ch, 22 events) and a
    video of five minutes that starts at 21:00 of the first half (throw-off at -21 min in video
    time). Most report events lie before (negative time) or after the video. Needs `recorded`."""
    from handball_api.core.jobs import MemoryJobQueue

    from .test_matches import upload

    m = await new_match(api, ids, opponent_name="HC Arbon")
    base = f"/v1/orgs/{ids['org']}/matches/{m['id']}"
    assert (await api.post(f"{base}/official-report", json={"url": CH_URL})).status_code == 200
    video = await upload(api, ids, m["id"], b"v" * 100)
    jobs: MemoryJobQueue = api.app.state.jobs
    await ingest(api, jobs.jobs[-1][2], jobs.jobs[-1][3]["prefix"], 300.0)
    # the clock shows 21:00 at the start of the video; the second half starts after it
    for body in ({"period": 1, "t_ms": 0, "clock_s": 1260}, {"period": 2, "t_ms": 1_500_000}):
        r = await api.put(f"{base}/kickoff", json=body)
        assert r.status_code == 204, r.text
    match = (await api.get(base)).json()
    assert match["kickoff_ms"] == {"1": -1_260_000, "2": 1_500_000}
    events = (await api.get(f"{base}/events")).json()
    times = [e["t_ms"] for e in events]
    assert any(t < 0 for t in times) and any(t > 300_000 for t in times)
    assert any(0 <= t <= 300_000 for t in times)
    return m, str(video["id"])


async def _roster(api: Api, ids: dict[str, Any], numbers: dict[int, str]) -> dict[int, str]:
    url = f"/v1/orgs/{ids['org']}/teams/{ids['team']}/seasons/{ids['season']}/roster"
    out = {}
    for n, name in numbers.items():
        r = await api.post(url, json={"first_name": name, "last_name": "X", "jersey_number": n})
        assert r.status_code == 201, r.text
        out[n] = r.json()["player_id"]
    return out


@pytest.mark.usefixtures("clean_db")
async def test_import_handball_ch_report(
    make_api: Callable[[], Api], recorded: list[tuple[str, int]]
) -> None:
    api = make_api()
    ids = await setup_club(api)
    players = await _roster(api, ids, {7: "Lisa", 33: "Denise", 1: "Aida"})
    m = await new_match(api, ids, opponent_name="HC Arbon")  # Leimental at home: we are home
    org = ids["org"]
    url = f"/v1/orgs/{org}/matches/{m['id']}/official-report"
    r = await api.post(url, json={"url": CH_URL})
    assert r.status_code == 200, r.text
    res = r.json()
    assert (res["provider"], res["game_id"], res["home"], res["final"]) == (
        "handball_ch",
        484345,
        "HSG Leimental",
        [25, 28],
    )
    assert res["created"] == 22 and res["replaced"] == 0
    assert res["warnings"] == ["numbers not in the roster: [6, 9, 32, 40]"]
    events = (await api.get(f"/v1/orgs/{org}/matches/{m['id']}/events")).json()
    assert {e["source"] for e in events} == {"official_report"}
    goals = [e for e in events if e["type"] == "shot" and e["outcome"] == "goal"]
    lisa = [e for e in goals if e["number"] == 7 and e["side"] == "own"]
    assert len(lisa) == 2 and {e["player_id"] for e in lisa} == {players[7]}
    assert lisa[0]["attributes"]["name"] == "ZUFALL Lisa"
    second_half = next(e for e in goals if e["clock_s"] == 1846)
    assert (second_half["period"], second_half["player_id"]) == (2, players[33])
    assert second_half["attributes"]["score"] == [13, 19]
    penalty = next(e for e in goals if e["shot_type"] == "penalty")
    assert (penalty["side"], penalty["shot_zone"], penalty["number"]) == ("opponent", "penalty", 5)
    save = next(e for e in events if e["clock_s"] == 42)
    assert (save["side"], save["outcome"], save["attributes"]["goalkeeper_id"]) == (
        "opponent",
        "save",
        players[1],
    )
    timeout = next(e for e in events if e["type"] == "timeout")
    assert (timeout["side"], timeout["clock_s"]) == ("own", 761)
    assert next(e for e in events if e["type"] == "suspension_2min")["number"] == 6
    match = (await api.get(f"/v1/orgs/{org}/matches/{m['id']}")).json()
    assert (match["score_own"], match["score_opponent"]) == (25, 28)
    assert (match["halftime_own"], match["halftime_opponent"]) == (12, 19)
    assert match["report_extra"]["official_report"]["game_id"] == 484345

    # idempotent: a re-import replaces the earlier rows
    again = (await api.post(url, json={"url": CH_URL})).json()
    assert (again["created"], again["replaced"]) == (22, 22)
    assert len((await api.get(f"/v1/orgs/{org}/matches/{m['id']}/events")).json()) == 22
    assert recorded == [("handball_ch", 484345), ("handball_ch", 484345)]


@pytest.mark.usefixtures("clean_db")
async def test_import_dhb_report_merges_video_goals(
    make_api: Callable[[], Api], recorded: list[tuple[str, int]], owner_conn: Any
) -> None:
    api = make_api()
    ids = await setup_club(api)
    players = await _roster(api, ids, {13: "Martin", 60: "Marc", 2: "Matheus"})
    m = await new_match(api, ids, opponent_name="SC Magdeburg II", is_home=False)  # we: Rostock
    org = ids["org"]
    ev_url = f"/v1/orgs/{org}/matches/{m['id']}/events"
    shot = {"type": "shot", "outcome": "goal", "period": 1}
    # tagged by hand (Pedersen's goal at 01:39): stays, no official duplicate
    manual = (await api.post(ev_url, json={**shot, "side": "own", "clock_s": 95})).json()
    # read from the overlay 9 s after Pedersen's goal at 04:31: merged into the official goal
    overlay = (await api.post(ev_url, json={**shot, "side": "own", "clock_s": 280})).json()
    # an overlay goal without an official one (no Magdeburg goal near 50:00) stays for checking
    lone = (await api.post(ev_url, json={**shot, "side": "opponent", "clock_s": 3000})).json()
    # an estimated goal: the report has every goal, the estimate goes
    guess = (await api.post(ev_url, json={**shot, "side": "opponent", "clock_s": 1000})).json()
    await owner_conn.execute(
        "UPDATE events SET source = 'scoreboard_ocr', t_ms = 300000, x = 34.0, y = 8.0,"
        " confidence = 0.95 WHERE id = $1",
        overlay["id"],
    )
    await owner_conn.execute(
        "UPDATE events SET source = 'scoreboard_ocr', period = 2 WHERE id = $1", lone["id"]
    )
    await owner_conn.execute("UPDATE events SET source = 'heuristic' WHERE id = $1", guess["id"])

    url = f"/v1/orgs/{org}/matches/{m['id']}/official-report"
    res = (await api.post(url, json={"url": "76839", "provider": "dhb"})).json()
    assert (res["home"], res["away"], res["final"]) == (
        "SC Magdeburg II",
        "HC Empor Rostock",
        [26, 26],
    )
    assert (res["matched_video_goals"], res["kept_manual_goals"], res["unmatched_video_goals"]) == (
        1,
        1,
        1,
    )
    assert res["created"] == 64 and res["warnings"] == [
        "numbers not in the roster: [7, 9, 23, 26, 43, 77, 87]"
    ]

    async def check() -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = (await api.get(ev_url)).json()
        ids_ = {e["id"] for e in events}
        assert manual["id"] in ids_ and lone["id"] in ids_
        assert overlay["id"] not in ids_ and guess["id"] not in ids_
        merged = next(e for e in events if e["source"] == "official_report" and e["clock_s"] == 271)
        assert (merged["t_ms"], merged["x"], merged["player_id"]) == (300_000, 34.0, players[13])
        assert merged["attributes"]["video"] == {
            "source": "scoreboard_ocr",
            "clock_s": 280.0,
            "t_ms": 300_000,
            "confidence": 0.95,
        }
        # the last goal of the first half at 30:00, scored by Magdeburg (the opponent)
        ht = next(e for e in events if e["clock_s"] == 1800 and e["type"] == "shot")
        assert (ht["period"], ht["side"], ht["shot_type"]) == (1, "opponent", "penalty")
        timeouts = [e["side"] for e in events if e["type"] == "timeout"]
        assert timeouts.count("own") == 3 and timeouts.count("opponent") == 3
        return events

    await check()
    stats = (await api.get(f"/v1/orgs/{org}/matches/{m['id']}/stats")).json()
    # 25 official + 1 tagged = the official result; the opponent's overlay goal without an
    # official one is a reading to check: it counts only once the coach confirms it
    assert (stats["own"]["goals"], stats["opponent"]["goals"]) == (26, 26)
    match = (await api.get(f"/v1/orgs/{org}/matches/{m['id']}")).json()
    assert (match["score_own"], match["score_opponent"], match["halftime_own"]) == (26, 26, 13)

    # re-import: same result, the video time taken over earlier is kept
    again = (await api.post(url, json={"url": DHB_URL})).json()
    assert (again["created"], again["replaced"], again["matched_video_goals"]) == (64, 64, 1)
    assert len(await check()) == 64 + 2


@pytest.mark.usefixtures("clean_db")
async def test_import_errors(make_api: Callable[[], Api], recorded: list[tuple[str, int]]) -> None:
    api = make_api()
    ids = await setup_club(api)
    m = await new_match(api, ids)
    url = f"/v1/orgs/{ids['org']}/matches/{m['id']}/official-report"
    cases = (
        ({"url": "https://www.youtube.com/watch?v=1"}, 422, "report-url-unsupported"),
        ({"url": "484345"}, 422, "report-url-unsupported"),
        ({"url": "https://www.handball.ch/de/matchcenter/spiele/1"}, 404, "report-not-found"),
        (
            {"url": "https://dhbdata.fmp.sportradar.com/match/1/pressReport.pdf"},
            422,
            "report-unreadable",
        ),
        ({"url": ""}, 422, "validation-error"),
    )
    for body, status, code in cases:
        r = await api.post(url, json=body)
        assert r.status_code == status, (body, r.text)
        assert r.json()["type"].endswith(code), r.text
    # nothing was imported, and the unsupported links were not fetched
    assert (await api.get(f"/v1/orgs/{ids['org']}/matches/{m['id']}/events")).json() == []
    assert recorded == [("handball_ch", 1), ("dhb", 1)]


@pytest.mark.usefixtures("clean_db")
async def test_analysis_after_import_does_not_count_goals_twice(
    make_api: Callable[[], Api], recorded: list[tuple[str, int]], owner_conn: Any
) -> None:
    """The report came first (no video time yet); the overlay of a later analysis sets the clock:
    the official goals get their video time and the overlay goals close to them are dropped, and
    no goals are estimated from throw-offs."""
    from handball_api.core.jobs import MemoryJobQueue

    from .test_auto_events import AUTO
    from .test_identity_sync import _finish, _ingest, _tracks
    from .test_matches import upload

    api = make_api()
    ids = await setup_club(api)
    m = await new_match(api, ids, opponent_name="HC Arbon")  # home: the overlay's left team is us
    org = ids["org"]
    r = await api.post(f"/v1/orgs/{org}/matches/{m['id']}/official-report", json={"url": CH_URL})
    assert r.status_code == 200, r.text
    ev_url = f"/v1/orgs/{org}/matches/{m['id']}/events"
    assert all(e["t_ms"] is None for e in (await api.get(ev_url)).json())

    overlay = {
        "goals": [
            {"t_ms": 35_000, "side": "left", "score": [1, 0]},  # clock 1:35, official 1:33
            {"t_ms": 200_000, "side": "right", "score": [2, 2]},  # clock 4:20, official 4:02
            {"t_ms": 500_000, "side": "right", "score": [2, 4]},  # clock 9:20: not in the report
        ],
        "clock": [{"start_ms": 0, "end_ms": 600_000, "start_clock_s": 60, "reads": 50}],
    }
    await upload(api, ids, m["id"], b"v" * 100)
    jobs: MemoryJobQueue = api.app.state.jobs
    await _ingest(api, jobs.jobs[-1][2], jobs.jobs[-1][3]["prefix"])
    payload = {"tracks": _tracks(), "detector": "model", "events": AUTO, "scoreboard": overlay}
    await _finish(api, jobs.jobs[-1][2], payload)

    events = (await api.get(ev_url)).json()
    official = [e for e in events if e["source"] == "official_report"]
    # the clip shows the first half only: the second half has no throw-off time yet
    assert len(official) == 22
    assert all((e["t_ms"] is not None) == (e["period"] == 1) for e in official)
    first = next(e for e in official if e["clock_s"] == 93)
    assert first["t_ms"] == 33_000  # throw-off at -60 s in this clip
    read = [(e["side"], e["t_ms"]) for e in events if e["source"] == "scoreboard_ocr"]
    assert read == [("opponent", 500_000)]
    assert not [e for e in events if e["source"] == "heuristic" and e["type"] == "shot"]
    # the official goals keep what the overlay read, so the comparison shows them as found
    assert first["attributes"]["video"] == {
        "source": "scoreboard_ocr",
        "clock_s": 95.0,
        "t_ms": 35_000,
        "confidence": 0.95,
    }
    cmp = (await api.get(f"/v1/orgs/{org}/matches/{m['id']}/official-report/comparison")).json()
    assert cmp["counts"] == {
        "official": 8,
        "found": 2,
        "missing": 6,
        "outside": 0,
        "extra": 1,
        "open": 7,
    }
    row = next(r for r in cmp["goals"] if r["clock_s"] == 93)
    assert (row["status"], row["t_ms"], row["estimated"], row["official_time"]) == (
        "found",
        35_000,
        False,
        "01:33",
    )
    assert [(x["side"], x["t_ms"]) for x in cmp["extra"]] == [("opponent", 500_000)]

    # the video is a clip of five minutes: goals the clock puts after it are outside, not missing
    await owner_conn.execute(
        "UPDATE video_assets SET duration_s = 300 WHERE match_id = $1::uuid", m["id"]
    )
    later = [
        g["event_id"]
        for g in cmp["goals"]
        if g["status"] == "missing" and g["t_ms"] is not None and g["t_ms"] > 300_000
    ]
    assert later
    clip = (await api.get(f"/v1/orgs/{org}/matches/{m['id']}/official-report/comparison")).json()
    assert [g["event_id"] for g in clip["goals"] if g["status"] == "outside"] == later
    assert clip["counts"] == {
        "official": 8,
        "found": 2,
        "missing": 6 - len(later),
        "outside": len(later),
        "extra": 1,
        "open": 7 - len(later),
    }


# ---- official goals compared with the video ----------------------------------------------------


@pytest.mark.usefixtures("clean_db")
async def test_goal_comparison_and_review(
    make_api: Callable[[], Api], recorded: list[tuple[str, int]], owner_conn: Any
) -> None:
    api = make_api()
    ids = await setup_club(api)
    m = await new_match(api, ids, opponent_name="SC Magdeburg II", is_home=False)
    org = ids["org"]
    base = f"/v1/orgs/{org}/matches/{m['id']}"
    cmp_url, review_url = f"{base}/official-report/comparison", f"{base}/official-report/review"

    # nothing imported yet: an empty comparison
    empty = (await api.get(cmp_url)).json()
    assert empty["imported"] is False and empty["goals"] == [] and empty["extra"] == []
    assert empty["counts"] == {
        "official": 0,
        "found": 0,
        "missing": 0,
        "outside": 0,
        "extra": 0,
        "open": 0,
    }

    shot = {"type": "shot", "outcome": "goal", "period": 1}
    overlay = (
        await api.post(f"{base}/events", json={**shot, "side": "own", "clock_s": 280})
    ).json()
    lone = (
        await api.post(f"{base}/events", json={**shot, "side": "opponent", "clock_s": 3000})
    ).json()
    await owner_conn.execute(
        "UPDATE events SET source = 'scoreboard_ocr', t_ms = 300000, confidence = 0.95"
        " WHERE id = ANY($1::uuid[])",
        [overlay["id"], lone["id"]],
    )
    await owner_conn.execute("UPDATE events SET period = 2 WHERE id = $1", lone["id"])
    r = await api.post(f"{base}/official-report", json={"url": DHB_URL})
    assert r.status_code == 200, r.text

    cmp = (await api.get(cmp_url)).json()
    assert (cmp["imported"], cmp["provider"], cmp["home"], cmp["window_s"]) == (
        True,
        "dhb",
        "SC Magdeburg II",
        20.0,
    )
    # 52 goals in the report; merged on import: Pedersen's goal at 04:31
    assert cmp["counts"] == {
        "official": 52,
        "found": 1,
        "missing": 51,
        "outside": 0,
        "extra": 1,
        "open": 52,
    }
    goals = cmp["goals"]
    assert [g["clock_s"] for g in goals] == sorted(g["clock_s"] for g in goals)
    merged = next(g for g in goals if g["status"] == "found")
    assert (merged["official_time"], merged["side"], merged["number"], merged["t_ms"]) == (
        "04:31",
        "own",
        13,
        300_000,
    )
    assert merged["video"]["source"] == "scoreboard_ocr" and merged["video"]["event_id"] is None
    # no throw-off time yet: the missing goals have no video time to jump to
    missing = next(g for g in goals if g["status"] == "missing")
    assert (missing["t_ms"], missing["estimated"], missing["video"]) == (None, True, None)
    assert cmp["extra"][0]["event_id"] == lone["id"]

    # a goal read from the video after the import, 6 s of clock after an official one: paired
    target = next(g for g in goals if g["status"] == "missing" and g["side"] == "opponent")
    late = (
        await api.post(
            f"{base}/events",
            json={**shot, "side": "opponent", "clock_s": target["clock_s"] + 6, "t_ms": 900_000},
        )
    ).json()
    await owner_conn.execute(
        "UPDATE events SET source = 'scoreboard_ocr', confidence = 0.8 WHERE id = $1", late["id"]
    )
    cmp = (await api.get(cmp_url)).json()
    assert (cmp["counts"]["found"], cmp["counts"]["extra"]) == (2, 1)
    paired = next(g for g in cmp["goals"] if g["event_id"] == target["event_id"])
    assert (paired["status"], paired["t_ms"], paired["estimated"]) == ("found", 900_000, False)
    assert paired["video"] == {
        "source": "scoreboard_ocr",
        "t_ms": 900_000,
        "clock_s": target["clock_s"] + 6,
        "confidence": 0.8,
        "event_id": late["id"],
    }

    # the coach checks rows: a missing goal confirmed, the lone video goal dismissed
    check = next(g for g in cmp["goals"] if g["status"] == "missing")
    for event_id, status in ((check["event_id"], "confirmed"), (lone["id"], "dismissed")):
        r = await api.put(review_url, json={"event_id": event_id, "status": status})
        assert r.status_code == 204, r.text
    cmp = (await api.get(cmp_url)).json()
    assert cmp["counts"]["open"] == 50 - 1
    assert next(g for g in cmp["goals"] if g["event_id"] == check["event_id"])["review"] == (
        "confirmed"
    )
    assert cmp["extra"][0]["review"] == "dismissed"
    # a re-import keeps the checks of the official goals
    await api.post(f"{base}/official-report", json={"url": DHB_URL})
    cmp = (await api.get(cmp_url)).json()
    again = next(g for g in cmp["goals"] if g["clock_s"] == check["clock_s"] and g["review"])
    assert (again["review"], cmp["counts"]["open"]) == ("confirmed", 49)
    # undo
    r = await api.put(review_url, json={"event_id": lone["id"], "status": None})
    assert r.status_code == 204
    assert (await api.get(cmp_url)).json()["extra"][0]["review"] is None

    # only goals of the comparison can be checked
    events = (await api.get(f"{base}/events")).json()
    timeout = next(e for e in events if e["type"] == "timeout")
    tagged = (await api.post(f"{base}/events", json={**shot, "side": "own", "clock_s": 10})).json()
    for event_id in (timeout["id"], tagged["id"], "00000000-0000-0000-0000-000000000000"):
        r = await api.put(review_url, json={"event_id": event_id, "status": "confirmed"})
        assert r.status_code == 404, r.text
    r = await api.put(review_url, json={"event_id": lone["id"], "status": "maybe"})
    assert r.status_code == 422


@pytest.mark.usefixtures("clean_db")
async def test_import_is_rate_limited_per_user(make_api: Callable[[], Api]) -> None:
    """Each import fetches from the federation's server and reads a PDF: limited per person."""

    class Spent:
        async def hit(self, key: str, limit: int, window: int) -> bool:
            return not key.startswith("official-report:")

    api = make_api()
    ids = await setup_club(api)
    m = await new_match(api, ids)
    api.app.state.rate_limiter = Spent()
    r = await api.post(
        f"/v1/orgs/{ids['org']}/matches/{m['id']}/official-report",
        json={"url": "https://www.handball.ch/de/matchcenter/spiele/484345"},
    )
    assert r.status_code == 429, r.text
