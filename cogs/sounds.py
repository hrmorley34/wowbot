import discord
from discord.ext import commands
import json
import glob
import random


class BaseVoiceCog(commands.Cog):
    bot: commands.bot.BotBase
    soundcommands: list = None

    def __init__(self, bot: commands.bot.BotBase):
        self.bot = bot

    def __repr__(self):
        s = "<" + type(self).__name__
        if self.soundcommands is not None:
            s += " soundcommands=list[{}]".format(len(self.soundcommands))
        return s + ">"

    @commands.command(name="join")
    async def join_voice(self, ctx):
        voicestate = ctx.author.voice

        if voicestate is None:
            await ctx.send("But you aren't in a voice chat!")
            return False

        if (
            ctx.voice_client is not None and ctx.voice_client.channel == voicestate.channel
        ):  # already there
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

    async def play_random(self, ctx, filenames):
        if len(filenames) <= 0:
            await ctx.send("I can't find any files...", delete_after=4)
            return
        fname = random.choice(filenames)
        source = await discord.FFmpegOpusAudio.from_probe(fname)

        ctx.voice_client.play(source)

        return fname

    @commands.command(name="leave", aliases=["stop"])
    async def leave_voice(self, ctx):
        await ctx.voice_client.disconnect()


def new_sound_player(name, data):
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

        arrays.append(filenames)
        weights.append(fd.get("weight", 1))

    @commands.command(name=name, aliases=data.get("aliases", []), **data.get("commandkwargs", {}))
    async def cmd(self, ctx):
        if await self.join_voice(ctx):
            fnames = random.choices(arrays, weights)[0]
            fname = await self.play_random(ctx, fnames)
            print(f"Played {name} ({fname}) in {ctx.author.voice.channel.name} ({ctx.guild.name})")

    return cmd


def VoiceCog(bot: commands.bot.BotBase):
    with open("sounds/sounds.json") as f:
        sounds_json = json.load(f)

    commands = {}
    for name, data in sounds_json.items():
        commands[name] = new_sound_player(name, data)

    pdict = {"sound_" + name: cmd for name, cmd in commands.items()}
    pdict["soundcommands"] = commands

    VoiceCogT = type("VoiceCog", (BaseVoiceCog,), pdict)

    return VoiceCogT(bot)


def setup(bot: commands.bot.BotBase):
    bot.add_cog(VoiceCog(bot))


def teardown(bot: commands.bot.BotBase):
    bot.remove_cog("VoiceCog")
