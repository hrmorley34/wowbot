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
