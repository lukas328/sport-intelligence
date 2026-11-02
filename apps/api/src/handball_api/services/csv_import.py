"""Roster CSV import (BRIEF 11.1). Tolerant to Excel exports: ; or , and UTF-8 (BOM) or Latin-1."""

from __future__ import annotations

import csv
import io
from typing import Any

from pydantic import ValidationError

from handball_api.schemas.roster import ImportRowError, RosterEntryCreate

MAX_ROWS = 200
MAX_BYTES = 200_000

HEADERS: dict[str, str] = {
    "vorname": "first_name",
    "first_name": "first_name",
    "firstname": "first_name",
    "prénom": "first_name",
    "prenom": "first_name",
    "nachname": "last_name",
    "name": "last_name",
    "last_name": "last_name",
    "lastname": "last_name",
    "nom": "last_name",
    "nummer": "jersey_number",
    "nr": "jersey_number",
    "rückennummer": "jersey_number",
    "number": "jersey_number",
    "jersey_number": "jersey_number",
    "numéro": "jersey_number",
    "numero": "jersey_number",
    "position": "main_position",
    "hauptposition": "main_position",
    "main_position": "main_position",
    "nebenpositionen": "secondary_positions",
    "secondary_positions": "secondary_positions",
    "wurfhand": "shooting_hand",
    "hand": "shooting_hand",
    "shooting_hand": "shooting_hand",
    "jahrgang": "birth_year",
    "geburtsjahr": "birth_year",
    "birth_year": "birth_year",
    "année": "birth_year",
}

POSITION_ALIASES = {
    "linksaussen": "LA",
    "rückraum links": "RL",
    "rueckraum links": "RL",
    "rückraum mitte": "RM",
    "mitte": "RM",
    "rückraum rechts": "RR",
    "rechtsaussen": "RA",
    "kreis": "KM",
    "kreisläufer": "KM",
    "kreismitte": "KM",
    "torhüter": "TW",
    "tor": "TW",
    "gk": "TW",
}

HAND_ALIASES = {
    "l": "left",
    "links": "left",
    "left": "left",
    "gauche": "left",
    "r": "right",
    "rechts": "right",
    "right": "right",
    "droite": "right",
}


def decode(data: bytes) -> str:
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1")


def _position(v: str) -> str:
    v = v.strip()
    return POSITION_ALIASES.get(v.lower(), v.upper())


def _row_to_payload(raw: dict[str, str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in raw.items():
        field = HEADERS.get((key or "").strip().lower())
        if field is None or value is None:
            continue
        value = value.strip()
        if value == "":
            continue
        if field == "main_position":
            out[field] = _position(value)
        elif field == "secondary_positions":
            out[field] = [
                _position(p)
                for p in value.replace("/", ",").replace("|", ",").split(",")
                if p.strip()
            ]
        elif field == "shooting_hand":
            out[field] = HAND_ALIASES.get(value.lower(), value)
        else:
            out[field] = value
    return out


def parse_roster_csv(data: bytes) -> tuple[list[RosterEntryCreate], list[ImportRowError]]:
    if len(data) > MAX_BYTES:
        return [], [ImportRowError(row=0, field=None, message="File is too large (max 200 kB)")]
    text = decode(data)
    try:
        dialect = csv.Sniffer().sniff(text.splitlines()[0] if text else "", delimiters=";,\t")
        delimiter = dialect.delimiter
    except csv.Error:
        delimiter = ";"
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    fields = {HEADERS.get((h or "").strip().lower()) for h in reader.fieldnames or []}
    if not {"first_name", "last_name"} <= fields:
        return [], [
            ImportRowError(
                row=1,
                field=None,
                message="Header needs columns Vorname and Nachname (first_name, last_name)",
            )
        ]
    rows: list[RosterEntryCreate] = []
    errors: list[ImportRowError] = []
    numbers: dict[int, int] = {}
    for i, raw in enumerate(reader, start=2):
        if i - 1 > MAX_ROWS:
            errors.append(ImportRowError(row=i, field=None, message=f"At most {MAX_ROWS} rows"))
            break
        if not any((v or "").strip() for v in raw.values() if isinstance(v, str)):
            continue
        try:
            entry = RosterEntryCreate.model_validate(_row_to_payload(raw))
        except ValidationError as exc:
            for err in exc.errors():
                loc = err.get("loc", ())
                errors.append(
                    ImportRowError(row=i, field=str(loc[0]) if loc else None, message=err["msg"])
                )
            continue
        if entry.jersey_number is not None:
            if entry.jersey_number in numbers:
                errors.append(
                    ImportRowError(
                        row=i,
                        field="jersey_number",
                        message=(
                            f"Number {entry.jersey_number} already used "
                            f"in row {numbers[entry.jersey_number]}"
                        ),
                    )
                )
                continue
            numbers[entry.jersey_number] = i
        rows.append(entry)
    return rows, errors
