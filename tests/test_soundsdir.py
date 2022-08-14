# SPDX-FileCopyrightText: 2022-present hrmorley34 <henry@morley.org.uk>
#
# SPDX-License-Identifier: MIT
from pathlib import Path

from wowbot.soundsdir import SoundsDir


class TestCommandsJson:
    ROOT = Path("tests/sounds")

    def test_load_soundsdir(self):
        sd = SoundsDir.from_folder(self.ROOT)

        assert sd.sounds_json.sounds
        assert sd.sound_collection
        assert sd.commands_json.commands
        sd.commands_json.check_sounds(sd.sound_collection)
