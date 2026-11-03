"""Natural-language match summaries (BRIEF 4.9 "TextGenerator", M7).

The model only rewords facts we computed: it receives the ranked insights as structured facts (no
player names, only jersey numbers) and must not invent numbers. `numbers_ok` rejects any text that
contains a number not present in the facts; the caller then falls back to the UI template text.
"""

from __future__ import annotations

import json
import re
from typing import Any, Protocol

import anthropic

from handball_api.core.logging import get_logger

log = get_logger("handball_api.text")

MODEL = "claude-opus-5-5"
SYSTEM = (
    "Du schreibst kurze Spielanalysen für Handballtrainerinnen und -trainer in der Schweiz. "
    "Schreibe auf Deutsch (Schweiz, kein Eszett, schreibe ss), sachlich, in 3 bis 5 Sätzen, ohne "
    "Aufzählungszeichen und ohne lange Gedankenstriche. Verwende ausschliesslich die Zahlen "
    "aus den Fakten, genau so wie sie dort stehen, und erfinde nichts dazu. "
    "Spieler nennst du nur mit "
    "Rückennummer (zum Beispiel Nr. 7). Beginne mit dem wichtigsten Punkt und ende mit einem "
    "konkreten Trainingshinweis, der sich direkt aus den Fakten ergibt."
)
_NUM = re.compile(r"\d+(?:[.,]\d+)?")


class TextGenerator(Protocol):
    model: str

    async def summarise(self, facts: dict[str, Any]) -> str | None: ...


def numbers_ok(text: str, allowed: set[float]) -> bool:
    """Every number in the text must be one of the fact numbers (1 and 2 aside: counting words)."""
    for raw in _NUM.findall(text):
        value = float(raw.replace(",", "."))
        if value in allowed or value in (1, 2):
            continue
        return False
    return True


class ClaudeTextGenerator:
    def __init__(self, api_key: str, model: str = MODEL) -> None:
        self.model = model
        self.client = anthropic.AsyncAnthropic(api_key=api_key, timeout=60.0, max_retries=2)

    async def summarise(self, facts: dict[str, Any]) -> str | None:
        try:
            response = await self.client.beta.messages.create(
                model=self.model,
                max_tokens=2000,
                system=SYSTEM,
                output_config={"effort": "low"},
                # policy declines are retried on a fallback model chosen by the API
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
                messages=[
                    {
                        "role": "user",
                        "content": "Fakten (JSON):\n"
                        + json.dumps(facts, ensure_ascii=False, sort_keys=True),
                    }
                ],
            )
        except anthropic.RateLimitError:
            log.warning("summary_rate_limited")
            return None
        except anthropic.APIStatusError as exc:
            log.warning("summary_api_error", status=exc.status_code)
            return None
        except anthropic.APIConnectionError:
            log.warning("summary_connection_error")
            return None
        if response.stop_reason in ("refusal", "max_tokens"):
            log.warning("summary_stopped", reason=response.stop_reason)
            return None
        text = "".join(b.text for b in response.content if b.type == "text").strip()
        return text or None
