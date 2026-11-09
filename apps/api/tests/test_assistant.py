"""Data assistant (addendum 01, 5.1): tools, number validator, logging, budget, eval set."""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, time
from typing import Any

import asyncpg
import pytest

from handball_api.core.assistant_llm import (
    AssistantUnavailableError,
    ModelTurn,
    Usage,
    invented_numbers,
    numbers_from,
)

from .assistant_eval import MATCHES, NUMBERS, PLAYS, QUESTIONS, Question, ScriptedModel, score
from .conftest import Api, setup_club
from .test_matches import new_match
from .test_official_report import recorded  # noqa: F401

pytestmark = pytest.mark.usefixtures("clean_db")


async def seed(api: Api, owner_conn: asyncpg.Connection) -> dict[str, Any]:
    """The evaluation season of assistant_eval.py in a fresh club."""
    ids = await setup_club(api)
    org, team, season = ids["org"], ids["team"], ids["season"]
    roster_url = f"/v1/orgs/{org}/teams/{team}/seasons/{season}/roster"
    players = {}
    for n in NUMBERS:
        r = await api.post(
            roster_url, json={"first_name": f"P{n}", "last_name": "X", "jersey_number": n}
        )
        players[n] = r.json()["player_id"]
    plays = {}
    for name in PLAYS:
        doc = {"formatVersion": 1, "court": "half", "frames": [{"tokens": [], "duration_ms": 1000}]}
        r = await api.post(
            f"/v1/orgs/{org}/teams/{team}/plays",
            json={"name": name, "category": "attack", "doc": doc},
        )
        plays[name] = r.json()["id"]
    rows = []
    for m in MATCHES:
        kickoff = datetime.combine(m.day, time(18, 0), tzinfo=UTC).isoformat()
        match = await new_match(api, ids, opponent_name=m.opponent, kickoff_at=kickoff)
        own, opp = m.score
        await owner_conn.execute(
            "UPDATE matches SET score_own = $1, score_opponent = $2 WHERE id = $3::uuid",
            own,
            opp,
            match["id"],
        )
        for e in m.events:
            player = players[e["number"]] if e["side"] == "own" and e["number"] else None
            attrs = {"play_id": plays[e["play"]]} if e["play"] else {}
            rows.append(
                (
                    uuid.uuid4(),
                    uuid.UUID(org),
                    uuid.UUID(match["id"]),
                    e["type"],
                    e["side"],
                    e["period"],
                    e["clock_s"],
                    e["t_ms"],
                    uuid.UUID(player) if player else None,
                    None if player else e["number"],
                    e["x"],
                    e["y"],
                    e["outcome"],
                    e["shot_type"],
                    e["goal_zone"],
                    e["turnover_type"],
                    json.dumps(attrs),
                )
            )
    await owner_conn.executemany(
        "INSERT INTO events (id, organization_id, match_id, type, side, period, clock_s, t_ms, "
        "player_id, number, x, y, outcome, shot_type, goal_zone, turnover_type, attributes, "
        "confidence, source) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, "
        "$15, $16, $17::jsonb, 1.0, 'user_correction')",
        rows,
    )
    return ids


def ask_url(ids: dict[str, Any]) -> str:
    return f"/v1/orgs/{ids['org']}/teams/{ids['team']}/assistant"


async def test_eval_set_regression(
    make_api: Callable[[], Api], owner_conn: asyncpg.Connection
) -> None:
    """Every question of the evaluation set, replayed with its tool plan, gives the expected
    answer, passes the number validator and is logged (5.1: >= 60 questions, no invented number)."""
    assert len(QUESTIONS) >= 60
    assert len({q.id for q in QUESTIONS}) == len(QUESTIONS)
    api = make_api()
    ids = await seed(api, owner_conn)
    failures = []
    for q in QUESTIONS:
        api.app.state.assistant = ScriptedModel(q)
        r = await api.post(ask_url(ids), json={"question": q.text})
        assert r.status_code == 201, (q.id, r.text)
        body = r.json()
        if not (score(body["answer"], q) and body["validated"]):
            failures.append((q.id, body["answer"], q.expect(), body["status"]))
    assert failures == []
    logged = await owner_conn.fetchval("SELECT count(*) FROM assistant_messages")
    assert logged == len(QUESTIONS)


