from __future__ import annotations

from enum import StrEnum

from sqlalchemy import Enum


def str_enum(enum: type[StrEnum], length: int = 20) -> Enum:
    """Enum stored as VARCHAR + CHECK (no native PG enum: easier migrations)."""
    return Enum(
        enum,
        native_enum=False,
        length=length,
        values_callable=lambda e: [m.value for m in e],
        validate_strings=True,
        create_constraint=True,
    )
