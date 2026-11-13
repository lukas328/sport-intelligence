"""Calendar and team organisation: ICS import/export (RFC 5545 subset), Spond/ClubCorner stubs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Protocol
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from handball_api.integrations.base import AdapterError, Stub


@dataclass(frozen=True)
class CalendarEntry:
    uid: str
    title: str
    starts_at: datetime | date
    ends_at: datetime | date | None = None
    location: str | None = None
    description: str | None = None


class TeamOpsAdapter(Protocol):
    name: str

    def import_events(self, source: str) -> list[CalendarEntry]: ...
    def export_events(self, entries: list[CalendarEntry], name: str) -> str: ...


def _unfold(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.replace("\r\n", "\n").split("\n"):
        if raw[:1] in (" ", "\t") and lines:
            lines[-1] += raw[1:]
        elif raw:
            lines.append(raw)
    return lines


def _unescape(v: str) -> str:
    return (
        v.replace("\\n", "\n").replace("\\N", "\n").replace("\\,", ",").replace(r"\;", ";")
    ).replace("\\\\", "\\")


def _escape(v: str) -> str:
    return v.replace("\\", "\\\\").replace(";", r"\;").replace(",", "\\,").replace("\n", "\\n")


def _parse_dt(value: str, params: dict[str, str]) -> datetime | date:
    try:
        if params.get("VALUE") == "DATE" or len(value) == 8:
            return datetime.strptime(value, "%Y%m%d").date()
        if value.endswith("Z"):
            return datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
        dt = datetime.strptime(value, "%Y%m%dT%H%M%S")
    except ValueError as exc:
        raise AdapterError(f"Invalid date {value}") from exc
    try:
        return dt.replace(tzinfo=ZoneInfo(params.get("TZID", "Europe/Zurich")))
    except ZoneInfoNotFoundError:
        return dt.replace(tzinfo=ZoneInfo("Europe/Zurich"))


def _fold(line: str) -> str:
    out, chunk = [], line
    while len(chunk.encode()) > 75:
        cut = 74
        while len(chunk[:cut].encode()) > 74:
            cut -= 1
        out.append(chunk[:cut])
        chunk = " " + chunk[cut:]
    out.append(chunk)
    return "\r\n".join(out)


def _fmt(v: datetime | date) -> str:
    if isinstance(v, datetime):
        return v.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
    return v.strftime("%Y%m%d")


class IcsTeamOps:
    name = "ics"

    def import_events(self, source: str) -> list[CalendarEntry]:
        if "BEGIN:VCALENDAR" not in source:
            raise AdapterError("Not an ICS calendar")
        entries: list[CalendarEntry] = []
        cur: dict[str, tuple[str, dict[str, str]]] | None = None
        for line in _unfold(source):
            if line == "BEGIN:VEVENT":
                cur = {}
                continue
            if line == "END:VEVENT" and cur is not None:
                if "DTSTART" in cur:
                    start = _parse_dt(*cur["DTSTART"])
                    end = _parse_dt(*cur["DTEND"]) if "DTEND" in cur else None
                    entries.append(
                        CalendarEntry(
                            uid=cur.get("UID", ("", {}))[0] or f"no-uid-{len(entries)}",
                            title=_unescape(cur.get("SUMMARY", ("", {}))[0]),
                            starts_at=start,
                            ends_at=end,
                            location=_unescape(cur["LOCATION"][0]) if "LOCATION" in cur else None,
                            description=_unescape(cur["DESCRIPTION"][0])
                            if "DESCRIPTION" in cur
                            else None,
                        )
                    )
                cur = None
                continue
            if cur is None or ":" not in line:
                continue
            head, value = line.split(":", 1)
            name, *raw_params = head.split(";")
            params = dict(p.split("=", 1) for p in raw_params if "=" in p)
            cur[name.upper()] = (value, params)
        return sorted(entries, key=lambda e: _fmt(e.starts_at))

    def export_events(self, entries: list[CalendarEntry], name: str) -> str:
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Handball Intelligence//Team calendar//DE",
            f"X-WR-CALNAME:{_escape(name)}",
        ]
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        for e in entries:
            lines += ["BEGIN:VEVENT", f"UID:{e.uid}", f"DTSTAMP:{stamp}"]
            date_only = not isinstance(e.starts_at, datetime)
            lines.append(
                f"DTSTART;VALUE=DATE:{_fmt(e.starts_at)}"
                if date_only
                else f"DTSTART:{_fmt(e.starts_at)}"
            )
            if e.ends_at is not None:
                lines.append(
                    f"DTEND;VALUE=DATE:{_fmt(e.ends_at)}"
                    if date_only
                    else f"DTEND:{_fmt(e.ends_at)}"
                )
            lines.append(f"SUMMARY:{_escape(e.title)}")
            if e.location:
                lines.append(f"LOCATION:{_escape(e.location)}")
            if e.description:
                lines.append(f"DESCRIPTION:{_escape(e.description)}")
            lines.append("END:VEVENT")
        lines.append("END:VCALENDAR")
        return "\r\n".join(_fold(line) for line in lines) + "\r\n"


class _TeamOpsStub(Stub):
    name = "team_ops"

    def import_events(self, source: str) -> list[CalendarEntry]:
        raise self._missing()

    def export_events(self, entries: list[CalendarEntry], name: str) -> str:
        raise self._missing()


class SpondTeamOps(_TeamOpsStub):
    name = partner = "spond"


class ClubCornerTeamOps(_TeamOpsStub):
    name = partner = "clubcorner"
