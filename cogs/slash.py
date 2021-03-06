from discord.ext import commands
from discord_slash import cog_ext, SlashContext, model
import functools
import string
import re
import traceback
from .utils import Problem


# Limit some commands' servers
GUILDS = [533622436860657664, 690860332322914305]
rcommand = functools.partial(cog_ext.cog_slash, guild_ids=GUILDS)
rsubcommand = functools.partial(cog_ext.cog_subcommand, guild_ids=GUILDS)
command = cog_ext.cog_slash
subcommand = cog_ext.cog_subcommand


class BaseSlashCog(commands.Cog):
    bot: commands.Bot

    def __init__(self, bot):
        self.bot = bot

    @property
    def voicecog(self):
        return self.bot.get_cog("VoiceCog")

    @commands.Cog.listener()
    async def on_slash_command_error(self, ctx: SlashContext, error: commands.CommandError):
        if isinstance(error, Problem):
            await ctx.send("\n".join(map(str, error.args)), hidden=True)
            return
        traceback.print_exc()

    @command(name="join")
    async def join(self, ctx: SlashContext):
        await ctx.defer(hidden=True)

        ctx.voice_client = ctx.guild.voice_client
        await self.voicecog.join_voice(ctx)
        await ctx.send("Hello!", hidden=True)

    @command(name="leave")
    async def leave(self, ctx: SlashContext):
        await ctx.defer(hidden=True)

        ctx.voice_client = ctx.guild.voice_client
        await self.voicecog.leave_voice(ctx)
        await ctx.send("Goodbye!", hidden=True)

    @rcommand(name="reload")
    async def reload(self, ctx: SlashContext):
        await ctx.defer(hidden=True)

        await self.bot.get_cog("InitCog")._reload()

        await ctx.send("Reloaded!", hidden=True)


SLASHCHARS = string.ascii_letters + string.digits + "-_"
SLASHRE = re.compile(r"^[\w-]{1,32}$", re.I | re.A)


def audio_command(cmd: commands.Command, base=None) -> model.CommandObject:
    name = cmd.name
    if not SLASHRE.match(name):
        for name in cmd.aliases:
            if SLASHRE.match(name):
                break
        else:
            name = "".join(c for c in cmd.name if c in SLASHCHARS)[:32]

    async def player(self, ctx: SlashContext):
        await ctx.defer(hidden=True)  # prevent `failed`

        ctx.voice_client = ctx.guild.voice_client
        if await self.voicecog.join_voice(ctx):
            await cmd.play_with(ctx.guild.voice_client)
        await ctx.send(name, hidden=True)

    if base is None:
        return command(name=name, description=cmd.description)(player)
    else:
        return subcommand(base=base, name=name, description=cmd.description)(player)


def SlashCog(bot: commands.Bot) -> BaseSlashCog:
    voicecog = bot.get_cog("VoiceCog")

    i = 0
    pdict = {}
    for cmd in voicecog.soundcommands.values():
        if not cmd.hidden:
            scmd = audio_command(cmd)
            pdict["play_" + scmd.name] = scmd
            i += 1
            if i >= 25:
                break

    SlashCogT = type("SlashCog", (BaseSlashCog,), pdict)

    return SlashCogT(bot)


def setup(bot: commands.Bot):
    bot.add_cog(SlashCog(bot))


def teardown(bot: commands.Bot):
    bot.remove_cog("SlashCog")
