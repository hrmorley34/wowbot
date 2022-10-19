from __future__ import annotations

from typing import NewType

import pydantic


class BaseModel(pydantic.BaseModel):
    class Config:
        extra = pydantic.Extra.forbid


Snowflake = NewType("Snowflake", pydantic.conint(ge=0, lt=1 << 64))
