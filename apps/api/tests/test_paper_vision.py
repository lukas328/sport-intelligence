"""Photographed paper match reports (addendum 01, 5.9)."""

from __future__ import annotations

import copy
import json
import os
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import asyncpg
import pytest

from handball_api.core.paper_vision import (
    EXTRACTION_SCHEMA,
    ClaudePaperExtractor,
    PaperExtractionError,
)
from handball_api.services.paper_vision import to_report, validate

from .conftest import Api, setup_club

pytestmark = pytest.mark.usefixtures("clean_db")

SHEET: dict[str, Any] = {
    "readable": True,
    "date": "2026-10-18",
    "kickoff": "17:30",
    "opponent": "TV Papier",
    "home": True,
    "competition": "2. Liga",
    "score": {"own": 24, "opponent": 22},
    "halftime": {"own": 12, "opponent": 11},
    "players": [
        {
            "number": 7,
            "name": "Lena",
            "goals": 9,
            "misses": 3,
            "seven_m_goals": 4,
            "seven_m_misses": 1,
            "suspensions": 1,
            "assists": 2,
        },
        {
            "number": 9,
            "name": None,
            "goals": 8,
            "misses": 5,
            "seven_m_goals": 0,
            "seven_m_misses": 0,
            "suspensions": 0,
            "assists": 4,
        },
        {
            "number": 11,
            "name": "Mia",
            "goals": 6,
            "misses": 2,
            "seven_m_goals": 0,
            "seven_m_misses": 0,
            "suspensions": 0,
            "assists": 1,
        },
    ],
    "goalkeepers": [{"number": 1, "name": "Tina", "saves": 12}],
    "score_progression": [
        {"minute": 10, "own": 4, "opponent": 5},
        {"minute": 30, "own": 12, "opponent": 11},
        {"minute": 60, "own": 24, "opponent": 22},
    ],
    "team_goals_total": 23,
    "uncertain": ["players[1].goals"],
    "notes": None,
}


class FakeExtractor:
    model = "fake"

    def __init__(self, result: dict[str, Any] | Exception) -> None:
        self.result = result
        self.calls: list[str] = []

    async def extract(self, image: bytes, media_type: str) -> dict[str, Any]:
        self.calls.append(media_type)
        if isinstance(self.result, Exception):
            raise self.result
        return copy.deepcopy(self.result)


def test_checks_and_conversion() -> None:
    codes = {i["code"] for i in validate(SHEET)}
    # 9 + 8 + 6 = 23 goals but the score says 24; the total line agrees with the players
    assert codes == {"goals_vs_score", "uncertain"}
    fixed = {
        **SHEET,
        "players": [
            *SHEET["players"][:1],
            {**SHEET["players"][1], "goals": 9},
            SHEET["players"][2],
        ],
        "team_goals_total": 24,
        "uncertain": [],
    }
    assert validate(fixed) == []
    broken = {
        **fixed,
        "score_progression": [
            {"minute": 10, "own": 5, "opponent": 2},
            {"minute": 20, "own": 3, "opponent": 4},
        ],
    }
    assert {i["code"] for i in validate(broken)} == {"progression_decreases"}
    wrong_final = {**fixed, "score_progression": [{"minute": 60, "own": 26, "opponent": 22}]}
    assert {i["code"] for i in validate(wrong_final)} == {"score_vs_progression"}
    seven = {
        **fixed,
        "players": [{**fixed["players"][0], "seven_m_goals": 12}, *fixed["players"][1:]],
    }
    assert "seven_m_above_goals" in {i["code"] for i in validate(seven)}
    dup = {**fixed, "players": [fixed["players"][0], fixed["players"][0]]}
    assert "duplicate_number" in {i["code"] for i in validate(dup)}
    empty = {"readable": False, "players": [], "uncertain": []}
    assert {i["code"] for i in validate(empty)} == {"unreadable", "missing"}
    report = to_report(fixed)
    assert report["schema"] == "handball-paper-report/1" and report["halftime"] == {
        "own": 12,
        "opponent": 11,
    }
    assert "name" not in report["players"][1]  # null names are dropped, not imported as "None"


