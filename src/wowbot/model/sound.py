from __future__ import annotations

__all__ = [
    "SoundName",
    "SoundFileABC",
    "Filename",
    "Weighted",
    "Filenames",
    "GlobFile",
    "SoundFile",
    "Sound",
    "ResolvedSound",
    "SoundsJson",
    "SoundCollection",
]

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Literal, NewType, Union

from pydantic import conint, conlist

from .errors import BaseModelError, ContextModelError, ErrorCollection, context
from .model import BaseModel, RootModel

SoundName = NewType("SoundName", str)


class SoundNameReuseError(ContextModelError):
    """Error for a sound name which is re-used by multiple sounds

    .. autoattribute:: name
    .. autoattribute:: context
    """

    name: SoundName
    """The re-used name"""

    def __init__(self, name: SoundName) -> None:
        self.name = name
        super().__init__(f"Re-use of name {name}")


class SoundFileNotFoundError(ContextModelError):
    """Error for a sound file which does not exist

    .. autoattribute:: filename
    .. autoattribute:: filepath
    .. autoattribute:: context
    """

    filename: Path
    """The name of the missing file"""

    filepath: Path
    """The non-existant path"""

    def __init__(self, filename: Path, filepath: Path) -> None:
        self.filename = filename
        self.filepath = filepath
        super().__init__(f"File {filepath} does not exist")


class EmptyGlobError(ContextModelError):
    """Error for a sound file which does not exist

    .. autoattribute:: pattern
    .. autoattribute:: context
    """

    pattern: str
    """The glob pattern"""

    def __init__(self, pattern: str) -> None:
        self.pattern = pattern
        super().__init__(f"Glob {pattern} has no matches")


class SoundFileABC(BaseModel, ABC):
    """An abstract representation of a collection of files with a weight

    .. automethod:: resolve_files
    .. automethod:: get_weight
    """

    @abstractmethod
    def resolve_files(self, root: Path) -> List[Path]:
        """Resolve the paths relative to root"""
        ...  # no cov

    @abstractmethod
    def get_weight(self) -> int:
        """Get the relative weight of this group of files"""
        ...  # no cov


class Filename(SoundFileABC, RootModel[str]):
    """A single filename with weight 1

    .. autoattribute:: root

    .. automethod:: resolve_files
    .. automethod:: get_weight
    """

    root: str
    """The file path"""

    def resolve_files(self, root: Path) -> List[Path]:
        """Resolve the path relative to root"""
        path = root / self.root
        if not path.exists():
            with context("root"):
                raise SoundFileNotFoundError(Path(self.root), path)
        return [path]

    def get_weight(self) -> int:
        """Get the chance weight of this file

        This will always be 1."""
        return 1


if TYPE_CHECKING:
    _WeightType = int
else:
    _WeightType = conint(gt=0, strict=True)  # strict prevents conversion from float


class Weighted(SoundFileABC):
    """A group of files with a weight attribute

    .. autoattribute:: weight

    .. automethod:: resolve_files
    .. automethod:: get_weight
    """

    weight: _WeightType = 1
    """The chance weight of this group of files being picked

    This must be greater than 0
    """

    def get_weight(self) -> int:
        """Get the relative weight of this file"""
        return self.weight


if TYPE_CHECKING:
    _NonEmptyStringList = list[str]
else:
    _NonEmptyStringList = conlist(str, min_length=1)


class Filenames(Weighted):
    """A list of files with a weight attribute

    .. autoattribute:: filenames
    .. autoattribute:: weight

    .. automethod:: resolve_files
    .. automethod:: get_weight
    """

    filenames: _NonEmptyStringList
    """A list of file paths

    This must be non-empty
    """

    def resolve_files(self, root: Path) -> List[Path]:
        """Resolve the paths relative to root"""
        paths: List[Path] = []
        missing: List[SoundFileNotFoundError] = []

        with context("filenames"):
            for index, name in enumerate(self.filenames):
                path = root / name
                paths.append(path)
                if not path.exists():
                    with context(index):
                        missing.append(SoundFileNotFoundError(Path(name), path))

        if missing:
            raise ErrorCollection(*missing)
        return paths


class GlobFile(Weighted):
    """A glob path with a weight attribute

    .. autoattribute:: glob
    .. autoattribute:: weight

    .. automethod:: resolve_files
    .. automethod:: get_weight
    """

    glob: str
    """A glob pattern

    This pattern is expanded in resolve_files into a list of files.
    """

    def resolve_files(self, root: Path) -> List[Path]:
        """Resolve the glob into paths relative to root"""
        paths = list(root.glob(self.glob))
        if not paths:
            with context("glob"):
                raise EmptyGlobError(self.glob)
        return paths


SoundFile = Union[Filename, Filenames, GlobFile]
if TYPE_CHECKING:
    _NonEmptySoundFileList = list[SoundFile]
else:
    _NonEmptySoundFileList = conlist(SoundFile, min_length=1)


class Sound(BaseModel):
    """A sound, containing multiple files

    .. autoattribute:: name
    .. autoattribute:: files

    .. automethod:: resolve_files
    """

    name: SoundName
    """The name of the sound"""
    files: _NonEmptySoundFileList
    """The files and weights

    This must be non-empty
    """

    def resolve_files(self, root: Path) -> ResolvedSound:
        """Resolve all paths relative to root"""
        groups: List[List[Path]] = []
        weights: List[int] = []

        errors: List[BaseModelError] = []

        with context("files"):
            for index, file in enumerate(self.files):
                try:
                    with context(index):
                        groups.append(file.resolve_files(root))
                        weights.append(file.get_weight())
                except BaseModelError as err:
                    errors.append(err)

        if errors:
            raise ErrorCollection(*errors)

        return ResolvedSound(name=self.name, filegroups=groups, groupweights=weights)


@dataclass
class ResolvedSound:
    """A sound, containing multiple files

    .. autoattribute:: name
    .. autoattribute:: filegroups
    .. autoattribute:: groupweights

    .. automethod:: random
    """

    name: SoundName
    """The name of the sound"""
    filegroups: List[List[Path]]
    """A list of groups of paths"""
    groupweights: List[int]
    """A list of weights, corresponding to the elements of filegroups"""

    def random(self) -> Path:
        """Select a random file

        This selects a random group, with groups biased by weight from groupweights.
        Then from this group, a file is randomly chosen, without bias.
        """
        group = random.choices(self.filegroups, self.groupweights, k=1)[0]
        return random.choice(group)


class SoundsJson(BaseModel):
    """Model representing a :doc:`sounds.json </sounds/sounds>` file

    .. autoattribute:: version
    .. autoattribute:: sounds

    .. automethod:: resolve_files"""

    version: Literal[1]
    """The version of the file. This must be 1."""
    sounds: List[Sound]
    """The list of sounds"""

    def resolve_files(self, root: Path) -> SoundCollection:
        """Resolve the paths of all sounds relative to root"""
        collection: SoundCollection = dict()
        errors: List[BaseModelError] = []

        with context("sounds"):
            for index, sound in enumerate(self.sounds):
                with context(index):
                    if sound.name in collection:
                        with context("name"):
                            errors.append(SoundNameReuseError(sound.name))
                    try:
                        collection[sound.name] = sound.resolve_files(root)
                    except BaseModelError as err:
                        errors.append(err)
                        # Allocate the key anyway, for re-use checks
                        collection[sound.name] = None  # type: ignore

        if errors:
            raise ErrorCollection(*errors)
        return collection


SoundCollection = Dict[SoundName, ResolvedSound]
