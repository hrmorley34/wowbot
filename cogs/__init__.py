import discord
from discord.ext import commands
from .utils import react_output
import random


activities = [discord.Game("wow - &wow")]


class InitCog(commands.Cog):
    bot: commands.bot.BotBase

    def __init__(self, bot: commands.bot.BotBase):
        self.bot = bot

    async def update_status(self):
        act = random.choice(activities)
        await self.bot.change_presence(activity=act)
        print(f"Updated status: {act}")

    @commands.Cog.listener()
    async def on_ready(self):
        print("Logged in as {0} ({0.id})".format(self.bot.user))

        await self.update_status()

    @commands.command()
    @commands.is_owner()
    async def reload(self, ctx):
        self.bot.reload_extension("cogs")
        print("Reloaded")

        await react_output(self.bot, ctx.message)

        await self.update_status()


def setup(bot):
    bot.add_cog(InitCog(bot))
    for ext in ["cogs.sounds", "cogs.reactor", "cogs.cmds", "cogs.slash"]:
        try:
            bot.load_extension(ext)
        except commands.ExtensionAlreadyLoaded:
            bot.reload_extension(ext)


def teardown(bot: commands.bot.BotBase):
    bot.remove_cog("InitCog")
