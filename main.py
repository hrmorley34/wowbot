#!/usr/bin/env python3
from discord.ext import commands
from discord_slash import SlashCommand
import json


bot = commands.Bot(command_prefix=commands.when_mentioned_or("&"))
slash = SlashCommand(bot, override_type=True)


bot.load_extension("cogs")


with open("client_data.json", "r") as f:
    client_data = json.load(f)
    bot.owner_ids = set(client_data.get("owner_ids", []))

try:
    bot.loop.run_until_complete(bot.start(client_data["token"]))
except KeyboardInterrupt:
    print("Stopping... (^C)")
    bot.loop.run_until_complete(bot.close())
