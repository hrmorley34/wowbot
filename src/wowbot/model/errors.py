from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, ClassVar, Generator, Generic, List, Tuple, TypeVar, Union

ContextItem = Union[str, int]
Context = Tuple[ContextItem, ...]


_context: ContextVar[Context | None] = ContextVar("_context", default=None)


class BaseModelError(Exception):
    """The base error which other resolution errors inherit"""

    pass


class ContextModelError(BaseModelError):
    """The base error for resolution errors with a context

    Context can be used to represent the location in a model tree.

    .. autoattribute:: context
    """

    context: Context | None
    """The position in the data of the error"""

    _var: ClassVar[ContextVar[Context | None]] = _context
    """The ContextVar to read contexts from"""

    def __init_subclass__(
        cls, var: ContextVar[Context | None] | None = None, **kwargs: Any
    ) -> None:
        if var is not None:
            cls._var = var
        return super().__init_subclass__(**kwargs)

    def __init__(self, *args: object) -> None:
        self.context = self._var.get()
        super().__init__(*args)


ExcT = TypeVar("ExcT", bound=Exception)


class ErrorCollection(BaseModelError, Generic[ExcT]):
    """Error representing multiple other errors

    If only one Exception is passed, it is returned directly, rather than returned

    .. autoattribute:: errors
    """

    errors: List[ExcT]
    """The collection of errors"""

    def __new__(cls, *args: ExcT | ErrorCollection[ExcT]):
        if len(args) == 1 and not isinstance(args[0], ErrorCollection):
            return args[0]
        return super().__new__(cls)

    def __init__(self, *args: ExcT | ErrorCollection[ExcT]) -> None:
        self.errors: List[ExcT] = []
        for arg in args:
            if isinstance(arg, ErrorCollection):
                self.errors.extend(arg.errors)  # type: ignore
            else:
                self.errors.append(arg)
        error_text = "error" if len(args) == 1 else "errors"
        super().__init__(f"{len(args)} {error_text}", *self.errors)


class ContextFactory:
    """A container of context variables

    This is used to store the current location in a model tree.

    .. automethod:: get_context
    .. automethod:: context
    """

    def __init__(self, var: ContextVar[Context | None]) -> None:
        self._var = var

    def get_context(self) -> Context | None:
        """Get the current context"""
        return self._var.get()

    @contextmanager
    def context(
        self, *values: ContextItem, base: Context | None = None
    ) -> Generator[Context, None, None]:
        """Enter the given context"""
        if base is None:
            base = self._var.get()
            if base is None:
                base = ()
        new_value = base + values
        token = self._var.set(new_value)
        try:
            yield new_value
        finally:
            self._var.reset(token)


contextvar = ContextFactory(_context)
context = contextvar.context