async def test_upload_review_confirm(
    make_api: Callable[[], Api], owner_conn: asyncpg.Connection
) -> None:
    api = make_api()
    ids = await setup_club(api)
    org, team = ids["org"], ids["team"]
    url = f"/v1/orgs/{org}/teams/{team}/paper-photos"
    photo = {"file": ("bogen.jpg", b"\xff\xd8\xff" + b"0" * 500, "image/jpeg")}
    api.app.state.paper = None
    assert (await api.post(url, files=photo)).status_code == 503
    fake = FakeExtractor(SHEET)
    api.app.state.paper = fake
    bad = await api.post(url, files={"file": ("bogen.gif", b"GIF89a", "image/gif")})
    assert bad.status_code == 415
    r = await api.post(url, files=photo)
    assert r.status_code == 201, r.text
    up = r.json()
    assert up["status"] == "extracted" and fake.calls == ["image/jpeg"]
    assert {e["code"] for e in up["errors"]} == {"goals_vs_score", "uncertain"}
    pic = await api.get(f"/v1/orgs/{org}/paper-photos/{up['id']}/photo")
    assert pic.status_code == 200 and pic.content.startswith(b"\xff\xd8")

    confirm = f"/v1/orgs/{org}/paper-photos/{up['id']}/confirm"
    r = await api.post(confirm, json={})
    assert r.status_code == 422 and r.json()["type"].endswith("paper-warnings")
    # the coach checks the photo: number 9 scored 9, not 8
    fixed = copy.deepcopy(SHEET)
    fixed["players"][1]["goals"] = 9
    fixed["uncertain"] = []
    fixed["team_goals_total"] = 24
    corrected = (
        await api.put(f"/v1/orgs/{org}/paper-photos/{up['id']}", json={"extraction": fixed})
    ).json()
    assert corrected["errors"] == []
    done = (await api.post(confirm, json={})).json()
    assert done["status"] == "confirmed" and done["match_id"]
    match = await owner_conn.fetchrow(
        "SELECT source, score_own, score_opponent FROM matches WHERE id = $1::uuid",
        done["match_id"],
    )
    assert dict(match) == {"source": "paper_report", "score_own": 24, "score_opponent": 22}
    goals = await owner_conn.fetchval(
        "SELECT count(*) FROM events WHERE match_id = $1::uuid "
        "AND outcome = 'goal' AND side = 'own'",
        done["match_id"],
    )
    assert goals == 24
    assert (await api.post(confirm, json={})).status_code == 409
    assert len((await api.get(url)).json()) == 1

    # an unreadable photo cannot be imported, a failing model marks the upload failed
    api.app.state.paper = FakeExtractor({"readable": False, "players": [], "uncertain": []})
    up2 = (await api.post(url, files=photo)).json()
    r = await api.post(
        f"/v1/orgs/{org}/paper-photos/{up2['id']}/confirm", json={"accept_warnings": True}
    )
    assert r.status_code == 422 and r.json()["type"].endswith("paper-incomplete")
    api.app.state.paper = FakeExtractor(PaperExtractionError("refusal"))
    up3 = (await api.post(url, files=photo)).json()
    assert up3["status"] == "failed" and up3["errors"][0]["code"] == "extraction_failed"


async def test_claude_extractor_request() -> None:
    class Messages:
        def __init__(self) -> None:
            self.calls: list[dict[str, Any]] = []

        async def create(self, **kw: Any) -> Any:
            self.calls.append(kw)
            return SimpleNamespace(
                stop_reason="end_turn",
                content=[SimpleNamespace(type="text", text=json.dumps(SHEET))],
            )

    x = ClaudePaperExtractor("sk-test")
    fake = Messages()
    x.client = SimpleNamespace(messages=fake)  # type: ignore[assignment]
    assert (await x.extract(b"img", "image/png"))["opponent"] == "TV Papier"
    call = fake.calls[0]
    assert call["model"] == "claude-opus-5-5"
    assert call["output_config"]["format"]["schema"] is EXTRACTION_SCHEMA
    image = call["messages"][0]["content"][0]
    assert image["type"] == "image" and image["source"]["media_type"] == "image/png"

    def all_objects_closed(schema: Any) -> bool:
        if isinstance(schema, dict):
            if schema.get("type") == "object" and schema.get("additionalProperties") is not False:
                return False
            return all(all_objects_closed(v) for v in schema.values())
        if isinstance(schema, list):
            return all(all_objects_closed(v) for v in schema)
        return True

    assert all_objects_closed(EXTRACTION_SCHEMA)  # structured outputs need closed objects


@pytest.mark.live
async def test_live_sheet_accuracy() -> None:
    """5.9 acceptance: >= 95 % of the number fields correct on 10 real sheets. Put photos and the
    true values as ml/eval/paper_sheets/<name>.jpg + <name>.json (extraction schema) and run with
    HB_ANTHROPIC_API_KEY set: uv run pytest -m live apps/api/tests/test_paper_vision.py."""
    key = os.environ.get("HB_ANTHROPIC_API_KEY")
    folder = Path(__file__).resolve().parents[3] / "ml" / "eval" / "paper_sheets"  # noqa: ASYNC240
    sheets = sorted(folder.glob("*.jpg")) if folder.exists() else []
    if not key or len(sheets) < 10:
        pytest.skip("needs HB_ANTHROPIC_API_KEY and 10 sheets in ml/eval/paper_sheets")
    x = ClaudePaperExtractor(key)
    right = total = 0
    for img in sheets:
        truth = json.loads(img.with_suffix(".json").read_text())
        got = await x.extract(img.read_bytes(), "image/jpeg")
        by_number = {p["number"]: p for p in got.get("players") or []}
        for p in truth["players"]:
            for field in (
                "goals",
                "misses",
                "seven_m_goals",
                "seven_m_misses",
                "suspensions",
                "assists",
            ):
                total += 1
                right += int(by_number.get(p["number"], {}).get(field) == p[field])
        for side in ("own", "opponent"):
            total += 1
            right += int((got.get("score") or {}).get(side) == truth["score"][side])
    assert right / total >= 0.95, right / total
