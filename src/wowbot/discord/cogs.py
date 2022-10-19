from __future__ import annotations

from discord import ApplicationContext, Cog, slash_command

from .util import get_voice_name, join, leave, respond


class AdminCog(Cog):
    @Cog.listener()
    async def on_ready(self):
        print("Connected!")


class JoinCog(Cog):
    @slash_command(name="join", description="Join your current voice channel")
    async def join_cmd(self, ctx: ApplicationContext):
        if not await join(ctx):
            return
        name = get_voice_name(ctx, "voice")
        await respond(ctx, f"Joined {name}")

    @slash_command(name="leave", description="Leave your current voice channel")
    async def leave_cmd(self, ctx: ApplicationContext):
        name = get_voice_name(ctx, "voice")
        if not await leave(ctx):
            return
        await respond(ctx, f"Left {name}")
