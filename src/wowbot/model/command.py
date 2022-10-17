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

from typing import Iterable, List, Literal, NewType, Union

import regex
from pydantic import ConstrainedStr, conlist, constr, validator

from .model import BaseModel
from .sound import SoundCollection, SoundName

# https://discord.com/developers/docs/interactions/application-commands#application-command-object-application-command-naming
_ValidSlashFieldType = regex.compile(r"^[-_\p{L}\p{N}\p{sc=Deva}\p{sc=Thai}]{1,32}$")


class ValidSlashField(ConstrainedStr):
    regex = _ValidSlashFieldType  # type: ignore - regex and re have similar enough interfaces


SlashCommandName = NewType("SlashCommandName", ValidSlashField)
ChoiceName = constr(min_length=1, max_length=100)


class SoundCommand(BaseModel):
    """A command which plays a single sound

    .. autoattribute:: name
    .. autoattribute:: sound

    .. automethod:: check_sounds
    """

    name: ValidSlashField
    """The name of this command"""
    sound: SoundName
    """The sound to play"""

    def check_sounds(self, sound_names: set[SoundName]):
        """Verifies that the sounds name exists in :code:`sound_names`"""
        if self.sound not in sound_names:
            raise Exception(f"Sound {self.sound} doesn't exist")


class CommandChoice(BaseModel):
    """A single choice for a ChoiceCommand's option

    .. autoattribute:: name
    .. autoattribute:: sound
    .. autoattribute:: default
    """

    name: ChoiceName
    """The displayed name of the option"""
    sound: SoundName
    """The played sound of the option"""
    default: bool = False
    """Whether this option is the default option"""


# https://discord.com/developers/docs/interactions/application-commands#application-command-object-application-command-option-structure
# choice? - max 25
CommandChoiceList = conlist(CommandChoice, min_items=1, max_items=25)


class ChoiceCommand(BaseModel):
    """A command with a choice option

    .. autoattribute:: name
    .. autoattribute:: optionname
    .. autoattribute:: choices

    .. automethod:: get_default_choice
    .. automethod:: check_sounds
    """

    name: ValidSlashField
    """The name of this command"""
    optionname: ValidSlashField = ValidSlashField("sound")
    """The name of the option for this command"""
    choices: CommandChoiceList
    """The options to choose between

    There must be between 1 and 25 options, of which only 0 or 1 can have default
    set to True"""

    @validator("choices")
    def check_choices_defaults(cls, value: CommandChoiceList) -> CommandChoiceList:
        """Verifies that only 0 or 1 choices are set as the default"""
        defaultscount = 0
        for op in value:
            if op.default:
                defaultscount += 1
        if defaultscount > 1:
            raise ValueError("Too many defaults given")
        return value

    def get_default_choice(self) -> CommandChoice | None:
        """Returns the default CommandChoice if none is passed to the command

        If there is no default, None is returned."""
        return next((op for op in self.choices if op.default), None)

    def check_sounds(self, sound_names: set[SoundName]):
        """Verifies that the names of sounds in the options exist in :code:`sound_names`"""
        for choice in self.choices:
            if choice.sound not in sound_names:
                raise Exception(f"Sound {choice.sound} doesn't exist")


class SubcommandsCommand(BaseModel):
    """A group of subcommands

    .. autoattribute:: name
    .. autoattribute:: subcommands
    .. autoattribute:: MAX_DEPTH

    .. automethod:: check_sounds
    """

    name: ValidSlashField
    """The name of this command group"""
    subcommands: List[AnyCommand]
    """The subcommands of this command"""

    MAX_DEPTH = 2
    """The maximum depth of a nested subcommand"""

    def validate_depth(self, current: int):
        """Verifies recursively that the subcommands have a limited depth"""
        if current >= self.MAX_DEPTH:
            raise ValueError(f"Subcommand {self.name} too deep")
        for cmd in self.subcommands:
            if isinstance(cmd, SubcommandsCommand):
                cmd.validate_depth(current + 1)

    def check_sounds(self, sound_names: set[SoundName]):
        """Verifies recursively that all sounds referenced by commands exist in :code:`sound_names`"""
        for cmd in self.subcommands:
            cmd.check_sounds(sound_names)


AnyCommand = Union[SoundCommand, ChoiceCommand, SubcommandsCommand]


SubcommandsCommand.update_forward_refs()


class CommandsJson(BaseModel):
    """Model representing a :doc:`commands.json </sounds/commands>` file

    .. autoattribute:: version
    .. autoattribute:: commands

    .. automethod:: check_sounds
    """

    version: Literal[1]
    """The version of the file. This must be 1."""
    commands: List[AnyCommand]
    """The list of commands."""

    @validator("commands")
    def validate_subcommand_depth(cls, cmds: List[AnyCommand]):
        """Verifies recursively that the subcommands have a limited depth"""
        for cmd in cmds:
            if isinstance(cmd, SubcommandsCommand):
                cmd.validate_depth(0)
        return cmds

    def check_sounds(self, sound_names: Iterable[SoundName] | SoundCollection):
        """Verifies recursively that all sounds referenced by commands exist in :code:`sound_names`"""
        sound_names = set(sound_names)
        for cmd in self.commands:
            cmd.check_sounds(sound_names)
