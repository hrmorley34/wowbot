# Wowbot

[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![GitHub Workflow Status](https://img.shields.io/github/workflow/status/hrmorley34/wowbot/pre-commit?label=pre-commit&logo=github)](https://github.com/hrmorley34/wowbot/actions/workflows/pre-commit.yml?query=branch%3Amain)

[![GitHub Workflow Status](https://img.shields.io/github/workflow/status/hrmorley34/wowbot/test?label=test&logo=github)](https://github.com/hrmorley34/wowbot/actions/workflows/test.yml?query=branch%3Amain)

-----

**Table of Contents**

- [Command Line Interface](#command-line-interface)
- [Hatch commands](#hatch-commands)
- [License](#license)

## Command Line Interface

The package installs two commands:

- `wowbot` - runs the bot
    - Reads the `DISCORD_BOT_TOKEN` and `WOWBOT_SOUNDS_DIR` environmental variables
- `wowbot-sounds` - validates sounds
    - `wowbot-sounds check FOLDER` - validates a sound folder

## Hatch commands

If you do not have `hatch` on your path, you can use `pipx hatch` or install it with `pip install hatch`.

- `hatch run bot` - runs the bot
- `hatch run wowbot-sounds [args]` - runs the sound validator
- `hatch run test:cov` - runs the tests, printing the coverage to the terminal
    - `hatch run test:cov-file` - write the coverage to an HTML file, and an XML file
    - `hatch run test:no-cov` - don't write coverage data
    - `hatch run testall:cov` - runs the tests in Python 3.8, 3.9, and 3.10
- `hatch run docs:html` - build the Sphinx documentation
    - `hatch run docs:clean` - remove the built documentation

## License

`wowbot` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