async def test_validator_correction_fallback_and_clips(
    make_api: Callable[[], Api], owner_conn: asyncpg.Connection
) -> None:
    api = make_api()
    ids = await seed(api, owner_conn)
    q = next(x for x in QUESTIONS if x.id == "clips_no7")
    # an invented number gets one correction round; the corrected answer is shown
    api.app.state.assistant = ScriptedModel(q, invent=True)
    body = (await api.post(ask_url(ids), json={"question": q.text})).json()
    assert body["validated"] and "4711" not in body["answer"]["text"]
    calls = [c["name"] for c in body["tool_calls"]]
    assert calls == ["query_events", "get_clips", "final_answer"]
    clips = body["answer"]["clips"]
    assert clips and all(c["t_ms"] is not None and c["label"] for c in clips)

    class Liar:
        model = "liar"

        async def respond(self, *_: Any) -> ModelTurn:
            block = {
                "type": "tool_use",
                "id": "x",
                "name": "final_answer",
                "input": {"answerable": True, "text": "Ihr trefft 87 Prozent.", "values": [87]},
            }
            return ModelTurn([block], "tool_use", Usage(10, 10), "liar", 1)

    api.app.state.assistant = Liar()
    body = (await api.post(ask_url(ids), json={"question": "Wie gut treffen wir?"})).json()
    assert body["answer"]["answerable"] is False and body["answer"]["suggestion"]
    assert body["status"] == "invented_numbers" and body["validated"] is False
    assert "87" not in body["answer"]["text"]

    class Broken:
        model = "broken"

        async def respond(self, *_: Any) -> ModelTurn:
            raise AssistantUnavailableError("connection")

    api.app.state.assistant = Broken()
    body = (await api.post(ask_url(ids), json={"question": "Wie gut treffen wir?"})).json()
    assert body["status"] == "model_connection" and body["answer"]["answerable"] is False

    class Plain:
        """Answers in plain text without the final tool: accepted when the numbers check out."""

        model = "plain"

        async def respond(self, *_: Any) -> ModelTurn:
            return ModelTurn([{"type": "text", "text": "In 5 Spielen nichts Neues."}], "end_turn")

    api.app.state.assistant = Plain()
    r = await api.post(
        ask_url(ids), json={"question": "Was war in den letzten 5 Spielen?", "lang": "fr"}
    )
    assert r.json()["validated"] and r.json()["answer"]["text"].startswith("In 5")

    class BadTool:
        """A tool error (unknown filter) goes back to the model as an error result."""

        model = "bad"
        calls = 0

        async def respond(self, system: str, tools: Any, messages: Any) -> ModelTurn:
            self.calls += 1
            if self.calls == 1:
                block = {
                    "type": "tool_use",
                    "id": "b",
                    "name": "aggregate_metric",
                    "input": {"metric": "goals", "filter": {"colour": "red"}},
                }
                return ModelTurn([block], "tool_use")
            last = messages[-1]["content"][0]
            assert last["is_error"] and "unknown filter" in last["content"]
            block = {
                "type": "tool_use",
                "id": "f",
                "name": "final_answer",
                "input": {"answerable": False, "text": "Nicht möglich.", "suggestion": "Tore?"},
            }
            return ModelTurn([block], "tool_use")

    api.app.state.assistant = BadTool()
    body = (await api.post(ask_url(ids), json={"question": "Tore in Rot?"})).json()
    assert body["tool_calls"][0]["error"]


