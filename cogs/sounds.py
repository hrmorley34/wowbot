import discord
from discord.ext import commands
import json
import glob
import random
from typing import Union
from .utils import react_output


class BaseVoiceCog(commands.Cog):
    bot: commands.bot.BotBase
    soundcommands: dict = None

    def __init__(self, bot: commands.bot.BotBase):
        self.bot = bot

    def __repr__(self):
        s = "<" + type(self).__name__
        if self.soundcommands is not None:
            s += " soundcommands=list[{}]".format(len(self.soundcommands))
        return s + ">"

    @commands.command(name="join")
    async def join_voice(self, ctx: commands.Context) -> bool:
        if ctx.guild is None:
            await ctx.send("Sorry, I can't do that outside of servers.", delete_after=4)
            return False

        voicestate = ctx.author.voice

        if voicestate is None:
            await ctx.send("But you aren't in a voice chat!", delete_after=4)
            return False

        if ctx.voice_client is not None and ctx.voice_client.channel == voicestate.channel:  # already there
            if ctx.voice_client.is_playing():
                ctx.voice_client.stop()
            return True

        try:
            await voicestate.channel.connect()
        except discord.ClientException:  # already in a voice chat
            if ctx.voice_client and not ctx.voice_client.is_playing():
                await ctx.voice_client.move_to(voicestate.channel)
            else:
                await ctx.send("Sorry, I'm busy right now.", delete_after=4)
                return False
        return True

    async def join_voice_channel(self, channel: discord.VoiceChannel) -> bool:
        voice_client = channel.guild.voice_client

        if voice_client is not None and voice_client.channel == channel:  # already there
            if voice_client.is_playing():
                voice_client.stop()
            return True

        try:
            await channel.connect()
        except discord.ClientException:  # already in a voice chat
            if voice_client and not voice_client.is_playing():
                await voice_client.move_to(channel)
            else:
                return False
        return True

    @commands.command(name="leave", aliases=["stop"])
    async def leave_voice(self, ctx):
        if ctx.voice_client is not None:
            await ctx.voice_client.disconnect()

    @commands.is_owner()
    @commands.command(name="trigger")
    async def trigger(self, ctx: commands.Context, cmd: str, where: Union[discord.VoiceChannel, discord.Guild, None] = None):
        if cmd not in self.soundcommands:
            await ctx.send(f"Unrecognised command: {cmd}", delete_after=4)
            return
        cmd = self.soundcommands[cmd]

        if isinstance(where, discord.Guild):
            voice_client = where.voice_client
            if voice_client is None:
                await ctx.send("Not connected in that guild!", delete_after=4)
                return
        elif isinstance(where, discord.VoiceChannel):
            voice_client = where.guild.voice_client
            if voice_client is None or voice_client.channel != where:
                if not await self.join_voice_channel(where):
                    await react_output(self.bot, ctx.message, success=False)
                    return
        else:
            await ctx.send("Supply a guild or voice channel!", delete_after=4)
            return

        await cmd.play_with(voice_client)
        await react_output(self.bot, ctx.message, success=True)


async def soundplayer_callback(self: BaseVoiceCog, ctx: commands.Context):
    if await self.join_voice(ctx):
        await ctx.command.play_with(ctx.voice_client)

    if getattr(ctx.command, "sound_autodelete", False):
        try:
            await ctx.message.delete()
        except discord.HTTPException:  # includes Forbidden, NotFound
            pass  # fail silently


class SoundPlayerCommand(commands.Command):
    sound_autodelete: bool = True  # should automatically delete the message on trigger?

    def __init__(self, name: str, data: dict):
        self.sound_name = name
        self.sound_data = data

        files = data["files"]

        arrays, weights = [], []
        for fd in files:
            filenames = []
            if "glob" in fd.keys():
                filenames.extend(glob.glob(fd["glob"]))
            if "filenames" in fd.keys():
                filenames.extend(fd["filenames"])
            if "filename" in fd.keys():
                filenames.append(fd["filename"])

            if len(filenames) >= 1:
                arrays.append(filenames)
                weights.append(fd.get("weight", 1))

        self.sound_arrays = arrays
        self.sound_weights = weights

        commands.Command.__init__(self, soundplayer_callback, name=name,
                                  aliases=data.get("aliases", []),
                                  **data.get("commandkwargs", {}))

    def copy(self):
        return type(self)(self.sound_name, self.sound_data)

    def get_filename(self):
        ls = random.choices(self.sound_arrays, self.sound_weights)[0]
        if len(ls):
            return random.choice(ls)
        else:
            raise Exception("Missing filenames")

    async def play_with(self, voice_client: discord.VoiceClient):
        fname = self.get_filename()
        source = await discord.FFmpegOpusAudio.from_probe(fname)
        voice_client.play(source)

        print(f"Played {self.sound_name} ({fname}) in "
              f"{voice_client.channel.name} ({voice_client.guild.name})")

        return fname


def VoiceCog(bot: commands.bot.BotBase) -> BaseVoiceCog:
    with open("jsons/sounds.json") as f:
        sounds_json = json.load(f)

    commands = {}
    for name, data in sounds_json.items():
        commands[name] = SoundPlayerCommand(name, data)

    pdict = {"sound_" + name: cmd for name, cmd in commands.items()}
    pdict["soundcommands"] = commands

    VoiceCogT = type("VoiceCog", (BaseVoiceCog,), pdict)

    return VoiceCogT(bot)


def setup(bot: commands.bot.BotBase):
    bot.add_cog(VoiceCog(bot))


def teardown(bot: commands.bot.BotBase):
    bot.remove_cog("VoiceCog")
