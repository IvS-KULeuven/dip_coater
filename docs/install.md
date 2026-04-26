# Install the App

Use this page when setting up the project on a Raspberry Pi or on a normal computer for testing.

## What You Need

- Python 3.10 or newer
- this project folder
- a terminal

The commands below assume you are inside the project folder.

```bash
cd /path/to/dip_coater
```

## Recommended: pip

Create a virtual environment:

```bash
python3 -m venv venv --prompt=dip-coater
source venv/bin/activate
```

Upgrade pip:

```bash
python3 -m pip install --upgrade pip
```

Install the app:

```bash
python3 -m pip install -e .
```

Then check that the app command exists:

```bash
dip-coater --help
```

## Raspberry Pi Install

On a Raspberry Pi with GPIO hardware, install the Raspberry Pi extra:

```bash
python3 -m pip install -e ".[rpi]"
```

## Alternative: uv

If you already use uv, you can install and run the project with:

```bash
uv sync
uv run dip-coater --help
```

On a Raspberry Pi with GPIO hardware:

```bash
uv sync --extra rpi
```

## Install Documentation Tools

The documentation website is optional. Install it only if you want to preview or publish the docs.

With pip:

```bash
python3 -m pip install -e ".[docs]"
```

Preview the website:

```bash
mkdocs serve
```

With uv:

```bash
uv sync --extra docs
```

Preview with uv:

```bash
uv run --extra docs mkdocs serve
```

## First Test Without Hardware

Before connecting hardware, you can test that the app opens:

```bash
dip-coater --driver TMC5160 --use-dummy-driver
```

If the app opens, the software installation is working.
