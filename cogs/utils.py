from discord.ext import commands
from collections.abc import MutableMapping
from typing import Tuple, Any
from io import StringIO
import contextlib
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


class PartialContext(commands.Context):
    def __init__(self, **attrs):
        for k, v in attrs.items():
            setattr(self, k, v)

    author = None
    channel = None
    guild = None

    async def send(*args, **kwargs):
        pass


class ExpandingCodeblock:
    ctx: commands.Context
    prefix: str
    suffix: str
    maxlen: int
    _contents: list
    messages: list

    def __init__(self, ctx=None, maxlen=3000, prefix="```\n", suffix="\n```"):
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
