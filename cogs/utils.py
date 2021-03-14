import discord
from discord.ext import commands
from collections.abc import MutableMapping
from typing import Tuple, Any
from io import StringIO
import contextlib
import asyncio
from typing import Optional
import json


def _json_keyer(key):
    return next(iter(json.loads(json.dumps({key: 0})).keys()))


class JsonFileDict(MutableMapping):
    def __init__(self, file: str):
        self.file = file

    def __repr__(self):
        return "<{} file={}>".format(type(self).__name__, self.file)

    def _load(self) -> dict:
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
    def _writer(self) -> Tuple[dict, StringIO]:
        with open(self.file, "r+") as f:
            data = json.load(f)

            def dump(data: dict, **kwargs):
                f.seek(0)
                json.dump(data, f)
                f.truncate()

            yield data, dump

    def keys(self):
        return self._load().keys()

    def values(self):
        return self._load().values()

    def __len__(self):
        return len(self._load())

    def __iter__(self):
        return iter(self._load().keys())

    def __getitem__(self, key) -> Any:
        key = _json_keyer(key)
        return self._load()[key]

    def __setitem__(self, key, value: Any):
        key = _json_keyer(key)
        with self._writer() as (data, dump):
            data[key] = value
            dump(data)

    def __delitem__(self, key):
        key = _json_keyer(key)
        with self._writer() as (data, dump):
            del data[key]
            dump(data)


async def asyncnull(*args, **kwargs):
    pass


class PartialContext(commands.Context):
    _attrs = {}

    def __getattribute__(self, k):
        if k[0] == "_":
            return super().__getattribute__(k)
        elif k in self._attrs:
            return self._attrs[k]
        else:
            return super().__getattribute__(k)

    def __init__(self, **attrs):
        self._attrs = attrs


class ExpandingCodeblock:
    ctx: commands.Context
    prefix: str
    suffix: str
    maxlen: int
    _contents: list
    messages: list

    def __init__(self, ctx=None, maxlen=1800, prefix="```\n", suffix="\n```"):
        self.ctx = ctx
        self.prefix = prefix
        self.suffix = suffix
        self.maxlen = maxlen
        self._contents = []
        self.messages = []

    def append(self, text):
        if len(self._contents) <= 0:
            self._contents.append("")

        for line in text.splitlines(True):
            if len(self._contents[-1]) + len(line) > self.maxlen:
                self._contents.append(line)
            else:
                self._contents[-1] += line

    def content_to_message_args(self, content: str, edit=False) -> dict:
        return {"content": self.prefix + content.strip("\n") + self.suffix}
        # Could instead return {"embed": discord.Embed(...)}

    async def update_messages(self, ctx=None):
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


async def _react_output(bot, message, emoji, wait):
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


class Problem(commands.CommandError):
    pass
