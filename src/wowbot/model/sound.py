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
    @abstractmethod
    def resolve_files(self, root: Path) -> List[Path]:
        ...  # no cov

    @abstractmethod
    def get_weight(self) -> int:
        ...  # no cov


class Filename(SoundFileABC):
    __root__: str

    def resolve_files(self, root: Path) -> List[Path]:
        path = root / self.__root__
        if not path.exists():
            raise FileNotFoundError(f"File {path} missing")
        return [path]

    def get_weight(self) -> int:
        return 1


_WeightType = conint(gt=0, strict=True)  # strict prevents conversion from float


class Weighted(SoundFileABC):
    weight: _WeightType = 1

    def get_weight(self) -> int:
        return self.weight


_NonEmptyStringList = conlist(str, min_items=1)


class Filenames(Weighted):
    filenames: _NonEmptyStringList

    def resolve_files(self, root: Path) -> List[Path]:
        paths = [root / name for name in self.filenames]
        missing = [p for p in paths if not p.exists()]
        if missing:
            raise FileNotFoundError("Files missing: " + ", ".join(map(str, missing)))
        return paths


class GlobFile(Weighted):
    glob: str

    def resolve_files(self, root: Path) -> List[Path]:
        paths = list(root.glob(self.glob))
        if not paths:
            raise Exception(f"No files in glob: {self.glob}")
        return paths


SoundFile = Union[Filename, Filenames, GlobFile]
_NonEmptySoundFileList = conlist(SoundFile, min_items=1)


class Sound(BaseModel):
    name: SoundName
    files: _NonEmptySoundFileList

    def resolve_files(self, root: Path) -> ResolvedSound:
        groups: List[List[Path]] = []
        weights: List[int] = []

        for file in self.files:
            groups.append(file.resolve_files(root))
            weights.append(file.get_weight())

        return ResolvedSound(name=self.name, filegroups=groups, groupweights=weights)


@dataclass
class ResolvedSound:
    name: SoundName
    filegroups: List[List[Path]]
    groupweights: List[int]

    def random(self) -> Path:
        group = random.choices(self.filegroups, self.groupweights, k=1)[0]
        return random.choice(group)


class SoundsJson(BaseModel):
    version: Literal[1]
    sounds: List[Sound]

    def resolve_files(self, root: Path) -> SoundCollection:
        collection: SoundCollection = dict()
        for sound in self.sounds:
            if sound.name in collection:
                raise Exception(f"Re-use of name: {sound.name}")
            collection[sound.name] = sound.resolve_files(root)
        return collection


SoundCollection = Dict[SoundName, ResolvedSound]
