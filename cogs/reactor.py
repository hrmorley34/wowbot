from __future__ import annotations

import asyncio
from collections.abc import Mapping
import discord
from discord.ext import commands
import traceback
from typing import Literal, TYPE_CHECKING, Tuple, Union
from .utils import JsonFileDict, Problem, react_output

if TYPE_CHECKING:
    from .sounds import BaseSoundsCog
    from .utils.typing import ReactionGuild


class ReactorCog(commands.Cog):
    bot: commands.Bot

    guilds: JsonFileDict[int, ReactionGuild]  # guild -> {"channel": <id>, "message": <id>}
    # mapping of (False, <unicode>) or (True, <emojiid>) -> <soundname> or "join" or "leave"
    reactionmap: Mapping[Union[Tuple[Literal[False], str], Tuple[Literal[True], int]], str] = {
        (True, 801507645491249202): "wow",  # 'wow'
        (False, "\U0001F480"): "death",  # skull
        (False, "\U0001F1FA"): "uhoh",  # regional indicator U
        (False, "\U0001F6AA"): "leave",  # door
    }

    def embed(self, ctx: commands.Context) -> discord.Embed:
        em = discord.Embed(title="React here to play sound!")
        return em

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.guilds = JsonFileDict("jsons/reactionguilds.json")

    def __repr__(self):
        return "<{}>".format(type(self).__name__)

    async def add_reactions(self, message: discord.Message):
        tasks = []
        for b, em in self.reactionmap.keys():
            if b:
                emoji = self.bot.get_emoji(em)
                tasks.append(asyncio.create_task(message.add_reaction(emoji)))
            else:
                tasks.append(asyncio.create_task(message.add_reaction(em)))
        await asyncio.gather(*tasks)

    async def remove_reactions(self, message: discord.Message):
        tasks = []
        for r in message.reactions:
            if r.me:
                tasks.append(asyncio.create_task(
                    message.remove_reaction(r, self.bot.user)))
        await asyncio.gather(*tasks)

    @commands.guild_only()
    @commands.group(aliases=["react"])
    async def reaction(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            # send this command's help (listing subcommands)
            await ctx.send_help(ctx.command)

    @reaction.command()
    async def here(self, ctx: commands.Context):
        " Create a reactable message in the current text channel "
        if ctx.guild is None:
            raise Problem("You aren't in a server!")

        message = await ctx.send(embed=self.embed(ctx))

        prev = self.guilds.get(message.guild.id)
        self.guilds[message.guild.id] = {
            "channel": message.channel.id, "message": message.id}

        tasks = [asyncio.create_task(self.add_reactions(message))]
        if prev is not None:
            try:
                ch = message.guild.get_channel(prev["channel"])
                if ch is None:
                    ch = await self.bot.fetch_channel(prev["channel"])
                msg = await ch.fetch_message(prev["message"])
                tasks.append(asyncio.create_task(self.remove_reactions(msg)))
            except Exception:
                traceback.print_exc()

        await asyncio.gather(*tasks)

        await react_output(self.bot, ctx.message)

    @reaction.command()
    async def remove(self, ctx: commands.Context):
        " Remove this server's reactable message "
        if ctx.guild is None:
            raise Problem("You aren't in a server!")

        prev = self.guilds.get(ctx.guild.id)

        if prev is not None:
            del self.guilds[ctx.guild.id]

            ch = self.bot.get_channel(prev["channel"])
            if ch is None:
                ch = await self.bot.fetch_channel(prev["channel"])
            msg = await ch.fetch_message(prev["message"])
            for r in msg.reactions:
                if r.me:
                    await msg.remove_reaction(r, self.bot.user)

            await react_output(self.bot, ctx.message)

    @reaction.command(aliases=["reset"])
    async def reload(self, ctx: commands.Context):
        " Reset the reactions "
        if ctx.guild is None:
            raise Problem("You aren't in a server!")

        gdata = self.guilds.get(ctx.guild.id)

        if gdata is None:
            raise Problem("There's no message in this server!")

        ch = self.bot.get_channel(gdata["channel"])
        if ch is None:
            ch = await self.bot.fetch_channel(gdata["channel"])
        msg = await ch.fetch_message(gdata["message"])
        await self.remove_reactions(msg)

        await self.add_reactions(msg)

        await react_output(self.bot, ctx.message)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, rawreaction: discord.RawReactionActionEvent):
        if rawreaction.user_id == self.bot.user.id:
            return  # ignore self, for when populating message

        guildid = rawreaction.guild_id

        if (
            guildid in self.guilds
            and self.guilds[guildid].get("channel") == rawreaction.channel_id
            and self.guilds[guildid].get("message") == rawreaction.message_id
        ):
            if rawreaction.emoji.id is None:
                sound = self.reactionmap.get((False, rawreaction.emoji.name))
            else:
                sound = self.reactionmap.get((True, rawreaction.emoji.id))
            if sound is None:
                return

            # guild = self.bot.get_guild(guildid)
            member: discord.Member = rawreaction.member
            # member = guild.get_member(rawreaction.user_id)
            # if member is None:
            #     member = await guild.fetch_member(rawreaction.user_id)
            ch = self.bot.get_channel(rawreaction.channel_id)
            if ch is None:
                ch = await self.bot.fetch_channel(rawreaction.channel_id)
            msg: discord.Message = await ch.fetch_message(rawreaction.message_id)

            try:
                await msg.remove_reaction(rawreaction.emoji, member)
            except discord.Forbidden:
                pass  # oh well

            vcog: BaseSoundsCog = self.bot.get_cog("SoundCog")
            if sound == "join":
                if member.voice is not None and member.voice.channel is not None:
                    await vcog.join_voice_channel(member.voice.channel)
            elif sound == "leave":
                await vcog.leave_voice_channel(member.guild)
            else:
                soundcmd = vcog.sounds.get(sound)
                if member.voice is not None and member.voice.channel is not None:
                    if await vcog.join_voice_channel(member.voice.channel):
                        await soundcmd.play_with(member.guild.voice_client)


def setup(bot: commands.Bot):
    bot.add_cog(ReactorCog(bot))


def teardown(bot: commands.Bot):
    bot.remove_cog("ReactorCog")
