import discord
from discord.ext import commands

import os
import json
import glob
import random

@commands.command(name="join")
async def join_voice(ctx):
    voicestate = ctx.author.voice

    if voicestate is None:
        await ctx.send("But you aren't in a voice chat!")
        return False

    if ctx.voice_client and ctx.voice_client.channel == voicestate.channel: # already there
        if ctx.voice_client.is_playing():
            ctx.voice_client.stop()
        return True

    try:
        await voicestate.channel.connect()
    except discord.ClientException: # already in a voice chat
        if ctx.voice_client and not ctx.voice_client.is_playing():
            await ctx.bot.move_to(voicestate.channel)
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

@commands.command(name="leave")
async def leave_voice(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()


def sound_player(name, data):
    files = data["files"]
    @commands.command(name=name, aliases=data.get("aliases", []))
    async def function(ctx):
        if await join_voice(ctx):
            w = ([], [])
            for fd in files:
                if "glob" in fd.keys():
                    filenames = glob.glob(fd["glob"])
                elif "filenames" in fd.keys():
                    filenames = list(fd["filenames"])
                else:
                    filenames = [fd["filename"]]
                weight = fd.get("weight", 1)

                w[0].append(filenames)
                w[1].append(weight)

            fnames = random.choices(*w)[0]
            fname = await play_random(ctx, fnames)
            print(f"Played {name} ({fname}) in {ctx.channel}")

    return function


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
