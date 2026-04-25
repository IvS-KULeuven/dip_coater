# Install the App

Use this page when setting up the project on a Raspberry Pi or on a normal computer for testing.

## What You Need

- Python 3.10 or newer
- this project folder
- a terminal
- Poetry, if you want the recommended installation method

The commands below assume you are inside the project folder.

```bash
cd /path/to/dip_coater
```

## Recommended: Poetry

Install Poetry first:

```bash
python3 -m pip install poetry
```

On a Raspberry Pi with GPIO hardware:

```bash
poetry install --with rpi
```

On macOS, Linux, or Windows for testing without Raspberry Pi GPIO:

```bash
poetry install
```

Start a shell inside the project environment:

```bash
poetry shell
```

Then check that the app command exists:

```bash
dip-coater --help
```

## Alternative: Python Virtual Environment

Create and activate a virtual environment:

```bash
python3 -m venv venv --prompt=dip-coater
source venv/bin/activate
```

Install the package in editable mode:

```bash
python3 -m pip install -e .
```

## Install Documentation Tools

The documentation website is optional. Install it only if you want to preview or publish the docs:

```bash
poetry install --with docs
```

Preview the website:

```bash
poetry run mkdocs serve
```

## First Test Without Hardware

Before connecting hardware, you can test that the app opens:

```bash
dip-coater --driver TMC5160 --use-dummy-driver
```

If the app opens, the software installation is working.
