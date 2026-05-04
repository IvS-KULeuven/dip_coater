# Install the App

Use this page when setting up the project on a Raspberry Pi or on a normal computer for testing.

## What You Need

- Python 3.10 or newer
- a terminal

## Recommended: pip

Create a virtual environment (optional):

```bash
python3 -m venv .venv --prompt=dip-coater
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
py -m venv .venv --prompt dip-coater
.\.venv\Scripts\Activate.ps1
```

On Windows Command Prompt:

```bat
py -m venv .venv --prompt dip-coater
.venv\Scripts\activate.bat
```

Upgrade pip (optional):

```bash
python3 -m pip install --upgrade pip
```

Install the app:

```bash
python3 -m pip install dip-coater
```

The Coder editor works without syntax highlighting by default. To install the
optional Python syntax-highlighting packages too:

```bash
python3 -m pip install "dip-coater[syntax]"
```

Then check that the app command exists:

```bash
dip-coater --version
```

## Raspberry Pi Install

On a Raspberry Pi with GPIO hardware, install the Raspberry Pi extra:

```bash
python3 -m pip install "dip-coater[rpi]"
```

This installs the GPIO backends used by both older Raspberry Pi boards
(`RPi.GPIO`) and Raspberry Pi 5 setups (`gpiozero` with `lgpio`).

## Source Checkout Install

Use this path only if you are running from a cloned source checkout, for example while developing the app or testing local changes.

```bash
git clone https://github.com/IvS-KULeuven/dip_coater.git
cd dip_coater
python3 -m venv .venv --prompt=dip-coater
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -e .
```

On Windows, use the same commands but activate the virtual environment with
`.\.venv\Scripts\Activate.ps1` in PowerShell or `.venv\Scripts\activate.bat`
in Command Prompt.

On a Raspberry Pi with GPIO hardware:

```bash
python3 -m pip install -e ".[rpi]"
```

## Alternative: uv

If you already use uv from a source checkout, you can install and run the project with:

```bash
uv sync
uv run dip-coater --version
```

On a Raspberry Pi with GPIO hardware:

```bash
uv sync --extra rpi
```

## Update the Software

Stop the app before updating it.

If you installed the normal package with pip, update it from the package index:

```bash
source .venv/bin/activate
python3 -m pip install --upgrade dip-coater
```

On Windows, activate the virtual environment with:

```powershell
.\.venv\Scripts\Activate.ps1
```

Or from Command Prompt:

```bat
.venv\Scripts\activate.bat
```

On a Raspberry Pi with GPIO hardware:

```bash
python3 -m pip install --upgrade "dip-coater[rpi]"
```

If you installed from a source checkout, update the local checkout first:

```bash
git pull
```

Then reinstall the editable package so command metadata and dependencies are refreshed:

```bash
python3 -m pip install --upgrade -e .
```

On a Raspberry Pi with GPIO hardware, include the Raspberry Pi extra:

```bash
python3 -m pip install --upgrade -e ".[rpi]"
```

If you installed from a source checkout with uv, refresh the environment instead:

```bash
uv sync
```

On a Raspberry Pi with GPIO hardware:

```bash
uv sync --extra rpi
```

Start the app again after updating. Check the version shown at the top of the UI and confirm that it matches the version you expected to install.

## Install Documentation Tools

The documentation website is optional. Install it only if you want to preview or publish the docs.

With pip:

```bash
python3 -m pip install "dip-coater[docs]"
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
