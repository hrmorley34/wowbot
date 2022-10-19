from pathlib import Path

from wowbot.model.main import app


class TestCliSounds:
    ROOT = Path("tests/sounds")

    def test_app_runs(self):
        try:
            app(["check", str(self.ROOT)])
        except SystemExit as ex:
            exit_code = ex.code
        else:
            exit_code = 0

        assert exit_code == 0
