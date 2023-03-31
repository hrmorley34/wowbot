# SPDX-FileCopyrightText: 2022-present hrmorley34 <henry@morley.org.uk>
#
# SPDX-License-Identifier: MIT
import json
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

import pytest
from pydantic import ValidationError

from wowbot.model.sound import (
    EmptyGlobError,
    SoundFileNotFoundError,
    SoundNameReuseError,
    SoundsJson,
)

from .utils import any_validation_error


class TestSoundsJson:
    ROOT = Path("tests/sounds")

    def test_wrong_version_fails(self):
        with open(self.ROOT / "sounds.json") as f:
            # known functional data, according to other test
            data = json.load(f)

        for version in {-1, 0, 2, 3, float("-inf"), float("NaN"), float("inf")}:
            data["version"] = version
            with pytest.raises(ValidationError) as excinfo:
                SoundsJson.parse_obj(data)
            assert any_validation_error(excinfo.value, loc=("version",))

    def test_missing_key_fails(self):
        with open(self.ROOT / "sounds.json") as f:
            # known functional data, according to other test
            data_original = json.load(f)

        for key in ["version", "sounds"]:
            data = data_original.copy()
            del data[key]
            with pytest.raises(ValidationError) as excinfo:
                SoundsJson.parse_obj(data)
            assert any_validation_error(excinfo.value, loc=(key,))

    def test_sounds_example(self):
        with open(self.ROOT / "sounds.json") as f:
            data = json.load(f)

        sj = SoundsJson.parse_obj(data)

        resolved = sj.resolve_files(self.ROOT)

        assert len(resolved) == 2

        for key in ["s.example", "s.mysound"]:
            assert key in resolved
            item = resolved[key].random()
            assert item.exists()

    @classmethod
    def get_data_from_files(cls, *files: Any) -> Any:
        return cls.get_data_from_sounds(cls.get_sound_from_files(*files))

    @staticmethod
    def get_sound_from_files(*files: Any, name: Optional[str] = None) -> Any:
        if name is None:
            name = str(uuid4())
        return {"name": name, "files": list(files)}

    @staticmethod
    def get_data_from_sounds(*sounds: Any) -> Any:
        return {"version": 1, "sounds": list(sounds)}

    def test_missing_file_fails(self):
        for element, ctx in [
            ("doesnotexist.opus", ("__root__",)),
            ({"filenames": ["doesnotexist.opus"]}, ("filenames", 0)),
            ({"filenames": ["example1.opus", "doesnotexist.opus"]}, ("filenames", 1)),
        ]:
            data = self.get_data_from_files(element)

            sj = SoundsJson.parse_obj(data)

            with pytest.raises(SoundFileNotFoundError) as exc_info:
                sj.resolve_files(self.ROOT)
            assert exc_info.value.context == ("sounds", 0, "files", 0) + ctx

    def test_empty_glob_fails(self):
        for element in [{"glob": "doesnotexist-*.opus"}, {"glob": "missing-*.opus"}]:
            data = self.get_data_from_files(element)

            sj = SoundsJson.parse_obj(data)

            with pytest.raises(EmptyGlobError) as exc_info:
                sj.resolve_files(self.ROOT)
            assert exc_info.value.pattern == element["glob"]
            assert exc_info.value.context == ("sounds", 0, "files", 0, "glob")

    def test_duplicate_names_fails(self):
        for name in ["s.duplicate1", "s.duplicate2"]:
            data = self.get_data_from_sounds(
                *(
                    self.get_sound_from_files(file, name=name)
                    for file in ["example1.opus", "example2.opus"]
                )
            )

            sj = SoundsJson.parse_obj(data)

            with pytest.raises(SoundNameReuseError) as exc_info:
                sj.resolve_files(self.ROOT)
            assert exc_info.value.name == name

    def test_no_files_fails(self):
        data = self.get_data_from_files()

        with pytest.raises(ValidationError) as excinfo:
            SoundsJson.parse_obj(data)
        assert any_validation_error(excinfo.value, loc=("sounds", 0, "files"))

    def test_invalid_weight_fails(self):
        for weight in [-100, -1, 0, 0.5, 1.0, 1.5]:
            file = {"filenames": ["example1.opus"], "weight": weight}
            data = self.get_data_from_files(file)

            with pytest.raises(ValidationError) as excinfo:
                SoundsJson.parse_obj(data)
            assert any_validation_error(
                excinfo.value, loc=("sounds", 0, "files", 0, "weight")
            )

    def test_extra_field_fails(self):
        with open(self.ROOT / "sounds.json") as f:
            # known functional data, according to other test
            data_original = json.load(f)

        for keys in [
            ("badkey",),
            ("sounds", 0, "badkey"),
            ("sounds", 0, "filenames"),
            ("sounds", 0, "glob"),
            ("sounds", 0, "weight"),
            ("sounds", 0, "files", 2, "badkey"),
            ("sounds", 1, "badkey"),
            ("sounds", 1, "filenames"),
            ("sounds", 1, "glob"),
            ("sounds", 1, "weight"),
            ("sounds", 1, "files", 0, "badkey"),
            ("sounds", 1, "files", 1, "badkey"),
        ]:
            data = data_original.copy()
            modify = data
            for key in keys[:-1]:
                modify = modify[key]
            modify[keys[-1]] = None

            with pytest.raises(ValidationError) as excinfo:
                SoundsJson.parse_obj(data)
            assert any_validation_error(
                excinfo.value, loc=keys, type="value_error.extra"
            )
