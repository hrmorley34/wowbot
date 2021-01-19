from discord.ext import commands


def setup(bot):
    for ext in ["cogs.sounds"]:
        try:
            print("Load "+ext)
            bot.load_extension(ext)
        except commands.ExtensionAlreadyLoaded:
            print("Reload "+ext)
            bot.reload_extension(ext)
