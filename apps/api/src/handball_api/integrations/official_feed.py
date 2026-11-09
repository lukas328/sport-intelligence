"""Official match data (BRIEF 7.4): CSV and JSON feeds, handball.ch stub."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from typing import Any, Protocol

from handball_api.core import clock
from handball_api.integrations.base import AdapterError, Stub

TYPES = {"goal", "miss", "save", "7m_goal", "7m_miss", "2min", "yellow", "red", "timeout"}


@dataclass(frozen=True)
class FeedEvent:
    period: int
    clock_s: float
    side: str  # own | opponent
    kind: str
    number: int | None


class OfficialMatchFeed(Protocol):
    name: str

    def events(self, payload: str) -> list[FeedEvent]: ...


def parse_clock(value: str) -> float:
    """The game clock of a feed row ("mm:ss" or seconds, core.clock), AdapterError if invalid."""
    try:
        return clock.parse_clock(value)
    except ValueError as exc:
        raise AdapterError(f"Invalid clock {value!r}") from exc


def _event(row: dict[str, Any], line: int) -> FeedEvent:
    side = str(row.get("team", "")).strip().lower()
    kind = str(row.get("event", "")).strip().lower()
    if side not in ("own", "opponent"):
        raise AdapterError(f"Row {line}: team must be own or opponent")
    if kind not in TYPES:
        raise AdapterError(f"Row {line}: unknown event {kind!r}")
    number = str(row.get("number") or "").strip()
    return FeedEvent(
        period=int(row.get("period") or 1),
        clock_s=parse_clock(str(row.get("clock", "0"))),
        side=side,
        kind=kind,
        number=int(number) if number.isdigit() else None,
    )


class CsvFeed:
    name = "csv"

    def events(self, payload: str) -> list[FeedEvent]:
        dialect = csv.Sniffer().sniff(payload.splitlines()[0], delimiters=",;\t")
        reader = csv.DictReader(io.StringIO(payload), dialect=dialect)
        return [_event(r, i + 2) for i, r in enumerate(reader)]


class JsonFeed:
    name = "json"

    def events(self, payload: str) -> list[FeedEvent]:
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise AdapterError("Invalid JSON") from exc
        rows = data.get("events", data) if isinstance(data, dict) else data
        if not isinstance(rows, list):
            raise AdapterError("Expected a list of events")
        return [_event(r, i + 1) for i, r in enumerate(rows)]


class HandballChFeed(Stub):
    name = partner = "handball_ch"

    def events(self, payload: str) -> list[FeedEvent]:
        raise self._missing()
