from __future__ import annotations

import discord
from discord.ext import commands
from discord_slash import cog_ext
from discord_slash.context import ComponentContext, SlashContext
from discord_slash.model import CommandObject
import json
from pathlib import Path
import random
import re
import string
from typing import Any, Callable, Coroutine, List, Mapping, Optional, Sequence, Union
from .utils import Problem, react_output
from .utils.typing import SOUNDS_JSON, SoundDef


SOUNDDIR = Path("./sounds")

# Characters valid within a slash command name
SLASHCHARS = string.ascii_letters + string.digits + "-_"
SLASHRE = re.compile(r"^[\w-]{1,32}$", re.IGNORECASE | re.ASCII)


class AudioPlayer:
    name: str
    description: Optional[str]
    aliases: Sequence[str]
    slash: bool
    slash_name: Optional[str]
    slash_group: Optional[str]
    cmd_kwargs: Mapping[str, Any]

    # Original data
    sound_data: SoundDef
    # Random sounds and weights
    sound_arrays: Sequence[Sequence[Path]]
    sound_weights: Sequence[int]

    autodelete: bool = True  # should we automatically delete the trigger message

    def __init__(self, name: str, data: SoundDef):
        self.name = name
        self.sound_data = data.copy()

        self.description = data.get("description", None)
        self.aliases = data.get("aliases", [])
        self.slash = data.get("slash", False)
        self.slash_name = data.get("slash_name", None)
        self.slash_group = data.get("slash_group", None)
        self.cmd_kwargs = data.get("commandkwargs", {})

        files = data.get("files", [])

        arrays: List[List[Path]] = []
        weights: List[int] = []
        for fd in files:
            filenames: List[Path] = []
            if "glob" in fd:
                filenames.extend(SOUNDDIR.glob(fd["glob"]))
            if "filenames" in fd:
                filenames.extend(map(SOUNDDIR.joinpath, fd["filenames"]))
            if "filename" in fd:
                filenames.append(SOUNDDIR / fd["filename"])

            if len(filenames) >= 1:
                arrays.append(filenames)
                weights.append(fd.get("weight", 1))

        self.sound_arrays = arrays
        self.sound_weights = weights

    def copy(self) -> AudioPlayer:
        return type(self)(self.name, self.sound_data)

    def get_filename(self) -> Path:
        ls = random.choices(self.sound_arrays, self.sound_weights)[0]
        if len(ls):
            return random.choice(ls)
        else:
            raise Exception("Missing filenames")

    async def play_with(self, voice_client: discord.VoiceClient) -> Path:
        fname = self.get_filename()
        source = await discord.FFmpegOpusAudio.from_probe(fname)
        voice_client.play(source)

        s = f"Played {self.name} ({fname})"
        try:
            s += f" in {voice_client.channel.name}"
            s += f" ({voice_client.guild.name})"
        except AttributeError:
            pass
        print(s)

        return fname

    def to_command_callback(self) -> Callable[[BaseSoundsCog, commands.Context], Coroutine]:
        async def callback(cself: BaseSoundsCog, ctx: commands.Context):
            if getattr(self, "autodelete", False):
                try:
                    await ctx.message.delete()
                except discord.HTTPException:  # includes Forbidden, NotFound
                    pass  # fail silently

            await cself.join_voice(ctx)  # may raise Problem
            await self.play_with(ctx.voice_client)

        callback.__name__ = self.name
        return callback

    def to_command(
        self,
        command_decorator: Callable[..., Callable[[Callable[..., Coroutine]], commands.Command]],
    ) -> commands.Command:
        callback = self.to_command_callback()
        cmd = command_decorator(
            name=self.name,
            aliases=self.aliases,
            description=self.description or "",
            **self.cmd_kwargs,
        )(callback)
        commands.guild_only()(cmd)
        return cmd

    def get_slash_name(self) -> str:
        if self.slash_name is not None:
            return self.slash_name

        if SLASHRE.match(self.name):
            return self.name

        for name in self.aliases:
            if SLASHRE.match(name):
                return name

        return "".join(c for c in self.name if c in SLASHCHARS)[:32]

    def to_slash_callback(self) -> Callable[[BaseSoundsCog, SlashContext], Coroutine]:
        name = self.get_slash_name()

        async def callback(cself: BaseSoundsCog, ctx: SlashContext):
            await ctx.defer(hidden=True)  # prevent `failed`

            # ctx.voice_client = ctx.guild.voice_client  # TODO: fix
            await cself.join_voice(ctx)  # may raise Problem
            await self.play_with(ctx.guild.voice_client)
            await ctx.send(name, hidden=True)

        # callback.__name__ = name
        return callback

    def to_slash(
        self,
        command_decorator: Callable[..., Callable[[Callable[..., Coroutine]], CommandObject]],
        subcommand_decorator: Callable[..., Callable[[Callable[..., Coroutine]], CommandObject]],
    ) -> CommandObject:
        name = self.get_slash_name()
        callback = self.to_slash_callback()

        if self.slash_group is None:
            return command_decorator(name=name, description=self.description, options=[])(callback)
        else:
            return subcommand_decorator(base=self.slash_group, name=name, description=self.description, options=[])(callback)


