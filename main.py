#!/usr/bin/env python3
import discord
from discord.ext import commands

import json


bot = commands.Bot(command_prefix=commands.when_mentioned_or("&"))

activity = discord.Game("wow - &wow")


@bot.event
async def on_ready():
    print("Logged in as {0} ({0.id})".format(bot.user))
    await bot.change_presence(activity=activity)
    print(f"Updated status: {activity}")


bot.load_extension("cogs")


@bot.command()
@commands.is_owner()
async def reload(ctx):
    bot.reload_extension("cogs")
    print("Reloaded")

    try:
        await ctx.message.add_reaction("\u2705")  # \N{White heavy check mark}
    except discord.Forbidden:
        pass  # it doesn't matter too much

    await bot.change_presence(activity=activity)
    print(f"Updated status: {activity}")


with open("client_data.json", "r") as f:
    client_data = json.load(f)
    bot.owner_ids = set(client_data.get("owner_ids", []))

try:
    bot.loop.run_until_complete(bot.start(client_data["token"]))
except KeyboardInterrupt:
    print("Stopping... (^C)")
    bot.loop.run_until_complete(bot.close())
