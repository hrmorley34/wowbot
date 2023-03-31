from typing import Optional, Tuple, Union

from pydantic import ValidationError

Location = Tuple[Union[str, int], ...]
PartialLocation = Optional[Tuple[Union[str, int, None], ...]]


def compare_locations(loc: Location, loc2: PartialLocation) -> bool:
    if loc2 is None:
        return True
    if len(loc) != len(loc2):
        return False
    for c, c2 in zip(loc, loc2):
        if c2 is not None and c != c2:
            return False
    return True


def any_validation_error(
    error: ValidationError,
    *,
    loc: PartialLocation = None,
    type: Optional[str] = None,
) -> bool:
    for err in error.errors():
        if compare_locations(err["loc"], loc) and (type is None or err["type"] == type):
            return True
    return False
