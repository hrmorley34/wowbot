from discord.ext import commands


class Problem(commands.CommandError):
    """An error which is sent in the channel"""
    def to_str(self) -> str:
        return "\n".join(map(str, self.args))
