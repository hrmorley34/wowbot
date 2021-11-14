from typing import TypedDict


class ReactionGuild(TypedDict, total=True):
    channel: int
    message: int
