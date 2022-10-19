from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Generator

import pydantic
import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .command import CommandsJson, SoundNotFoundError
from .sound import (
    BaseModelError,
    ContextModelError,
    EmptyGlobError,
    ErrorCollection,
    SoundCollection,
    SoundFileNotFoundError,
    SoundNameReuseError,
    SoundsJson,
)
from .soundsdir import COMMANDS_FILE, SOUNDS_FILE

app = typer.Typer(no_args_is_help=True)


STYLE_FILENAME = "cyan underline"
STYLE_ERR = "red"
STYLE_LOC = "blue"
STYLE_LOC_ARROW = STYLE_ERR
STYLE_SUCCESS = "green"

STYLE_ERR_MSG = STYLE_ERR
STYLE_ERR_MSG_FILENAME = STYLE_FILENAME


def make_validation_error(
    err: pydantic.ValidationError, name: str
) -> Generator[Text, None, None]:
    errors = err.errors()
    plural = "Errors" if len(errors) else "Error"
    yield (
        Text(plural + " in ", STYLE_ERR_MSG)
        + Text(name, STYLE_ERR_MSG_FILENAME)
        + Text(":", STYLE_ERR_MSG)
    )
    for error in errors:
        loc_str = Text(" -> ", STYLE_LOC_ARROW).join(
            Text(str(e), STYLE_LOC) for e in error["loc"]
        )
        yield Text("  ", STYLE_ERR_MSG) + loc_str
        yield Text("    " + error["msg"], STYLE_ERR_MSG)


def make_validation_error_panel(err: pydantic.ValidationError, name: str) -> Panel:
    return Panel(Text("\n", STYLE_ERR_MSG).join(make_validation_error(err, name)))


def make_json_error_panel(err: json.JSONDecodeError, name: str) -> Panel:
    return Panel(
        Text("Error parsing ", STYLE_ERR_MSG)
        + Text(name, STYLE_ERR_MSG_FILENAME)
        + Text(":\n  Line ", STYLE_ERR_MSG)
        + Text(str(err.lineno), STYLE_LOC)
        + Text(" column ", STYLE_ERR_MSG)
        + Text(str(err.colno), STYLE_LOC)
        + Text(" (char ", STYLE_ERR_MSG)
        + Text(str(err.pos), STYLE_LOC)
        + Text(")\n    " + err.msg, STYLE_ERR_MSG)
    )


def make_resolve_error_panel(
    err: BaseModelError | ErrorCollection[BaseModelError],
) -> Panel:
    errs: tuple[BaseModelError, ...]
    if isinstance(err, ErrorCollection):
        errs = err.errors  # type: ignore
    else:
        errs = (err,)

    plural = "Error" if len(errs) == 1 else "Errors"
    err_text = Text(f"{plural} resolving sounds:", STYLE_ERR)
    for err in errs:
        err_text += Text("\n  ", STYLE_ERR_MSG)
        if isinstance(err, ContextModelError) and err.context is not None:
            err_text += Text(" -> ", STYLE_LOC_ARROW).join(
                Text(str(loc), STYLE_LOC) for loc in err.context
            ) + Text("\n    ", STYLE_ERR_MSG)

        if isinstance(err, SoundNameReuseError):
            err_text += (
                Text("Sound name ", STYLE_ERR_MSG)
                + Text(err.name, STYLE_ERR_MSG_FILENAME)
                + Text(" reused", STYLE_ERR_MSG)
            )
        elif isinstance(err, SoundFileNotFoundError):
            err_text += (
                Text("Sound file ", STYLE_ERR_MSG)
                + Text(str(err.filename), STYLE_ERR_MSG_FILENAME)
                + Text(" does not exist", STYLE_ERR_MSG)
            )
        elif isinstance(err, EmptyGlobError):
            err_text += (
                Text("Glob ", STYLE_ERR_MSG)
                + Text(err.pattern, STYLE_ERR_MSG_FILENAME)
                + Text(" does not match any files", STYLE_ERR_MSG)
            )
        else:
            err_text += Text(str(err), STYLE_ERR_MSG)

    return Panel(err_text)


