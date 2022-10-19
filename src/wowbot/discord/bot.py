from __future__ import annotations

import os
from pathlib import Path

import dotenv
from discord import Bot

from ..model.soundsdir import SoundsDir
from .cogs import AdminCog, JoinCog
from .slash import make_cog


def main():
    dotenv.load_dotenv()

    TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
    if TOKEN is None:
        raise Exception("No token supplied. Please set DISCORD_BOT_TOKEN")

    ROOT = Path(os.environ.get("WOWBOT_SOUNDS_DIR", "./sounds"))
    if not ROOT.is_dir():
        raise Exception("Sounds directory doesn't exist. Please set WOWBOT_SOUNDS_DIR")

    sounds_dir = SoundsDir.from_folder(ROOT)

    bot = Bot()

    bot.add_cog(AdminCog())
    bot.add_cog(JoinCog())
    bot.add_cog(make_cog(sounds_dir))

    try:
        bot.loop.run_until_complete(bot.start(TOKEN))
    except KeyboardInterrupt:
        print("Stopping... (^C)")
        bot.loop.run_until_complete(bot.close())


if __name__ == "__main__":
    main()
