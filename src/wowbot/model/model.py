from __future__ import annotations

from typing import NewType

import pydantic


class BaseModel(pydantic.BaseModel):
    pass


Snowflake = NewType("Snowflake", pydantic.conint(ge=0, lt=1 << 64))
