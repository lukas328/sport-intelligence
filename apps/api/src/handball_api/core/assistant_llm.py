"""Model access for the data assistant (addendum 01, 5.1).

The model plans which typed tools to call and phrases the answer; every number comes from a tool
result. `numbers_from` collects the numbers a tool result contains (including percentages of
ratios) and `invented_numbers` lists the numbers of an answer that no tool returned. The API
rejects such answers (P3).
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any, Protocol

import anthropic

from handball_api.core.logging import get_logger

log = get_logger("handball_api.assistant")

MODEL = "claude-opus-5-5"
# list prices in USD per million tokens (input, output, cache read, cache write)
PRICES_USD = {MODEL: (4.0, 20.0, 0.20, 5.0)}
_NUM = re.compile(r"(?<![\w.])-?\d+(?:[.,]\d+)?")


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

    def add(self, other: Usage) -> None:
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.cache_read_tokens += other.cache_read_tokens
        self.cache_write_tokens += other.cache_write_tokens

    def cost_usd(self, model: str) -> float:
        i, o, cr, cw = PRICES_USD.get(model, PRICES_USD[MODEL])
        return (
            self.input_tokens * i
            + self.output_tokens * o
            + self.cache_read_tokens * cr
            + self.cache_write_tokens * cw
        ) / 1_000_000


@dataclass
class ModelTurn:
    content: list[dict[str, Any]]  # API content blocks, replayed unchanged on the next request
    stop_reason: str | None
    usage: Usage = field(default_factory=Usage)
    model: str = MODEL
    latency_ms: int = 0


class AssistantUnavailableError(Exception):
    """The model could not be reached or declined; the caller answers without it."""


class AssistantModel(Protocol):
    model: str

    async def respond(
        self, system: str, tools: list[dict[str, Any]], messages: list[dict[str, Any]]
    ) -> ModelTurn: ...


class ClaudeAssistantModel:
    def __init__(self, api_key: str, model: str = MODEL) -> None:
        self.model = model
        self.client = anthropic.AsyncAnthropic(api_key=api_key, timeout=30.0, max_retries=1)

    async def respond(
        self, system: str, tools: list[dict[str, Any]], messages: list[dict[str, Any]]
    ) -> ModelTurn:
        start = time.monotonic()
        try:
            params: dict[str, Any] = {
                "model": self.model,
                "max_tokens": 16000,
                # stable prefix (tools + system) is cached across questions
                "system": [
                    {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
                ],
                "tools": tools,
                "messages": messages,
                # chat latency matters more than depth; the tools do the arithmetic
                "output_config": {"effort": "low"},
                # policy declines are retried on a fallback model chosen by the API
                "betas": ["server-side-fallback-2026-07-01"],
                "fallbacks": "default",
            }
            response = await self.client.beta.messages.create(**params)
        except anthropic.RateLimitError as exc:
            log.warning("assistant_rate_limited")
            raise AssistantUnavailableError("rate_limited") from exc
        except anthropic.APIStatusError as exc:
            log.warning("assistant_api_error", status=exc.status_code)
            raise AssistantUnavailableError("api_error") from exc
        except anthropic.APIConnectionError as exc:
            log.warning("assistant_connection_error")
            raise AssistantUnavailableError("connection") from exc
        u = response.usage
        return ModelTurn(
            content=[b.model_dump(exclude_none=True) for b in response.content],
            stop_reason=response.stop_reason,
            usage=Usage(
                input_tokens=u.input_tokens,
                output_tokens=u.output_tokens,
                cache_read_tokens=u.cache_read_input_tokens or 0,
                cache_write_tokens=u.cache_creation_input_tokens or 0,
            ),
            model=response.model,
            latency_ms=round((time.monotonic() - start) * 1000),
        )


# ---- number validator --------------------------------------------------------------------------


def _parse(raw: str) -> float:
    return float(raw.replace(",", "."))


def numbers_from(value: Any, out: set[float] | None = None) -> set[float]:
    """All numbers of a tool result. Ratios (0..1) also count as percentages, rounded like a text
    would round them (0.583 allows 58 and 58.3); every number also counts rounded to 0 and 1
    decimals."""
    out = set() if out is None else out
    if isinstance(value, bool) or value is None:
        return out
    if isinstance(value, int | float):
        v = abs(float(value))
        out |= {v, round(v), round(v, 1)}
        if v <= 1:
            out |= {round(v * 100), round(v * 100, 1)}
    elif isinstance(value, str):
        for raw in _NUM.findall(value):
            numbers_from(_parse(raw), out)
    elif isinstance(value, dict):
        for v in value.values():
            numbers_from(v, out)
    elif isinstance(value, list | tuple):
        for v in value:
            numbers_from(v, out)
    return out


# Counting words and the match length are fine without a tool ("2 Halbzeiten", "60 Minuten").
_FREE = {0.0, 1.0, 2.0, 60.0}


_DATE = re.compile(r"(?<![\w.])(\d{1,2})\.(\d{1,2})\.(\d{4})?(?!\d)")


def invented_numbers(text: str, allowed: set[float]) -> list[str]:
    bad = []
    # dates like 3.10.2026 or 3.10.: day, month and year must each come from a result
    for m in _DATE.finditer(text):
        for part in m.groups():
            if part is not None and float(part) not in allowed and float(part) not in _FREE:
                bad.append(m.group(0))
                break
    text = _DATE.sub(" ", text)
    for raw in _NUM.findall(text):
        v = abs(_parse(raw))
        if v in _FREE or v in allowed or round(v, 1) in allowed:
            continue
        bad.append(raw)
    return bad
