from __future__ import annotations

from typing import TYPE_CHECKING, NewType

import pydantic


class BaseModel(pydantic.BaseModel):
    model_config = {"extra": "forbid"}


if TYPE_CHECKING:
    Int64 = int
else:
    Int64 = pydantic.conint(ge=0, lt=1 << 64)
Snowflake = NewType("Snowflake", Int64)
