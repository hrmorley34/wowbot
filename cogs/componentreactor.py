"Component Reactor: click on components to play sounds"

from __future__ import annotations

import discord
from discord.channel import TextChannel
from discord.errors import NotFound
from discord.ext import commands
from discord.message import Message
from discord_slash import cog_ext
from discord_slash.context import ComponentContext, SlashContext
from discord_slash.model import ButtonStyle
from discord_slash.utils.manage_components import create_button, create_actionrow
import traceback
from typing import TYPE_CHECKING
from .utils import JsonFileDict, Problem

if TYPE_CHECKING:
    from .sounds import BaseSoundsCog
    from .utils.typing import ReactionGuild


BASE_COMMAND: str = "react"


class ComponentReactorCog(commands.Cog):
    bot: commands.Bot
    guilds: JsonFileDict[int, ReactionGuild]

    def get_embed(self, ctx: SlashContext) -> discord.Embed:
        em = discord.Embed(title="React here to play sound!")
        return em

    def get_components(self) -> list[dict]:
        return [
            create_actionrow(
                create_button(
                    style=ButtonStyle.gray,
                    emoji=self.bot.get_emoji(801507645491249202),
                    custom_id="wow",
                ),
                create_button(
                    style=ButtonStyle.gray,
                    emoji="\U0001F480",  # skull
                    custom_id="death",
                ),
                create_button(
                    style=ButtonStyle.gray,
                    emoji="\U0001F1FA",  # regional indicator U
                    custom_id="uhoh",
                ),
                create_button(
                    style=ButtonStyle.red,
                    emoji="\U0001F6AA",  # door
                    custom_id="leave",
                ),
            ),
        ]

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.guilds = JsonFileDict("jsons/componentreactionguilds.json")

    def __repr__(self) -> str:
        return "<{}>".format(type(self).__name__)

    async def get_guild_message(self, rg: ReactionGuild) -> Message:
        ch = self.bot.get_channel(rg["channel"])
        if ch is None:
            ch = await self.bot.fetch_channel(rg["channel"])
        return await ch.fetch_message(rg["message"])

    # @cog_ext.cog_subcommand(base=BASE_COMMAND, name="help")
    # @commands.group(name="creaction", aliases=["creact"])
    # async def help(self, ctx: SlashContext):
    #     pass

    @cog_ext.cog_subcommand(base=BASE_COMMAND, name="here")
    async def here(self, ctx: SlashContext):
        " Create a reactable message in the current text channel "
        if ctx.guild is None:
            raise Problem("You aren't in a server!")

        await self.in_.invoke(ctx, ctx.channel)

    @cog_ext.cog_subcommand(base=BASE_COMMAND, name="in")
    async def in_(self, ctx: SlashContext, channel: TextChannel):
        " Add a reactor in the specified channel "
        message: Message = await channel.send(embed=self.get_embed(ctx), components=self.get_components())

        prev = self.guilds.get(message.guild.id)
        self.guilds[message.guild.id] = {
            "channel": message.channel.id, "message": message.id}

        if prev is not None:
            try:
                msg = await self.get_guild_message(prev)
                await msg.delete()
            except NotFound:
                pass
            except Exception:
                traceback.print_exc()

        await ctx.send("Sent!", hidden=True)

    @cog_ext.cog_subcommand(base=BASE_COMMAND, name="remove")
    async def remove(self, ctx: SlashContext):
        " Remove this server's reactable message "
        if ctx.guild is None:
            raise Problem("You aren't in a server!")

        prev = self.guilds.get(ctx.guild.id)

        if prev is not None:
            del self.guilds[ctx.guild.id]

            try:
                msg = await self.get_guild_message(prev)
                await msg.delete()
            except NotFound:
                pass

            await ctx.send("Done!", hidden=True)
        else:
            await ctx.send("There isn't one!", hidden=True)

    @cog_ext.cog_subcommand(base=BASE_COMMAND, name="reload")
    async def reload(self, ctx: SlashContext):
        " Reset the reactions "
        if ctx.guild is None:
            raise Problem("You aren't in a server!")

        gdata = self.guilds.get(ctx.guild.id)
        if gdata is None:
            raise Problem("There's no message in this server!")

        msg = await self.get_guild_message(gdata)
        await msg.edit(embed=self.get_embed(ctx), components=self.get_components())
        await ctx.send("Done!", hidden=True)

    @commands.Cog.listener(name="on_component")
    async def _on_component(self, ctx: ComponentContext):
        try:
            await self.on_component(ctx)
        except commands.CommandError as error:
            await self.on_component_callback_error(ctx, error)
        except Exception as error:
            await self.on_component_callback_error(ctx, commands.CommandError(error))

    async def on_component(self, ctx: ComponentContext):
        if ctx.guild is None:
            return

        guildid = ctx.guild_id

        if (
            guildid in self.guilds
            and self.guilds[guildid].get("channel") == ctx.channel_id
            # and self.guilds[guildid].get("message") == ctx.???
        ):
            sound: str = ctx.custom_id

            member: discord.Member = ctx.author
            vcog: BaseSoundsCog = self.bot.get_cog("SoundCog")
            if sound == "join":
                # if member.voice is not None and member.voice.channel is not None:
                await vcog.join_voice(ctx)
                await ctx.defer(ignore=True)
                return
            elif sound == "leave":
                await vcog.leave_voice_channel(member.guild)
                await ctx.defer(ignore=True)
                return
            else:
                soundcmd = vcog.sounds.get(sound)
                # if member.voice is not None and member.voice.channel is not None:
                if await vcog.join_voice(ctx):
                    await soundcmd.play_with(member.guild.voice_client)
                    await ctx.defer(ignore=True)
                    return

    @commands.Cog.listener()
    async def on_component_callback_error(self, ctx: ComponentContext, error: commands.CommandError):
        if isinstance(error, Problem):
            await ctx.send(error.to_str(), hidden=True)
            return
        elif isinstance(error, commands.NoPrivateMessage):  # guild_only check failed
            await ctx.send("You need to be in a guild to do that!", hidden=True)
            return
        raise error


def setup(bot: commands.Bot):
    bot.add_cog(ComponentReactorCog(bot))


def teardown(bot: commands.Bot):
    bot.remove_cog("ComponentReactorCog")
