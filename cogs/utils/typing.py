from typing import Any, Dict, List, TypedDict


class SoundPath(TypedDict, total=False):
    glob: str
    filenames: List[str]
    filename: str
    weight: int


class SoundDef(TypedDict, total=False):
    files: List[SoundPath]

    description: str
    aliases: List[str]
    slash: bool
    slash_name: str
    slash_group: str

    commandkwargs: Dict[str, Any]


SOUNDS_JSON = Dict[str, SoundDef]


class ReactionGuild(TypedDict, total=True):
    channel: int
    message: int