class BaseSoundsCog(commands.Cog):
    bot: commands.Bot
    sounds: Optional[dict[str, AudioPlayer]] = None

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def __repr__(self):
        s = "<" + type(self).__name__
        if self.sounds is not None:
            s += " sounds=array[{}]".format(len(self.sounds))
        return s + ">"

    async def join_voice_channel(self, channel: discord.VoiceChannel) -> True:
        voice_client: Optional[discord.VoiceClient] = channel.guild.voice_client

        if voice_client is not None and voice_client.channel == channel:  # already there
            if voice_client.is_playing():
                voice_client.stop()
            return True

        try:
            await channel.connect()
        except discord.ClientException:  # already in a voice chat
            if voice_client:  # ignore `voice_client.is_playing()`
                await voice_client.move_to(channel)
            else:
                raise Problem("Sorry, I'm busy right now.")
        return True

    async def join_voice(self, ctx: Union[commands.Context, SlashContext, ComponentContext]):
        if ctx.guild is None:
            raise commands.NoPrivateMessage

        voicestate: Optional[discord.VoiceState] = ctx.author.voice

        if voicestate is None:
            raise Problem("But you aren't in a voice chat!")

        return await self.join_voice_channel(voicestate.channel)

    async def leave_voice_channel(self, guild: discord.Guild) -> bool:
        voice_client: Optional[discord.VoiceClient] = guild.voice_client
        if voice_client is not None:
            await voice_client.disconnect()
            return True
        return False

    async def leave_voice(self, ctx: Union[commands.Context, SlashContext]):
        if ctx.guild is None:
            raise commands.NoPrivateMessage

        return await self.leave_voice_channel(ctx.guild)

    @commands.guild_only()
    @commands.command(name="join")
    async def cmd_join(self, ctx: commands.Context):
        await self.join_voice(ctx)

    @commands.guild_only()
    @commands.command(name="leave", aliases=["stop"])
    async def cmd_leave(self, ctx: commands.Context):
        await self.leave_voice(ctx)

    @commands.guild_only()
    @cog_ext.cog_slash(name="join")
    async def slash_join(self, ctx: SlashContext):
        await self.join_voice(ctx)
        await ctx.send("Hello!", hidden=True)

    @commands.guild_only()
    @cog_ext.cog_slash(name="leave")
    async def slash_leave(self, ctx: SlashContext):
        await self.leave_voice(ctx)
        await ctx.send("Goodbye!", hidden=True)

    @commands.is_owner()
    @commands.command(name="trigger")
    async def cmd_trigger(self, ctx: commands.Context, cmd: str, where: Union[discord.VoiceChannel, discord.Guild, None] = None):
        raise NotImplementedError

        if cmd not in self.soundcommands:
            raise Problem(f"Unrecognised command: {cmd}")

        cmdo = self.soundcommands[cmd]

        if isinstance(where, discord.Guild):
            voice_client = where.voice_client
            if voice_client is None:
                raise Problem("Not connected in that guild!")
        elif isinstance(where, discord.VoiceChannel):
            voice_client = where.guild.voice_client
            if voice_client is None or voice_client.channel != where:
                if not await self.join_voice_channel(where):
                    await react_output(self.bot, ctx.message, success=False)
                    return
        else:
            raise Problem("Supply a guild or voice channel!")

        await cmdo.play_with(voice_client)
        await react_output(self.bot, ctx.message, success=True)


def SoundCog(bot: commands.Bot) -> BaseSoundsCog:
    with open(SOUNDDIR / "sounds.json") as f:
        sounds_json: SOUNDS_JSON = json.load(f)

    sounds: dict[str, AudioPlayer] = {}
    d = {}
    for name, data in sounds_json.items():
        sounds[name] = s = AudioPlayer(name, data)
        d["scmd_" + s.name] = s.to_command(commands.command)
        d["sslash_" + s.get_slash_name()] = s.to_slash(cog_ext.cog_slash, cog_ext.cog_subcommand)

    d["sounds"] = sounds

    SoundCogT = type("SoundCog", (BaseSoundsCog,), d)

    return SoundCogT(bot)


def setup(bot: commands.Bot):
    bot.add_cog(SoundCog(bot))
    # bot.loop.create_task(
    #     bot.slash.sync_all_commands(delete_from_unused_guilds=True))


def teardown(bot: commands.Bot):
    bot.remove_cog("SoundCog")
