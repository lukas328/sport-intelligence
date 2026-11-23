from __future__ import annotations

import re
from typing import Annotated

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, StringConstraints

HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


def _hex(v: str) -> str:
    if not HEX_COLOR.match(v):
        raise ValueError("must be a hex colour like #0b6bcb")
    return v.lower()


HexColor = Annotated[str, AfterValidator(_hex)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]

_SOURCE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,39}$")


def _source(value: object) -> str | None:
    # a place on the website (`?src=hero`): anything else is dropped, never a reason to refuse a
    # sign-up
    if not isinstance(value, str):
        return None
    cleaned = value.strip().lower()
    return cleaned if _SOURCE.match(cleaned) else None


SignupSource = Annotated[str | None, BeforeValidator(_source)]
ShortName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
