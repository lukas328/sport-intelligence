"""PDF match report (M8)."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from handball_api.services.report_pdf import TEXTS, comparison_rows, insight_text, player_columns

from .conftest import Api, setup_club
from .test_insights_api import tagged_match

pytestmark = pytest.mark.usefixtures("clean_db")
WEB = Path(__file__).resolve().parents[2] / "web" / "messages"


def test_insight_texts_match_the_web_app() -> None:
    for lang in ("de-CH", "en", "fr"):
        web = json.loads((WEB / f"{lang}.json").read_text(encoding="utf-8"))
        for key, text in TEXTS[lang]["insights"].items():
            assert web["insights"][key] == text, (lang, key)
        assert TEXTS[lang]["zones"] == web["zones"], lang


def test_insight_text_formatting() -> None:
    item = {
        "key": "insights.zone_weak",
        "params": {"zone": "wing_left", "k": 1, "n": 6, "avg": 55},
    }
    assert insight_text("de-CH", item, {}).startswith("Von Aussen links nur 1 Tore aus 6")
    keeper = {
        "key": "insights.keeper_good",
        "params": {"player_id": "p1", "number": 1, "saves": 12, "faced": 25, "gsax": 3.21},
    }
    assert "Mia Tor" in insight_text("en", keeper, {"p1": "Mia Tor"})
    assert "3.2" in insight_text("en", keeper, {})
    assert insight_text("fr", {"key": "insights.unknown", "params": {}}, {}) == ""
    broken = {"key": "insights.drought", "params": {}}
    assert "{minutes}" in insight_text("de-CH", broken, {})


async def test_pdf_endpoint(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    roster = f"/v1/orgs/{org}/teams/{ids['team']}/seasons/{ids['season']}/roster"
    await api.post(roster, json={"first_name": "Lea", "last_name": "Müller", "jersey_number": 9})
    for day in ("05", "12"):
        await tagged_match(api, ids, 15, 10, kickoff_at=f"2026-09-{day}T18:00:00+02:00")
    m = await tagged_match(
        api, ids, 8, 20, kickoff_at="2026-09-19T18:00:00+02:00", competition="2. Liga"
    )
    await api.patch(
        f"/v1/orgs/{org}/matches/{m}",
        json={"score_own": 8, "score_opponent": 6, "halftime_own": 4, "halftime_opponent": 3},
    )
    for lang in ("de-CH", "en", "fr"):
        r = await api.get(f"/v1/orgs/{org}/matches/{m}/report.pdf", params={"lang": lang})
        assert r.status_code == 200, r.text
        assert r.headers["content-type"] == "application/pdf"
        assert r.content.startswith(b"%PDF") and len(r.content) > 3000
        assert 'filename="matchreport-2026-09-19-tv-gegner.pdf"' in r.headers["content-disposition"]
    empty = await api.post(
        f"/v1/orgs/{org}/teams/{ids['team']}/matches",
        json={"opponent_name": "Leer", "kickoff_at": "2026-10-01T18:00:00+02:00", "is_home": False},
    )
    r = await api.get(f"/v1/orgs/{org}/matches/{empty.json()['id']}/report.pdf")
    assert r.status_code == 200 and r.content.startswith(b"%PDF")
    assert (
        await api.get(f"/v1/orgs/{org}/matches/{m}/report.pdf", params={"lang": "it"})
    ).status_code == 422


def _side(**over: object) -> dict[str, object]:
    base: dict[str, object] = {
        "goals": 24,
        "shots": 24,
        "shooting_pct": 1.0,
        "saves": 0,
        "save_pct": None,
        "turnovers": 0,
        "seven_m_goals": 0,
        "seven_m_shots": 0,
        "fast_break_goals": 0,
        "suspensions": 0,
        "xg": 0.0,
        "xg_shots": 0,
        "known": {"shooting": False, "saving": False, "turnovers": False},
    }
    return {**base, **over}


def test_the_not_recorded_label_matches_the_web_app() -> None:
    for lang in ("de-CH", "en", "fr"):
        web = json.loads((WEB / f"{lang}.json").read_text(encoding="utf-8"))
        assert TEXTS[lang]["labels"]["notRecorded"] == web["stats"]["notRecorded"], lang


def test_goals_alone_print_no_zeros_for_what_was_never_recorded() -> None:
    """A match with the federation's goals only: no shots, saves, turnovers or xG of 0, and no
    100 % shooting (the PDF printed them as measured figures)."""
    t = TEXTS["de-CH"]["labels"]
    stats = {"quality": {"attempts_known": False}}
    rows = comparison_rows(t, _side(), _side(goals=21, shots=21), stats)
    assert [r[0] for r in rows] == ["Tore", "Wurfquote", "Paradenquote"]
    assert rows[1][1:] == ["nicht erfasst", "nicht erfasst"]
    cols = [label for label, _ in player_columns(t, _side()["known"])]  # type: ignore[arg-type]
    assert cols == ["Tore", "7 m", "2 Minuten"]


def test_recorded_figures_are_printed_and_unknown_sides_say_so() -> None:
    t = TEXTS["en"]["labels"]
    known = {"shooting": True, "saving": False, "turnovers": True}
    own = _side(
        shots=40, shooting_pct=0.6, turnovers=9, suspensions=2, xg=21.4, xg_shots=30, known=known
    )
    opp = _side(
        goals=20,
        shots=38,
        shooting_pct=0.53,
        saves=11,
        save_pct=0.35,
        turnovers=12,
        known={"shooting": True, "saving": True, "turnovers": True},
    )
    rows = {
        r[0]: r[1:] for r in comparison_rows(t, own, opp, {"quality": {"attempts_known": True}})
    }
    assert rows["Shots"] == [40, 38]
    assert rows["Shooting %"] == ["60 %", "53 %"]
    assert rows["Saves"] == ["not recorded", 11]
    assert rows["Turnovers"] == [9, 12] and rows["2 minutes"] == [2, 0]
    assert rows["xG (estimated)"] == ["21.4", "0.0"]
    assert t["sevenM"] not in rows  # 0/0 on both sides
    player = {
        "goals": 6,
        "shots": 9,
        "seven_m_goals": 1,
        "seven_m_shots": 2,
        "turnovers": 2,
        "suspensions": 0,
        "saves": 0,
    }
    cells = {label: cell(player) for label, cell in player_columns(t, known)}
    assert cells[t["shots"]] == 9 and cells[t["shootingPct"]] == "67 %"
    assert t["saves"] not in cells
    # older stats without `known` print everything, as before
    old = {k: v for k, v in own.items() if k != "known"}
    assert len(comparison_rows(t, old, old, {"quality": {}})) >= 6
