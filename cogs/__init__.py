import discord
from discord.ext import commands
from discord_slash import cog_ext
from discord_slash.context import SlashContext
from discord_slash.model import SlashCommandPermissionType
from discord_slash.utils.manage_commands import create_permission
import platform
import random
from typing import Optional

from .utils import react_output
from .utils.problem import Problem


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

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, Problem):
            await ctx.send(error.to_str(), delete_after=4)
            return
        elif isinstance(error, commands.NoPrivateMessage):  # guild_only check failed
            await ctx.send("You need to be in a guild to do that!", delete_after=4)
            return
        raise error

    @commands.Cog.listener()
    async def on_slash_command_error(self, ctx: SlashContext, error: commands.CommandError):
        if isinstance(error, Problem):
            await ctx.send(error.to_str(), hidden=True)
            return
        elif isinstance(error, commands.NoPrivateMessage):  # guild_only check failed
            await ctx.send("You need to be in a guild to do that!", hidden=True)
            return
        raise error

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

    @cog_ext.cog_slash(
        name="reload",
        guild_ids=[690860332322914305],
        default_permission=False,
        permissions={
            690860332322914305: [
                create_permission(367722993293590529, SlashCommandPermissionType.USER, True),
            ],
        },
    )
    async def slash_reload(self, ctx: SlashContext):
        await ctx.defer(hidden=True)

        await self._reload()

        await ctx.send("Reloaded!", hidden=True)

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

    for ext in [
        "cogs.sounds",
        "cogs.reactor",
        "cogs.cmds",
        "cogs.componentreactor",
    ]:
        try:
            bot.load_extension(ext)
        except commands.ExtensionAlreadyLoaded:
            bot.reload_extension(ext)


def teardown(bot: commands.Bot):
    bot.remove_cog("InitCog")
