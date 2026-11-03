"""Paper match report and tactics board photos to data (addendum 01, 5.9).

Claude (vision) reads the photo into a flat extraction schema (structured output); the service turns
it into the paper report schema of BRIEF 15, validates sums and scores and shows everything for
review next to the photo. Fields the model is unsure about are listed in `uncertain`.
"""

from __future__ import annotations

import base64
import json
from typing import Any, Protocol

import anthropic

from handball_api.core.logging import get_logger

log = get_logger("handball_api.paper_vision")

MODEL = "claude-opus-5-5"


def _nullable(t: str) -> dict[str, Any]:
    return {"anyOf": [{"type": t}, {"type": "null"}]}


_SCORE = {
    "type": "object",
    "properties": {"own": {"type": "integer"}, "opponent": {"type": "integer"}},
    "required": ["own", "opponent"],
    "additionalProperties": False,
}

EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "readable": {"type": "boolean"},
        "date": _nullable("string"),
        "kickoff": _nullable("string"),
        "opponent": _nullable("string"),
        "home": {"type": "boolean"},
        "competition": _nullable("string"),
        "score": {"anyOf": [_SCORE, {"type": "null"}]},
        "halftime": {"anyOf": [_SCORE, {"type": "null"}]},
        "players": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "number": {"type": "integer"},
                    "name": _nullable("string"),
                    "goals": {"type": "integer"},
                    "misses": {"type": "integer"},
                    "seven_m_goals": {"type": "integer"},
                    "seven_m_misses": {"type": "integer"},
                    "suspensions": {"type": "integer"},
                    "assists": {"type": "integer"},
                },
                "required": [
                    "number",
                    "name",
                    "goals",
                    "misses",
                    "seven_m_goals",
                    "seven_m_misses",
                    "suspensions",
                    "assists",
                ],
                "additionalProperties": False,
            },
        },
        "goalkeepers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "number": {"type": "integer"},
                    "name": _nullable("string"),
                    "saves": {"type": "integer"},
                },
                "required": ["number", "name", "saves"],
                "additionalProperties": False,
            },
        },
        "score_progression": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "minute": {"type": "integer"},
                    "own": {"type": "integer"},
                    "opponent": {"type": "integer"},
                },
                "required": ["minute", "own", "opponent"],
                "additionalProperties": False,
            },
        },
        "team_goals_total": _nullable("integer"),
        "uncertain": {"type": "array", "items": {"type": "string"}},
        "notes": _nullable("string"),
    },
    "required": [
        "readable",
        "date",
        "kickoff",
        "opponent",
        "home",
        "competition",
        "score",
        "halftime",
        "players",
        "goalkeepers",
        "score_progression",
        "team_goals_total",
        "uncertain",
        "notes",
    ],
    "additionalProperties": False,
}

PROMPT = """This is a photo of a handball match report sheet (or a tactics board) kept by a club.
Read only what is written; never guess. Our team is the club's own team; "opponent" is the other
team's name. Copy numbers exactly as written. Counts not on the sheet are 0, unknown text is null.
Per player, `goals` is the player's total including 7 m goals and `seven_m_goals` the part of it
scored from 7 m (sheets often write "9 (4)" for that).
Dates as YYYY-MM-DD, kickoff as HH:MM. `team_goals_total` is the total written on the sheet for our
team's goals (null if there is none). In `uncertain`, list the fields you could not read with
certainty as paths like "players[3].goals" or "score.own". If the photo is not a match report or not
readable, set `readable` to false."""


class PaperExtractionError(Exception):
    pass


class PaperExtractor(Protocol):
    model: str

    async def extract(self, image: bytes, media_type: str) -> dict[str, Any]: ...


class ClaudePaperExtractor:
    def __init__(self, api_key: str, model: str = MODEL) -> None:
        self.model = model
        self.client = anthropic.AsyncAnthropic(api_key=api_key, timeout=90.0, max_retries=1)

    async def extract(self, image: bytes, media_type: str) -> dict[str, Any]:
        params: dict[str, Any] = {
            "model": self.model,
            "max_tokens": 16000,
            "output_config": {
                "effort": "medium",
                "format": {"type": "json_schema", "schema": EXTRACTION_SCHEMA},
            },
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": base64.standard_b64encode(image).decode(),
                            },
                        },
                        {"type": "text", "text": PROMPT},
                    ],
                }
            ],
        }
        try:
            response = await self.client.messages.create(**params)
        except anthropic.APIStatusError as exc:
            log.warning("paper_api_error", status=exc.status_code)
            raise PaperExtractionError("api_error") from exc
        except anthropic.APIConnectionError as exc:
            raise PaperExtractionError("connection") from exc
        if response.stop_reason in ("refusal", "max_tokens"):
            raise PaperExtractionError(str(response.stop_reason))
        text = next((b.text for b in response.content if b.type == "text"), "")
        try:
            data: dict[str, Any] = json.loads(text)
        except ValueError as exc:
            raise PaperExtractionError("invalid_json") from exc
        return data
