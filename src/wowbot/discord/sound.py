from __future__ import annotations

from discord import ApplicationContext, FFmpegOpusAudio, VoiceClient

from ..model.sound import ResolvedSound
from .util import join, respond


async def get_source(sound: ResolvedSound) -> FFmpegOpusAudio:
    return await FFmpegOpusAudio.from_probe(str(sound.random()))


async def play_sound(ctx: ApplicationContext, sound: ResolvedSound):
    if not await join(ctx):
        return

    if ctx.guild is not None and isinstance(ctx.guild.voice_client, VoiceClient):
        if ctx.guild.voice_client.is_playing():
            ctx.guild.voice_client.stop()

        source = await get_source(sound)
        ctx.guild.voice_client.play(source)
        await respond(ctx, ctx.command.name)
