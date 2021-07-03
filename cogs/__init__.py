import discord
from discord.ext import commands
from .utils import react_output
from typing import Optional
import platform
import random


activities = [discord.Game("wow - &wow")]


class InitCog(commands.Cog):
    bot: commands.Bot

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def update_status(self):
        act = random.choice(activities)
        await self.bot.change_presence(activity=act)
        print(f"Updated status: {act}")

    @commands.Cog.listener()
    async def on_ready(self):
        print("Logged in as {0} ({0.id})".format(self.bot.user))

        await self.update_status()

        self.bot.loop.create_task(
            self.bot.slash.sync_all_commands(delete_from_unused_guilds=True))

    async def _reload(self):
        self.bot.reload_extension("cogs")
        print("Reloaded")

        await self.update_status()

        self.bot.loop.create_task(
            self.bot.slash.sync_all_commands(delete_from_unused_guilds=True))

    @commands.command(name="reload")
    @commands.is_owner()
    async def reload(self, ctx: commands.Context):
        await self._reload()

        await react_output(self.bot, ctx.message)

    @commands.command(name="suspend", aliases=["^z", "^Z"])
    @commands.is_owner()
    async def suspend(self, ctx: commands.Context, *, plt: Optional[str] = None):
        if plt:
            if platform.node().lower() != plt.lower():
                return
        else:
            await ctx.send(platform.node())
            return

        print("Suspending...")

        OLD_HELP = self.bot.help_command
        for name in list(self.bot.extensions):
            self.bot.unload_extension(name)
        self.bot.help_command = None

        @self.bot.command(name="unsuspend", aliases=["fg", "bg", "start"])
        @commands.is_owner()
        async def unsuspend(ctx):
            print("Unsuspending...")
            ctx.bot.help_command = OLD_HELP

            try:
                ctx.bot.load_extension("cogs")
            except commands.ExtensionAlreadyLoaded:
                ctx.bot.reload_extension("cogs")

            ctx.bot.remove_command(ctx.command.name)  # remove self
            print("Hello!")

        print("Done.")
        await react_output(self.bot, ctx.message)


def setup(bot: commands.Bot):
    bot.add_cog(InitCog(bot))

    for ext in ["cogs.sounds", "cogs.reactor", "cogs.cmds", "cogs.slash"]:
        try:
            bot.load_extension(ext)
        except commands.ExtensionAlreadyLoaded:
            bot.reload_extension(ext)


def teardown(bot: commands.Bot):
    bot.remove_cog("InitCog")
