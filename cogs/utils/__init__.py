from __future__ import annotations

__all__ = [
    "Problem",
    "asyncnull",
    "JsonFileDict",
    "ExpandingCodeblock",
    "react_output",
]

import asyncio
from collections.abc import MutableMapping
import contextlib
import discord
from discord.ext import commands
import json
from typing import Any, Callable, Dict, Generator, Iterator, KeysView, Mapping, MutableSequence, Optional, Tuple, TypeVar, ValuesView

from .problem import Problem


_json_keyer: Callable[[Any], str] = str
# def _json_keyer(key: Any) -> str:
#     return next(iter(json.loads(json.dumps({key: 0})).keys()))


KT = TypeVar("KT")
VT = TypeVar("VT")


class JsonFileDict(MutableMapping[KT, VT]):
    def __init__(self, file: str):
        self.file = file

    def __repr__(self) -> str:
        return "<{} file={}>".format(type(self).__name__, self.file)

    def _load(self) -> Dict[str, VT]:
        try:
            with open(self.file, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return dict()

    def _raw(self) -> Optional[str]:
        try:
            with open(self.file, "r") as f:
                return f.read()
        except FileNotFoundError:
            return None

    @contextlib.contextmanager
    def _writer(self) -> Generator[Tuple[Dict[str, VT], Callable[[Mapping[str, VT]], None]], None, None]:
        with open(self.file, "r+") as f:
            data: Dict[str, VT] = json.load(f)

            def dump(data: Mapping[str, VT], **kwargs):
                f.seek(0)
                json.dump(data, f, **kwargs)
                f.truncate()

            yield data, dump

    def keys(self) -> KeysView[str]:
        return self._load().keys()

    def values(self) -> ValuesView[VT]:
        return self._load().values()

    def __len__(self) -> int:
        return len(self._load())

    def __iter__(self) -> Iterator[str]:
        return iter(self._load().keys())

    def __getitem__(self, key: KT) -> VT:
        k = _json_keyer(key)
        return self._load()[k]

    def __setitem__(self, key: KT, value: VT):
        k = _json_keyer(key)
        with self._writer() as (data, dump):
            data[k] = value
            dump(data)

    def __delitem__(self, key: KT):
        k = _json_keyer(key)
        with self._writer() as (data, dump):
            del data[k]
            dump(data)


async def asyncnull(*args, **kwargs):
    pass


class ExpandingCodeblock:
    ctx: Optional[commands.Context]
    prefix: str
    suffix: str
    maxlen: int
    _contents: MutableSequence[str]
    messages: MutableSequence[discord.Message]

    def __init__(self, ctx: Optional[commands.Context] = None, maxlen: int = 1800, prefix: str = "```\n", suffix: str = "\n```"):
        self.ctx = ctx
        self.prefix = prefix
        self.suffix = suffix
        self.maxlen = maxlen
        self._contents = []
        self.messages = []

    def append(self, text: str):
        if len(self._contents) <= 0:
            self._contents.append("")

        for line in text.splitlines(True):
            if len(self._contents[-1]) + len(line) > self.maxlen:
                self._contents.append(line)
            else:
                self._contents[-1] += line

    def content_to_message_args(self, content: str, edit: bool = False) -> Mapping[str, Any]:
        return {"content": self.prefix + content.strip("\n") + self.suffix}
        # Could instead return {"embed": discord.Embed(...)}

    async def update_messages(self, ctx: Optional[commands.Context] = None):
        ctx = ctx or self.ctx
        if ctx is None:
            raise TypeError("No context supplied")

        start = max(len(self.messages) - 1, 0)  # last item index
        for i, cont in enumerate(self._contents[start:], start):
            if i < len(self.messages):
                await self.messages[i].edit(**self.content_to_message_args(cont, edit=True))
            else:
                m = await ctx.send(**self.content_to_message_args(cont, edit=False))
                self.messages.append(m)


async def _react_output(bot: discord.Client, message: discord.Message, emoji, wait: int):
    try:
        await message.add_reaction(emoji)
    except discord.Forbidden:
        pass  # it doesn't matter too much
    else:
        if wait is not None and wait >= 0:
            await asyncio.sleep(wait)
            await message.remove_reaction(emoji, bot.user)


async def react_output(bot: discord.Client, message: discord.Message, success: bool = True, emoji=None, wait: int = 4):
    " React to a message, and then retract the reaction "
    if emoji is None:
        if success:
            emoji = "\u2705"  # \N{White heavy check mark}
        else:
            emoji = "\u274C"  # \N{Cross mark}
    # schedule in the background
    return asyncio.create_task(_react_output(bot, message, emoji, wait))
