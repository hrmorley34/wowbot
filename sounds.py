import discord
from discord.ext import commands

import json
import glob
import random


@commands.command(name="join")
async def join_voice(ctx):
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
            await ctx.send("Sorry, I'm busy right now.")
            return False
    return True


async def play_random(ctx, filenames):
    if len(filenames) <= 0:
        await ctx.send("I can't find any files...")
        return
    fname = random.choice(filenames)
    source = await discord.FFmpegOpusAudio.from_probe(fname)

    ctx.voice_client.play(source)

    return fname


@commands.command(name="leave", aliases=["stop"])
async def leave_voice(ctx):
    await ctx.voice_client.disconnect()


def sound_player(name, data):
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
    async def cmd(ctx):
        if await join_voice(ctx):
            fnames = random.choices(arrays, weights)[0]
            fname = await play_random(ctx, fnames)
            print(f"Played {name} ({fname}) in {ctx.channel}")

    return cmd


LOADED_COMMANDS = []


def setup(bot):
    bot.add_command(join_voice)
    bot.add_command(leave_voice)

    with open("sounds/sounds.json") as f:
        SOUNDS = json.load(f)

    for name, data in SOUNDS.items():
        bot.add_command(sound_player(name, data))
        LOADED_COMMANDS.append(name)


def teardown(bot):
    bot.remove_command(join_voice)
    bot.remove_command(leave_voice)

    for name in LOADED_COMMANDS:
        bot.remove_command(name)

    LOADED_COMMANDS.clear()
