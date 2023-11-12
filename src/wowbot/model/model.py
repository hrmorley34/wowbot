from __future__ import annotations

from typing import TYPE_CHECKING, Generic, NewType, TypeVar

import pydantic

T = TypeVar("T")


class BaseModel(pydantic.BaseModel):
    model_config = {"extra": "forbid"}


class RootModel(BaseModel, pydantic.RootModel[T], Generic[T]):
    model_config = {"extra": None}  # `extra` not allowed for `RootModel`


if TYPE_CHECKING:
    Int64 = int
else:
    Int64 = pydantic.conint(ge=0, lt=1 << 64)
Snowflake = NewType("Snowflake", Int64)
