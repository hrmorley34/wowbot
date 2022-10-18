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
from typing import Dict, List, Literal, NewType, Union

from pydantic import conint, conlist

from .model import BaseModel

SoundName = NewType("SoundName", str)


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


class Filename(SoundFileABC):
    """A single filename with weight 1

    .. autoattribute:: __root__

    .. automethod:: resolve_files
    .. automethod:: get_weight
    """

    __root__: str
    """The file path"""

    def resolve_files(self, root: Path) -> List[Path]:
        """Resolve the path relative to root"""
        path = root / self.__root__
        if not path.exists():
            raise FileNotFoundError(f"File {path} missing")
        return [path]

    def get_weight(self) -> int:
        """Get the chance weight of this file

        This will always be 1."""
        return 1


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


_NonEmptyStringList = conlist(str, min_items=1)


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
        paths = [root / name for name in self.filenames]
        missing = [p for p in paths if not p.exists()]
        if missing:
            raise FileNotFoundError("Files missing: " + ", ".join(map(str, missing)))
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
            raise Exception(f"No files in glob: {self.glob}")
        return paths


SoundFile = Union[Filename, Filenames, GlobFile]
_NonEmptySoundFileList = conlist(SoundFile, min_items=1)


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

        for file in self.files:
            groups.append(file.resolve_files(root))
            weights.append(file.get_weight())

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
        for sound in self.sounds:
            if sound.name in collection:
                raise Exception(f"Re-use of name: {sound.name}")
            collection[sound.name] = sound.resolve_files(root)
        return collection


SoundCollection = Dict[SoundName, ResolvedSound]
