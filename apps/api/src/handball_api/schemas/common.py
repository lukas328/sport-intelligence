from __future__ import annotations

import re
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, StringConstraints

HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


def _hex(v: str) -> str:
    if not HEX_COLOR.match(v):
        raise ValueError("must be a hex colour like #0b6bcb")
    return v.lower()


HexColor = Annotated[str, AfterValidator(_hex)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
ShortName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
