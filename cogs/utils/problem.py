from discord.ext import commands


class Problem(commands.CommandError):
    """An error which is sent in the channel"""
    pass
