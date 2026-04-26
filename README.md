# Dip Coater

Dip Coater is a terminal application for controlling a motorized dip coater. It supports manual motion, homing, absolute positioning, logging, advanced motor settings, and simple scripted coating routines.

The app is built with [Textual](https://www.textualize.io/). It supports `TMC2209`, `TMC2660`, and `TMC5160` motor drivers.

## Start Here

The user documentation lives in [`docs/`](docs/index.md).

- [Install the app](docs/install.md)
- [Connect the hardware](docs/hardware-setup.md)
- [Run the app](docs/run-the-app.md)
- [Use the interface](docs/using-the-ui.md)
- [Write coating scripts](docs/coder-api.md)
- [Troubleshoot problems](docs/troubleshooting.md)

## Quick Run

After installation, start the app with:

```bash
dip-coater
```

To test the interface without real hardware:

```bash
dip-coater --driver TMC5160 --use-dummy-driver
```

For a TMC5160 evaluation board connected over USB-TMCL:

```bash
dip-coater --driver TMC5160 --interface usb_tmcl --port /dev/tty.usbmodemTMCEVAL1
```

## Documentation Website

The docs are written as Markdown and can be published with MkDocs.

Preview locally:

```bash
python3 -m pip install -e ".[docs]"
mkdocs serve
```

Then open the local URL printed by MkDocs.

Build the static site:

```bash
mkdocs build
```

## Development Checks

Run the non-hardware tests:

```bash
uv run pytest -q -m "not hardware"
```

Hardware tests are documented in [Developer Notes](docs/developer-notes.md).
