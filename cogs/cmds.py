from discord.ext import commands
from .utils import ExpandingCodeblock

import asyncio
import re


ANSI_RE = re.compile("\x1b\\[[^\\100-\\177]*[\\100-\\177]")


def decode_output(in_: bytes, encoding=None) -> str:
    if encoding is None:
        t = in_.decode()
    else:
        t = in_.decode(encoding=encoding)
    t = re.sub("\r+\n", "\n", t)  # \r before \n does nothing
    t = ANSI_RE.sub("", t)  # remove ANSI codes

    # abc\rd -> abc.
    #         + d... -> dbc
    partsiter = iter(t.split("\r"))
    strcut = next(partsiter)
    for p in partsiter:
        if len(p) < len(strcut):
            strcut = p + strcut[len(p):]
        else:
            strcut = p

    return strcut


async def _run_command(args, output: ExpandingCodeblock):
    proc = await asyncio.create_subprocess_exec(*args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
    rline = await proc.stdout.readline()
    while rline:
        output.append(decode_output(rline))
        rline = await proc.stdout.readline()
    await proc.wait()
    return proc.returncode


async def _update_codeblock(cb: ExpandingCodeblock, task: asyncio.Task, wait: float = 0.1):
    while not task.done():
        await cb.update_messages()
        await asyncio.sleep(wait)
    await cb.update_messages()


async def run_command(args, output: ExpandingCodeblock, updatefrequency: float = 0.1):
    runtask = asyncio.Task(_run_command(args, output=output))
    updatetask = asyncio.Task(_update_codeblock(
        output, task=runtask, wait=updatefrequency))
    # Run both in parallel
    await asyncio.gather(runtask, updatetask)
    return runtask.result()


class CmdsCog(commands.Cog):
    bot: commands.bot.BotBase

    def __init__(self, bot: commands.bot.BotBase):
        self.bot = bot

    @commands.command()
    @commands.is_owner()
    async def gitpull(self, ctx):
        codeblock = ExpandingCodeblock(ctx=ctx)
        await run_command(("git", "pull"), output=codeblock)


def setup(bot: commands.bot.BotBase):
    bot.add_cog(CmdsCog(bot))


def teardown(bot: commands.bot.BotBase):
    bot.remove_cog("CmdsCog")
