# Install the App

Use this page when setting up the project on a Raspberry Pi or on a normal computer for testing.

## What You Need

- Python 3.10 or newer
- this project folder
- a terminal
- uv

The commands below assume you are inside the project folder.

```bash
cd /path/to/dip_coater
```

## Install uv

Install uv first:

```bash
python3 -m pip install uv
```

On a Raspberry Pi with GPIO hardware:

```bash
uv sync --extra rpi
```

On macOS, Linux, or Windows for testing without Raspberry Pi GPIO:

```bash
uv sync
```

Run commands inside the project environment with `uv run`:

```bash
uv run dip-coater --help
```

If you prefer to activate the environment manually:

```bash
source .venv/bin/activate
```

Then check that the app command exists:

```bash
dip-coater --help
```

## Alternative: Install With pip

You can still install the package into an existing virtual environment:

```bash
python3 -m venv venv --prompt=dip-coater
source venv/bin/activate
python3 -m pip install -e .
```

## Install Documentation Tools

The documentation website is optional. Install it only if you want to preview or publish the docs:

```bash
uv sync --extra docs
```

Preview the website:

```bash
uv run --extra docs mkdocs serve
```

## First Test Without Hardware

Before connecting hardware, you can test that the app opens:

```bash
uv run dip-coater --driver TMC5160 --use-dummy-driver
```

If the app opens, the software installation is working.
