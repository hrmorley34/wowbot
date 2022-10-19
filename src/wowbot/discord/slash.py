from __future__ import annotations

from typing import Union

from discord import (
    ApplicationContext,
    Cog,
    Option,
    OptionChoice,
    SlashCommand,
    SlashCommandGroup,
)

from wowbot.model.soundsdir import SoundsDir

from ..model.command import (
    AnyCommand,
    ChoiceCommand,
    CommandsJson,
    SoundCommand,
    SubcommandsCommand,
)
from ..model.sound import SoundCollection, SoundName
from .sound import play_sound


class SoundSlashCommand(SlashCommand):
    @classmethod
    def from_cmd(
        cls,
        cmd: SoundCommand,
        sounds: SoundCollection,
        parent: SlashCommandGroup | None = None,
    ) -> "SoundSlashCommand":
        return cls(cls.make_callback(cmd, sounds), name=cmd.name, parent=parent)

    @staticmethod
    def make_callback(cmd: SoundCommand, sounds: SoundCollection):
        sound = sounds[cmd.sound]

        async def callback(self: BaseSoundsCog, ctx: ApplicationContext):
            await play_sound(ctx, sound)

        return callback


class ChoiceSlashCommand(SlashCommand):
    @classmethod
    def from_cmd(
        cls,
        cmd: ChoiceCommand,
        sounds: SoundCollection,
        parent: SlashCommandGroup | None = None,
    ) -> "ChoiceSlashCommand":
        choices = [OptionChoice(opt.name, opt.sound) for opt in cmd.choices]
        default = cmd.get_default_choice()
        opt = Option(
            str,
            name=cmd.optionname,
            choices=choices,
            default=None if default is None else default.sound,
            required=default is None,
        )
        return cls(
            cls.make_callback(cmd, sounds), name=cmd.name, options=[opt], parent=parent
        )

    @staticmethod
    def make_callback(cmd: ChoiceCommand, sounds: SoundCollection):
        async def callback(
            self: BaseSoundsCog, ctx: ApplicationContext, choice: SoundName
        ):
            await play_sound(ctx, sounds[choice])

        return callback


class SubcommandsSlashCommand(SlashCommandGroup):
    @classmethod
    def from_cmd(
        cls,
        cmd: SubcommandsCommand,
        sounds: SoundCollection,
        parent: SlashCommandGroup | None = None,
    ) -> "SubcommandsSlashCommand":
        self = cls(name=cmd.name, parent=parent)

        for subcmd in cmd.subcommands:
            appcmd = make_command(subcmd, sounds, parent=self)
            self.subcommands.append(appcmd)

        return self


AnySlashCommand = Union[SoundSlashCommand, ChoiceSlashCommand, SubcommandsSlashCommand]


def make_command(
    cmd: AnyCommand, sounds: SoundCollection, parent: SlashCommandGroup | None = None
) -> AnySlashCommand:
    if isinstance(cmd, ChoiceCommand):
        return ChoiceSlashCommand.from_cmd(cmd, sounds, parent=parent)
    elif isinstance(cmd, SubcommandsCommand):
        return SubcommandsSlashCommand.from_cmd(cmd, sounds, parent=parent)
    else:
        assert isinstance(cmd, SoundCommand)
        return SoundSlashCommand.from_cmd(cmd, sounds, parent=parent)


class BaseSoundsCog(Cog):
    pass


COG_NAME = "SoundsCog"


def make_cog_type(cmds: CommandsJson, sounds: SoundCollection) -> type[BaseSoundsCog]:
    members = {}
    for cmd in cmds.commands:
        members[cmd.name] = make_command(cmd, sounds)
    return type(COG_NAME, (BaseSoundsCog,), members)


def make_cog(soundsdir: SoundsDir) -> BaseSoundsCog:
    SoundsCog = make_cog_type(soundsdir.commands_json, soundsdir.sound_collection)
    return SoundsCog()
