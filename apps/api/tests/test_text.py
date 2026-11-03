from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import anthropic
import httpx2 as httpx
import pytest

from handball_api.core.text import MODEL, ClaudeTextGenerator


class FakeMessages:
    def __init__(self, result: Any) -> None:
        self.result = result
        self.calls: list[dict[str, Any]] = []

    async def create(self, **kw: Any) -> Any:
        self.calls.append(kw)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def gen(result: Any) -> tuple[ClaudeTextGenerator, FakeMessages]:
    g = ClaudeTextGenerator("sk-test")
    fake = FakeMessages(result)
    g.client = SimpleNamespace(beta=SimpleNamespace(messages=fake))  # type: ignore[assignment]
    return g, fake


def msg(stop: str, text: str = "") -> Any:
    return SimpleNamespace(
        stop_reason=stop, content=[SimpleNamespace(type="text", text=text)] if text else []
    )


async def test_summarise_request_and_text() -> None:
    g, fake = gen(msg("end_turn", " Gute Abwehr. "))
    assert await g.summarise({"erkenntnisse": []}) == "Gute Abwehr."
    call = fake.calls[0]
    assert call["model"] == MODEL == "claude-opus-5-5"
    assert call["fallbacks"] == "default"
    assert call["betas"] == ["server-side-fallback-2026-07-01"]
    assert "Fakten (JSON)" in call["messages"][0]["content"]


@pytest.mark.parametrize("stop", ["refusal", "max_tokens"])
async def test_stops_give_none(stop: str) -> None:
    g, _ = gen(msg(stop, "x"))
    assert await g.summarise({}) is None
    g, _ = gen(msg("end_turn"))
    assert await g.summarise({}) is None


async def test_api_errors_give_none() -> None:
    req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    for exc in (
        anthropic.RateLimitError("slow", response=httpx.Response(429, request=req), body=None),
        anthropic.InternalServerError("boom", response=httpx.Response(500, request=req), body=None),
        anthropic.APIConnectionError(request=req),
    ):
        g, _ = gen(exc)
        assert await g.summarise({}) is None
