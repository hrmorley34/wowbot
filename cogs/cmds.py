import asyncio
from discord.ext import commands
import re
from typing import Sequence

from .utils import ExpandingCodeblock


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


async def _run_command(args: Sequence[str], output: ExpandingCodeblock):
    proc = await asyncio.create_subprocess_exec(*args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
    assert proc.stdout is not None
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
    runtask = asyncio.create_task(_run_command(args, output=output))
    updatetask = asyncio.create_task(_update_codeblock(
        output, task=runtask, wait=updatefrequency))
    # Run both in parallel
    await asyncio.gather(runtask, updatetask)
    return runtask.result()


class CmdsCog(commands.Cog):
    bot: commands.Bot

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command()
    @commands.is_owner()
    async def gitpull(self, ctx: commands.Context):
        codeblock = ExpandingCodeblock(ctx=ctx)
        await run_command(("git", "pull", "--recurse-submodules"), output=codeblock)


def setup(bot: commands.Bot):
    bot.add_cog(CmdsCog(bot))


def teardown(bot: commands.Bot):
    bot.remove_cog("CmdsCog")