def make_checksounds_error_panel(
    err: BaseModelError | ErrorCollection[BaseModelError],
) -> Panel:
    errs: tuple[BaseModelError, ...]
    if isinstance(err, ErrorCollection):
        errs = err.errors  # type: ignore
    else:
        errs = (err,)

    plural = "Error" if len(errs) == 1 else "Errors"
    err_text = Text(f"{plural} resolving sounds in {COMMANDS_FILE}:", STYLE_ERR)
    for err in errs:
        err_text += Text("\n  ", STYLE_ERR_MSG)
        if isinstance(err, ContextModelError) and err.context is not None:
            err_text += Text(" -> ", STYLE_LOC_ARROW).join(
                Text(str(loc), STYLE_LOC) for loc in err.context
            ) + Text("\n    ", STYLE_ERR_MSG)

        if isinstance(err, SoundNotFoundError):
            err_text += (
                Text("Sound name ", STYLE_ERR_MSG)
                + Text(err.name, STYLE_ERR_MSG_FILENAME)
                + Text(" does not exist", STYLE_ERR_MSG)
            )
        else:
            err_text += Text(str(err), STYLE_ERR_MSG)

    return Panel(err_text)


@app.command("check")
def check_folder(folder: Path) -> None:
    console = Console(markup=False)

    if not folder.is_dir():
        console.print(
            Text(str(folder), STYLE_ERR_MSG_FILENAME)
            + Text(" is not a folder!", STYLE_ERR_MSG),
        )
        raise typer.Exit(1)

    exit_code = 0

    sounds_path = folder / SOUNDS_FILE

    sounds_data: Any | None = None
    try:
        with open(sounds_path) as f:
            sounds_data = json.load(f)
    except json.JSONDecodeError as err:
        console.print(make_json_error_panel(err, SOUNDS_FILE))
        exit_code |= 1

    sounds: SoundsJson | None = None
    if sounds_data is not None:
        try:
            sounds = SoundsJson.parse_obj(sounds_data)
        except pydantic.ValidationError as err:
            console.print(make_validation_error_panel(err, SOUNDS_FILE))
            exit_code |= 1
        else:
            console.print(
                Text("Parsed ", STYLE_SUCCESS)
                + Text(SOUNDS_FILE, STYLE_FILENAME)
                + Text(".", STYLE_SUCCESS)
            )

    soundcol: SoundCollection | None = None
    if sounds is not None:
        try:
            soundcol = sounds.resolve_files(folder)
        except BaseModelError as err:
            console.print(make_resolve_error_panel(err))
            exit_code |= 1
        else:
            console.print(Text("Located sound files.", STYLE_SUCCESS))

    commands_path = folder / COMMANDS_FILE

    commands_data: Any | None = None
    try:
        with open(commands_path) as f:
            commands_data = json.load(f)
    except json.JSONDecodeError as err:
        console.print(make_json_error_panel(err, COMMANDS_FILE))
        exit_code |= 1

    commands: CommandsJson | None = None
    if commands_data is not None:
        try:
            commands = CommandsJson.parse_obj(commands_data)
        except pydantic.ValidationError as err:
            console.print(make_validation_error_panel(err, COMMANDS_FILE))
            exit_code |= 1
        else:
            console.print(
                Text("Parsed ", STYLE_SUCCESS)
                + Text(COMMANDS_FILE, STYLE_FILENAME)
                + Text(".", STYLE_SUCCESS)
            )

    if commands is not None and soundcol is not None:
        try:
            commands.check_sounds(soundcol)
        except BaseModelError as err:
            console.print(make_checksounds_error_panel(err))
            exit_code |= 1

    if exit_code:
        raise typer.Exit(exit_code)


@app.command("pass")
def pass_():
    raise typer.Exit(0)


if __name__ == "__main__":
    app()
