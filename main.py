import discord
from discord.ext import commands

import json


bot = commands.Bot(command_prefix="&")

@bot.event
async def on_ready():
    print("Logged in as {0} ({0.id})".format(bot.user))

bot.load_extension("sounds")
@bot.command()
async def reload(ctx):
    bot.reload_extension("sounds")
    print("Reloaded")


with open("client_data.json", "r") as f:
    client_data = json.load(f)
bot.run(client_data["token"])
