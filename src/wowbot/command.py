from __future__ import annotations

__all__ = [
    "SlashCommandName",
    "ChoiceName",
    "SoundCommand",
    "CommandChoice",
    "ChoiceCommand",
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
ChoiceName = constr(min_length=1, max_length=100)


class SoundCommand(BaseModel):
    name: ValidSlashField
    sound: SoundName


class CommandChoice(BaseModel):
    name: ChoiceName
    sound: SoundName
    default: bool = False


# https://discord.com/developers/docs/interactions/application-commands#application-command-object-application-command-option-structure
# choice? - max 25
CommandChoiceList = conlist(CommandChoice, min_items=1, max_items=25)


class ChoiceCommand(BaseModel):
    name: ValidSlashField
    optionname: ValidSlashField = ValidSlashField("sound")
    choices: CommandChoiceList

    @validator("choices")
    def check_choices_defaults(cls, value: CommandChoiceList) -> CommandChoiceList:
        defaultscount = 0
        for op in value:
            if op.default:
                defaultscount += 1
        if defaultscount > 1:
            raise ValueError("Too many defaults given")
        return value

    def get_default_choice(self) -> ChoiceName | None:
        return next((op.name for op in self.choices if op.default), None)


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


AnyCommand = Union[SoundCommand, ChoiceCommand, SubcommandsCommand]


SubcommandsCommand.update_forward_refs()


class CommandsJson(BaseModel):
    version: Literal[1]
    commands: List[AnyCommand]

    @validator("commands")
    def validate_subcommand_depth(cls, cmds: List[AnyCommand]):
        for cmd in cmds:
            if isinstance(cmd, SubcommandsCommand):
                cmd.validate_depth(0)
        return cmds