async def test_conversation_history_rating_budget_and_rights(
    make_api: Callable[[], Api], owner_conn: asyncpg.Connection
) -> None:
    api = make_api()
    ids = await seed(api, owner_conn)
    q: Question = QUESTIONS[0]
    api.app.state.assistant = ScriptedModel(q)
    first = (await api.post(ask_url(ids), json={"question": q.text})).json()
    seen: list[list[dict[str, Any]]] = []

    class Recorder(ScriptedModel):
        async def respond(self, system: str, tools: Any, messages: Any) -> ModelTurn:
            seen.append(messages)
            return await super().respond(system, tools, messages)

    api.app.state.assistant = Recorder(q)
    second = (
        await api.post(
            ask_url(ids),
            json={"question": "Und davor?", "conversation_id": first["conversation_id"]},
        )
    ).json()
    assert second["conversation_id"] == first["conversation_id"]
    # earlier turns go back as plain text, the new question with the team context
    assert seen[0][0] == {"role": "user", "content": q.text}
    assert seen[0][1]["role"] == "assistant" and isinstance(seen[0][1]["content"], str)
    assert "Und davor?" in seen[0][2]["content"]
    org = ids["org"]
    convs = (await api.get(ask_url(ids))).json()
    assert len(convs) == 1
    detail = (await api.get(f"/v1/orgs/{org}/assistant/{first['conversation_id']}")).json()
    assert [m["question"] for m in detail["messages"]] == [q.text, "Und davor?"]
    r = await api.post(
        f"/v1/orgs/{org}/assistant/messages/{first['id']}/rating", json={"rating": 1}
    )
    assert r.status_code == 204
    assert (
        await owner_conn.fetchval(
            "SELECT rating FROM assistant_messages WHERE id = $1::uuid", first["id"]
        )
        == 1
    )

    # monthly budget: once used up, the assistant refuses until next month
    await owner_conn.execute("UPDATE assistant_messages SET cost_usd = 100")
    r = await api.post(ask_url(ids), json={"question": q.text})
    assert r.status_code == 429 and r.json()["type"].endswith("assistant-budget")
    await owner_conn.execute("UPDATE assistant_messages SET cost_usd = 0")

    # not configured
    api.app.state.assistant = None
    assert (await api.post(ask_url(ids), json={"question": q.text})).status_code == 503
    api.app.state.assistant = ScriptedModel(q)
    # someone else's conversation is not found
    other = make_api()
    await setup_club(other, email="other@hc-test.ch")
    r = await other.get(f"/v1/orgs/{org}/assistant/{first['conversation_id']}")
    assert r.status_code in (403, 404)


def test_number_validator() -> None:
    allowed = numbers_from(
        {"value": 0.583, "numerator": 7, "denominator": 12, "date": "2026-10-03"}
    )
    assert invented_numbers("58 % (7 von 12) am 3.10.2026", allowed) == []
    assert invented_numbers("58,3 Prozent", allowed) == []
    assert invented_numbers("in 2 Halbzeiten und 60 Minuten", allowed) == []
    assert invented_numbers("13 Tore", allowed) == ["13"]
    assert invented_numbers("Differenz -0.2", numbers_from({"difference": -0.2})) == []
    assert Usage(1_000_000, 1_000_000).cost_usd("claude-opus-5-5") == 24.0


class _Block:
    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data

    def model_dump(self, exclude_none: bool = False) -> dict[str, Any]:
        return dict(self.data)


class _FakeMessages:
    def __init__(self, result: Any) -> None:
        self.result = result
        self.calls: list[dict[str, Any]] = []

    async def create(self, **kw: Any) -> Any:
        self.calls.append(kw)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


async def test_claude_model_request_and_errors() -> None:
    from types import SimpleNamespace

    import anthropic
    import httpx2 as httpx

    from handball_api.core.assistant_llm import MODEL, ClaudeAssistantModel
    from handball_api.services.assistant import SYSTEM, TOOLS

    usage = SimpleNamespace(
        input_tokens=100,
        output_tokens=20,
        cache_read_input_tokens=900,
        cache_creation_input_tokens=0,
    )
    response = SimpleNamespace(
        content=[_Block({"type": "tool_use", "id": "a", "name": "list_matches", "input": {}})],
        stop_reason="tool_use",
        usage=usage,
        model=MODEL,
    )
    m = ClaudeAssistantModel("sk-test")
    fake = _FakeMessages(response)
    m.client = SimpleNamespace(beta=SimpleNamespace(messages=fake))  # type: ignore[assignment]
    turn = await m.respond(SYSTEM, TOOLS, [{"role": "user", "content": "Hallo"}])
    assert turn.stop_reason == "tool_use" and turn.content[0]["name"] == "list_matches"
    assert turn.usage.cache_read_tokens == 900
    call = fake.calls[0]
    assert call["model"] == "claude-opus-5-5" and call["output_config"] == {"effort": "low"}
    assert call["fallbacks"] == "default" and call["system"][0]["cache_control"]
    assert {t["name"] for t in call["tools"]} >= {"query_events", "final_answer"}
    req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    for exc in (
        anthropic.RateLimitError("slow", response=httpx.Response(429, request=req), body=None),
        anthropic.InternalServerError("boom", response=httpx.Response(500, request=req), body=None),
        anthropic.APIConnectionError(request=req),
    ):
        m.client = SimpleNamespace(beta=SimpleNamespace(messages=_FakeMessages(exc)))  # type: ignore[assignment]
        with pytest.raises(AssistantUnavailableError):
            await m.respond(SYSTEM, TOOLS, [])


