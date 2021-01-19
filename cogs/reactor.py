import discord
from discord.ext import commands
from .utils import JsonFileDict, PartialContext

from collections.abc import Mapping
import traceback


class ReactorCog(commands.Cog):
    bot: commands.bot.BotBase

    guilds: Mapping  # guild -> {"channel": <id>, "message": <id>}
    reactionmap: Mapping = {
        "\U0001F62E": "wow",  # face with open mouth
        "\U0001F480": "death",  # skull
    }

    def embed(self, ctx) -> discord.Embed:
        em = discord.Embed(title="React here to play sound!")
        return em

    def __init__(self, bot: discord.client.Client):
        self.bot = bot
        self.guilds = JsonFileDict("jsons/reactionguilds.json")

    def __repr__(self):
        return "<{}>".format(type(self).__name__)

    @commands.group(aliases=["react"])
    async def reaction(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send("No subcommand given!")

    @reaction.command()
    async def here(self, ctx):
        " Create a reactable message in the current text channel "
        message = await ctx.send(embed=self.embed(ctx))

        prev = self.guilds.get(message.guild.id)
        self.guilds[message.guild.id] = {
            "channel": message.channel.id, "message": message.id}

        if prev is not None:
            try:
                ch = message.guild.get_channel(prev["channel"])
                if ch is None:
                    ch = await self.bot.fetch_channel(prev["channel"])
                msg = await ch.fetch_message(prev["message"])
                for r in msg.reactions:
                    if r.me:
                        await msg.remove_reaction(r, self.bot.user)
            except:
                traceback.print_exc()

        for reaction in self.reactionmap.keys():
            await message.add_reaction(reaction)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, rawreaction):
        if rawreaction.user_id == self.bot.user.id:
            return  # ignore self, for when populating message

        guildid = rawreaction.guild_id

        if (
            guildid in self.guilds
            and self.guilds[guildid].get("channel") == rawreaction.channel_id
            and self.guilds[guildid].get("message") == rawreaction.message_id
        ):
            sound = self.reactionmap.get(rawreaction.emoji.name)

            vcog = self.bot.get_cog("VoiceCog")
            soundcmd = vcog.soundcommands.get(sound)

            guild = self.bot.get_guild(guildid)
            member = rawreaction.member
            # member = guild.get_member(rawreaction.user_id)
            # if member is None:
            #     member = await guild.fetch_member(rawreaction.user_id)
            ch = self.bot.get_channel(rawreaction.channel_id)
            if ch is None:
                ch = await self.bot.fetch_channel(rawreaction.channel_id)
            msg = await ch.fetch_message(rawreaction.message_id)

            ctx = PartialContext(
                author=member, guild=guild, channel=ch, message=msg, bot=self.bot, prefix=self.bot.command_prefix)

            try:
                await msg.remove_reaction(rawreaction.emoji, member)
            except discord.Forbidden:
                pass  # oh well
            await soundcmd(vcog, ctx)


def setup(bot: commands.bot.BotBase):
    bot.add_cog(ReactorCog(bot))


def teardown(bot: commands.bot.BotBase):
    bot.remove_cog("ReactorCog")
