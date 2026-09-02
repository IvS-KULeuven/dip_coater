# Dip Coater

Dip Coater is a terminal application for controlling a motorized dip coater. It supports manual motion, homing, absolute positioning, logging, advanced motor settings, and simple scripted coating routines.

The app is built with [Textual](https://www.textualize.io/). It supports `TMC2209`, `TMC2660`, and `TMC5160` motor drivers.

## Start Here

The user [documentation](https://ivs-kuleuven.github.io/dip_coater/) is published
with GitHub Pages.

- [Install the app](https://ivs-kuleuven.github.io/dip_coater/install/)
- [Connect the hardware](https://ivs-kuleuven.github.io/dip_coater/hardware-setup/)
- [Run the app](https://ivs-kuleuven.github.io/dip_coater/run-the-app/)
- [Use the interface](https://ivs-kuleuven.github.io/dip_coater/using-the-ui/)
- [Write coating scripts](https://ivs-kuleuven.github.io/dip_coater/coder-api/)
- [Troubleshoot problems](https://ivs-kuleuven.github.io/dip_coater/troubleshooting/)
- [Developer and release notes](https://ivs-kuleuven.github.io/dip_coater/developer-notes/)

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

The documentation is published at
[ivs-kuleuven.github.io/dip_coater](https://ivs-kuleuven.github.io/dip_coater/).
Its Markdown sources are built with MkDocs.

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

Hardware tests are documented in
[Developer Notes](https://ivs-kuleuven.github.io/dip_coater/developer-notes/).
