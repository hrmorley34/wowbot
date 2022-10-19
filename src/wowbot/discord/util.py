from __future__ import annotations

from typing import Any

from discord import ApplicationContext, Member
from discord.channel import VocalGuildChannel


async def respond(ctx: ApplicationContext, *args: Any, **kwargs: Any):
    await ctx.send_response(*args, ephemeral=True, delete_after=4, **kwargs)


async def err(ctx: ApplicationContext, *args: Any, **kwargs: Any):
    await respond(ctx, *args, **kwargs)


def get_voice_name(ctx: ApplicationContext, default: str) -> str:
    if (
        ctx.guild is not None
        and ctx.guild.voice_client is not None
        and isinstance(ctx.guild.voice_client.channel, VocalGuildChannel)
    ):
        return ctx.guild.voice_client.channel.name
    return default


async def join(ctx: ApplicationContext) -> bool:
    if ctx.guild is None:
        await err(ctx, "You aren't in a server!")
        return False

    if not isinstance(ctx.author, Member):
        return False

    if ctx.author.voice is None:
        await err(ctx, "You aren't in a voice chat!")
        return False

    if ctx.author.voice.channel is None:
        return False

    if ctx.guild.voice_client is None:
        await ctx.author.voice.channel.connect()
        return True
    elif ctx.guild.voice_client.channel == ctx.author.voice.channel:
        return True
    else:
        await ctx.guild.voice_client.disconnect(force=False)
        await ctx.author.voice.channel.connect()
        return True


async def leave(ctx: ApplicationContext) -> bool:
    if ctx.guild is None:
        await err(ctx, "You aren't in a server!")
        return False

    if not isinstance(ctx.author, Member):
        return False

    if ctx.author.voice is None:
        await err(ctx, "You aren't in a voice chat!")
        return False

    if ctx.author.voice.channel is None:
        return False

    if ctx.guild.voice_client is None:
        await err(ctx, "I'm not in a voice chat!")
        return False
    elif ctx.guild.voice_client.channel != ctx.author.voice.channel:
        await err(ctx, "I'm not in your voice chat!")
        return False
    else:
        await ctx.guild.voice_client.disconnect(force=False)
        return True
