import json
from pathlib import Path

from .command import CommandsJson
from .sound import SoundCollection, SoundsJson

SOUNDS_FILE = "sounds.json"
COMMANDS_FILE = "commands.json"


class SoundsDir:
    sounds_json: SoundsJson
    sound_collection: SoundCollection

    commands_json: CommandsJson

    def __init__(
        self, sounds_path: Path, sounds_root: Path, commands_path: Path
    ) -> None:
        with open(sounds_path) as f:
            sounds_data = json.load(f)

        self.sounds_json = SoundsJson.parse_obj(sounds_data)
        self.sound_collection = self.sounds_json.resolve_files(sounds_root)

        with open(commands_path) as f:
            commands_data = json.load(f)

        self.commands_json = CommandsJson.parse_obj(commands_data)
        self.commands_json.check_sounds(self.sound_collection)

    @classmethod
    def from_folder(cls, folder: Path):
        sounds_path = folder / SOUNDS_FILE
        commands_path = folder / COMMANDS_FILE
        return cls(
            sounds_path=sounds_path, sounds_root=folder, commands_path=commands_path
        )
