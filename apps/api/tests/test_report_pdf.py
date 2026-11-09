"""PDF match report (M8)."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from handball_api.services.report_pdf import TEXTS, insight_text

from .conftest import Api, setup_club
from .test_insights_api import tagged_match

pytestmark = pytest.mark.usefixtures("clean_db")
WEB = Path(__file__).resolve().parents[2] / "web" / "messages"


def test_insight_texts_match_the_web_app() -> None:
    for lang in ("de-CH", "en", "fr"):
        web = json.loads((WEB / f"{lang}.json").read_text(encoding="utf-8"))
        for key, text in TEXTS[lang]["insights"].items():
            assert web["insights"][key] == text, (lang, key)
        # "Fernwurf / leeres Tor" split into long_range and empty_goal: the web labels follow
        # with the UI handover (docs/plans/ui-match-workspace.md)
        split = {"long_range", "empty_goal"}
        assert {k: v for k, v in TEXTS[lang]["zones"].items() if k not in split} == {
            k: v for k, v in web["zones"].items() if k not in split
        }


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
