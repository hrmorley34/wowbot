from discord.ext import commands


def setup(bot):
    for ext in ["cogs.sounds", "cogs.reactor"]:
        try:
            bot.load_extension(ext)
        except commands.ExtensionAlreadyLoaded:
            bot.reload_extension(ext)
