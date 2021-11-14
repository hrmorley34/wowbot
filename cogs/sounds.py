from __future__ import annotations

import discord
from discord.ext import commands
from discord_slash import cog_ext
from discord_slash.context import ComponentContext, SlashContext
from discord_slash.model import CommandObject, SlashCommandOptionType
from discord_slash.utils.manage_commands import create_choice, create_option
import json
from pathlib import Path
import re
import string
from typing import Any, Callable, Coroutine, Literal, Optional, Type, Union

from sounds.lib.command import Command as _BaseCommand, BaseSlashCommand as _BaseSlashCommand, SlashCommand as _SlashCommand, SlashCommandType, SlashOptionCommand as _SlashOptionCommand
from sounds.lib.sound import Sound as _BaseSound
from sounds.lib.typing import COMMANDS_JSON, COMMANDS_SLASH_JSON, SOUNDS_JSON, CommandDef, CommandName, SlashCommandCommon, SlashGroup, SlashName, SlashOption, SoundDef, SoundName
from .utils import Problem, react_output


SOUNDDIR = Path("./sounds")

# Characters valid within a slash command name
SLASHCHARS = string.ascii_letters + string.digits + "-_"
SLASHRE = re.compile(r"^[\w-]{1,32}$", re.IGNORECASE | re.ASCII)


class Sound(_BaseSound):
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


class Command(_BaseCommand):
    sound: Sound

    autodelete: bool = True  # should we automatically delete the trigger message

    def __init__(self, name: CommandName, data: CommandDef, sounds: dict[SoundName, Sound]):
        super().__init__(name, data, sounds)

    def get_filename(self) -> Path:
        return self.sound.get_filename()

    async def play_with(self, voice_client: discord.VoiceClient) -> Path:
        return await self.sound.play_with(voice_client)

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

    def to_command(self, commandtype: Type[commands.Command] = commands.Command) -> commands.Command:
        callback = self.to_command_callback()
        cmd = commandtype(
            callback,
            name=self.name,
            aliases=tuple(self.aliases),
            description=self.description or "",
            **self.commandkwargs,
        )
        commands.guild_only()(cmd)
        return cmd


class BaseSlashCommand(_BaseSlashCommand):
    _slashcommandtypes = {}

    def __init__(self, group: Optional[SlashGroup], name: SlashName, data: SlashCommandCommon, sounds: dict[SoundName, Sound]):
        super().__init__(group, name, data, sounds)

    def to_slash_callback(self) -> Callable[..., Coroutine]:
        raise NotImplementedError

    def get_slash_options(self) -> list[dict[str, Any]]:
        return []

    def to_slash(
        self,
        command_decorator: Callable[..., Callable[[Callable[..., Coroutine]], CommandObject]],
        subcommand_decorator: Callable[..., Callable[[Callable[..., Coroutine]], CommandObject]],
    ) -> CommandObject:
        callback = self.to_slash_callback()

        if self.group is None:
            dec = command_decorator(name=self.name, description=self.description, options=self.get_slash_options())
        else:
            dec = subcommand_decorator(base=self.group, name=self.name, description=self.description, options=self.get_slash_options())
        return dec(callback)


class SlashCommand(BaseSlashCommand, _SlashCommand, slashtype=SlashCommandType.normal):
    sound: Sound

    def get_filename(self) -> Path:
        return self.sound.get_filename()

    async def play_with(self, voice_client: discord.VoiceClient) -> Path:
        return await self.sound.play_with(voice_client)

    def to_slash_callback(self) -> Callable[[BaseSoundsCog, SlashContext], Coroutine]:
        async def callback(cself: BaseSoundsCog, ctx: SlashContext):
            await ctx.defer(hidden=True)  # prevent `failed`

            # ctx.voice_client = ctx.guild.voice_client  # TODO: fix
            await cself.join_voice(ctx)  # may raise Problem
            await self.play_with(ctx.guild.voice_client)
            await ctx.send(self.name, hidden=True)

        callback.__name__ = self.name
        return callback


class SlashOptionCommand(BaseSlashCommand, _SlashOptionCommand, slashtype=SlashCommandType.options):
    options: dict[SlashOption, Sound]

    def get_slash_options(self) -> list[dict[str, Any]]:
        return [
            create_option(
                name="sound",
                description="Which version of the sound?",
                option_type=SlashCommandOptionType.STRING,
                required=False,
                choices=[
                    create_choice(name, name)
                    for name in self.options.keys()
                ]
            ),
        ]

    def to_slash_callback(self) -> Callable[[BaseSoundsCog, SlashContext, SlashOption], Coroutine]:
        async def callback(cself: BaseSoundsCog, ctx: SlashContext, sound: SlashOption | None = None):
            await ctx.defer(hidden=True)  # prevent `failed`

            soundobj = self.options[sound or self.default]

            # ctx.voice_client = ctx.guild.voice_client  # TODO: fix
            await cself.join_voice(ctx)  # may raise Problem
            await soundobj.play_with(ctx.guild.voice_client)
            await ctx.send(self.name, hidden=True)

        callback.__name__ = self.name
        return callback


class BaseSoundsCog(commands.Cog):
    bot: commands.Bot
    sounds: Optional[dict[SoundName, Sound]] = None

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def __repr__(self):
        s = "<" + type(self).__name__
        if self.sounds is not None:
            s += " sounds=array[{}]".format(len(self.sounds))
        return s + ">"

    async def join_voice_channel(self, channel: discord.VoiceChannel) -> Literal[True]:
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
    d: dict[str, Any] = {}

    with open(SOUNDDIR / "sounds.json") as f:
        sounds_json: SOUNDS_JSON = json.load(f)

    sounds: dict[SoundName, Sound] = {}
    for name, data in sounds_json.items():
        sounds[name] = Sound(SOUNDDIR, name, data)

    d["sounds"] = sounds

    with open(SOUNDDIR / "commands.json") as f:
        commands_json: COMMANDS_JSON = json.load(f)

    for name, data in commands_json.items():
        cmd = Command(name, data, sounds)
        d["scmd_" + cmd.name] = cmd.to_command(commands.Command)

    with open(SOUNDDIR / "commands_slash.json") as f:
        commands_slash_json: COMMANDS_SLASH_JSON = json.load(f)

    for group, namedata in commands_slash_json.items():
        if group is None:
            groupstr = ""
        else:
            groupstr = f"group_{group}_"
        for name, data in namedata.items():
            slcmd = BaseSlashCommand(group, name, data, sounds)
            d[f"sslash_{groupstr}{slcmd.name}"] = slcmd.to_slash(cog_ext.cog_slash, cog_ext.cog_subcommand)

    SoundCogT = type("SoundCog", (BaseSoundsCog,), d)

    return SoundCogT(bot)


def setup(bot: commands.Bot):
    bot.add_cog(SoundCog(bot))
    # bot.loop.create_task(
    #     bot.slash.sync_all_commands(delete_from_unused_guilds=True))


def teardown(bot: commands.Bot):
    bot.remove_cog("SoundCog")
