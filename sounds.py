import discord
from discord.ext import commands

import os
import glob
import random

class Sounds(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @commands.command(name="join")
    async def join_voice(self, ctx):
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
                await self.move_to(voicestate.channel)
            else:
                await ctx.send("Sorry, I'm busy right now.")
                return False

        return True

    async def play_random(self, ctx, filenames):
        if len(filenames) <= 0:
            await ctx.send("I can't find any files...")
            return
        fname = random.choice(filenames)
        source = await discord.FFmpegOpusAudio.from_probe(fname)

        ctx.voice_client.play(source)

        return fname

    @commands.command(name="leave")
    async def leave_voice(self, ctx):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()


    @commands.command()
    async def wow(self, ctx):
        await self.join_voice(ctx)
        fname = await self.play_random(ctx, glob.glob("sounds/wow*.*"))
        print(f"Played {fname} in {ctx.channel}")

    @commands.command()
    async def death(self, ctx):
        await self.join_voice(ctx)
        fname = await self.play_random(ctx, glob.glob("sounds/legostarwarsdeath-*.*"))
        print(f"Played {fname} in {ctx.channel}")


def setup(bot):
    bot.add_cog(Sounds(bot))

def teardown(bot):
    bot.remove_cog("Sounds")
