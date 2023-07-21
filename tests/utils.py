from typing import Optional, Set, Tuple, Union

from pydantic import ValidationError

Location = Tuple[Union[str, int], ...]


class UnionMember:
    values: Optional[Set[str]]

    def __init__(self, value: Optional[Union[Set[str], str, type]] = None) -> None:
        if value is None:
            self.values = None
        elif isinstance(value, str):
            self.values = {value}
        elif isinstance(value, type):
            self.values = {value.__name__}
        else:
            self.values = set(value)

    def check(self, value: Union[str, int]) -> bool:
        return self.values is None or value in self.values


PartialLocation = Optional[Tuple[Union[str, int, UnionMember, None], ...]]


def filter_location(loc: PartialLocation) -> Location:
    if loc is None or None in loc:
        raise ValueError
    return tuple(m for m in loc if m is not None and not isinstance(m, UnionMember))


def compare_locations(loc: Location, loc2: PartialLocation) -> bool:
    if loc2 is None:
        return True
    if len(loc) != len(loc2):
        return False
    for c, c2 in zip(loc, loc2):
        if c2 is None:
            continue
        elif isinstance(c2, UnionMember):
            if not c2.check(c):
                return False
        elif c != c2:
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
