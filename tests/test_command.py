# SPDX-FileCopyrightText: 2022-present hrmorley34 <henry@morley.org.uk>
#
# SPDX-License-Identifier: MIT
import json
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

import pytest
from pydantic import ValidationError

from wowbot.command import ChoiceCommand, CommandsJson, SoundCommand, SubcommandsCommand


class TestCommandsJson:
    ROOT = Path("tests/sounds")

    def test_wrong_version_fails(self):
        with open(self.ROOT / "commands.json") as f:
            # known functional data, according to other test
            data = json.load(f)

        for version in {-1, 0, 2, 3, float("-inf"), float("NaN"), float("inf")}:
            data["version"] = version
            with pytest.raises(ValidationError):
                CommandsJson.parse_obj(data)

    def test_missing_key_fails(self):
        with open(self.ROOT / "commands.json") as f:
            # known functional data, according to other test
            data_original = json.load(f)

        for key in ["version", "commands"]:
            data = data_original.copy()
            del data[key]
            with pytest.raises(ValidationError):
                CommandsJson.parse_obj(data)

    def test_commands_example(self):
        with open(self.ROOT / "commands.json") as f:
            data = json.load(f)

        cj = CommandsJson.parse_obj(data)

        assert len(cj.commands) == 3
        assert isinstance(cj.commands[0], SoundCommand)
        assert isinstance(cj.commands[1], ChoiceCommand)
        assert cj.commands[1].get_default_choice() == "Option 1"
        assert isinstance(cj.commands[2], SubcommandsCommand)
        assert len(cj.commands[2].subcommands) == 3
        assert isinstance(cj.commands[2].subcommands[0], SoundCommand)
        assert isinstance(cj.commands[2].subcommands[1], ChoiceCommand)
        assert cj.commands[2].subcommands[1].get_default_choice() is None
        assert isinstance(cj.commands[2].subcommands[2], SubcommandsCommand)
        assert len(cj.commands[2].subcommands[2].subcommands) == 1
        assert isinstance(cj.commands[2].subcommands[2].subcommands[0], SoundCommand)

    @staticmethod
    def get_data_from_commands(*commands: Any) -> Any:
        return {"version": 1, "commands": list(commands)}

    @staticmethod
    def get_subcommand_from_commands(*commands: Any, name: Optional[str] = None) -> Any:
        if name is None:
            name = str(uuid4())[:30]
        return {"name": name, "subcommands": list(commands)}

    def test_choices_multiple_defaults_fails(self):
        for count in range(2, 5):
            choices = [
                {"name": f"thing{i}", "sound": "s.mysound", "default": True}
                for i in range(count)
            ]
            cmd = {"name": "cmd", "choices": choices}
            data = self.get_data_from_commands(cmd)

            with pytest.raises(ValidationError):
                CommandsJson.parse_obj(data)

    def test_subcommand_too_deep_fails(self):
        # sub of sub of sub-group - not allowed
        dep3 = {"name": "mycommand", "sound": "s.mysound"}
        dep2 = self.get_subcommand_from_commands(dep3.copy())  # sub of sub-group
        dep1 = self.get_subcommand_from_commands(dep2, dep3.copy())  # sub-group
        dep0 = self.get_subcommand_from_commands(dep1, dep3.copy())  # base
        data = self.get_data_from_commands(dep0)

        with pytest.raises(ValidationError):
            CommandsJson.parse_obj(data)

    def test_no_choices_fails(self):
        cmd: Any = {"name": "cmd", "choices": []}
        data = self.get_data_from_commands(cmd)

        with pytest.raises(ValidationError):
            CommandsJson.parse_obj(data)

    def test_too_many_choices_fails(self):
        for count in [26, 27, 100]:
            choices: list[Any] = [
                {"name": f"thing{i}", "sound": "s.mysound"} for i in range(count)
            ]
            choices[0]["default"] = True

            cmd = {"name": "cmd", "choices": choices}
            data = self.get_data_from_commands(cmd)

            with pytest.raises(ValidationError):
                CommandsJson.parse_obj(data)
