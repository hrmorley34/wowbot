from __future__ import annotations

__all__ = [
    "SlashCommandName",
    "OptionName",
    "SoundCommand",
    "CommandOption",
    "OptionsCommand",
    "SubcommandsCommand",
    "AnyCommand",
    "CommandsJson",
]

from typing import List, Literal, NewType, Union

import regex
from pydantic import ConstrainedStr, conlist, constr, validator

from .model import BaseModel
from .sound import SoundName

# https://discord.com/developers/docs/interactions/application-commands#application-command-object-application-command-naming
_ValidSlashFieldType = regex.compile(r"^[-_\p{L}\p{N}\p{sc=Deva}\p{sc=Thai}]{1,32}$")


class ValidSlashField(ConstrainedStr):
    regex = _ValidSlashFieldType  # type: ignore - regex and re have similar enough interfaces


SlashCommandName = NewType("SlashCommandName", ValidSlashField)
OptionName = constr(min_length=1, max_length=100)


class SoundCommand(BaseModel):
    name: ValidSlashField
    sound: SoundName


class CommandOption(BaseModel):
    name: OptionName
    sound: SoundName
    default: bool = False


CommandOptionList = conlist(CommandOption, min_items=1)


class OptionsCommand(BaseModel):
    name: ValidSlashField
    optionname: ValidSlashField = ValidSlashField("sound")
    options: CommandOptionList

    @validator("options")
    def check_options_defaults(cls, value: CommandOptionList) -> CommandOptionList:
        defaultscount = 0
        for op in value:
            if op.default:
                defaultscount += 1
        if defaultscount > 1:
            raise ValueError("Too many defaults given")
        return value


class SubcommandsCommand(BaseModel):
    name: ValidSlashField
    subcommands: List[AnyCommand]

    MAX_DEPTH = 2

    def validate_depth(self, current: int):
        if current >= self.MAX_DEPTH:
            raise ValueError(f"Subcommand {self.name} too deep")
        for cmd in self.subcommands:
            if isinstance(cmd, SubcommandsCommand):
                cmd.validate_depth(current + 1)


AnyCommand = Union[SoundCommand, OptionsCommand, SubcommandsCommand]


SubcommandsCommand.update_forward_refs()


class CommandsJson(BaseModel):
    version: Literal[1]
    commands: List[AnyCommand]

    @validator("commands")
    def validate_subcommand_depth(cls, cmds: List[AnyCommand]):
        for cmd in cmds:
            if isinstance(cmd, SubcommandsCommand):
                cmd.validate_depth(0)