@pytest.mark.live
async def test_live_eval(make_api: Callable[[], Api], owner_conn: asyncpg.Connection) -> None:
    """The evaluation set against the real model (5.1 acceptance: >= 90 % correct, no invented
    number, answer under 8 s). Run: HB_ANTHROPIC_API_KEY=... uv run pytest -m live
    apps/api/tests/test_assistant.py. Writes docs/perf/assistant-eval.md."""
    import os
    import statistics
    from pathlib import Path

    from handball_api.core.assistant_llm import ClaudeAssistantModel

    key = os.environ.get("HB_ANTHROPIC_API_KEY")
    if not key:
        pytest.skip("HB_ANTHROPIC_API_KEY not set")
    api = make_api()
    ids = await seed(api, owner_conn)
    api.app.state.assistant = ClaudeAssistantModel(key)
    rows, latencies, cost = [], [], 0.0
    for q in QUESTIONS:
        body = (await api.post(ask_url(ids), json={"question": q.text})).json()
        ok = score(body["answer"], q)
        latencies.append(body["latency_ms"])
        rows.append((q.id, ok, body["validated"], body["status"], body["latency_ms"]))
    cost = float(await owner_conn.fetchval("SELECT sum(cost_usd) FROM assistant_messages"))
    correct = sum(1 for r in rows if r[1]) / len(rows)
    invented = sum(1 for r in rows if r[3] == "invented_numbers")
    p95 = sorted(latencies)[int(0.95 * (len(latencies) - 1))]
    lines = [
        "# Data assistant evaluation (live)",
        "",
        f"Questions: {len(rows)}, correct: {correct:.0%}, invented numbers caught: {invented}, "
        f"latency median {statistics.median(latencies) / 1000:.1f} s, p95 {p95 / 1000:.1f} s, "
        f"cost USD {cost:.2f}.",
        "",
        "| question | correct | validated | status | ms |",
        "|---|---|---|---|---|",
        *[f"| {a} | {'yes' if b else 'no'} | {c} | {d} | {e} |" for a, b, c, d, e in rows],
    ]
    out = Path(__file__).resolve().parents[3] / "docs" / "perf" / "assistant-eval.md"  # noqa: ASYNC240
    out.write_text("\n".join(lines) + "\n")
    assert correct >= 0.9 and p95 < 8000


@pytest.mark.usefixtures("recorded")
async def test_clips_only_for_moments_of_the_video(make_api: Callable[[], Api]) -> None:
    """The assistant cites clips by an event's video time. With an official report on a clip of
    five minutes from mid-half, most events lie before (negative time) or after the video: they
    used to be offered as clips that show nothing. Now they count as without video."""
    from handball_api.core.db import enable_system_access, open_session
    from handball_api.models import Team
    from handball_api.services import team_data
    from handball_api.services.context import Ctx

    from .test_official_report import reported_clip

    api = make_api()
    ids = await setup_club(api)
    m, _ = await reported_clip(api, ids)
    events = (await api.get(f"/v1/orgs/{ids['org']}/matches/{m['id']}/events")).json()
    async with open_session() as db:
        await enable_system_access(db, reason="test")
        state = api.app.state
        ctx = Ctx(db=db, settings=state.settings, email=state.email, storage=state.storage)
        team = await db.get(Team, uuid.UUID(ids["team"]))
        assert team is not None
        data = await team_data.load(ctx, team)
    for e in events:
        inside = e["t_ms"] is not None and 0 <= e["t_ms"] <= 300_000
        assert data.event_ms[e["id"]] == (e["t_ms"] if inside else None), e
    assert any(v is not None for v in data.event_ms.values())
