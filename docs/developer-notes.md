# Developer Notes

This page is for maintainers and developers.

## Run Tests

Run all non-hardware tests:

```bash
uv run pytest -q -m "not hardware"
```

Run hardware tests only when the correct hardware is connected.

## TMC5160 Hardware Tests

Set the hardware port:

```bash
DIP_COATER_TMC5160_PORT=/dev/tty.usbmodemTMCEVAL1 \
uv run pytest -m hardware src/test/test_tmc5160_hardware.py
```

Optional motion smoke test:

```bash
DIP_COATER_TMC5160_PORT=/dev/tty.usbmodemTMCEVAL1 \
DIP_COATER_TMC5160_RUN_MOTION=1 \
uv run pytest -m hardware src/test/test_tmc5160_hardware.py
```

Supported hardware-test variables:

| Variable | Meaning |
|---|---|
| `DIP_COATER_TMC5160_PORT` | Required serial port |
| `DIP_COATER_TMC5160_INTERFACE` | Interface type, defaults to `usb_tmcl` |
| `DIP_COATER_TMC5160_STEP_MODE` | Step mode, defaults to `16` |
| `DIP_COATER_TMC5160_CURRENT_MA` | Run current, defaults to `500` |
| `DIP_COATER_TMC5160_STANDSTILL_MA` | Standstill current, defaults to `0` |
| `DIP_COATER_TMC5160_STANDSTILL_NONZERO_MA` | Non-zero standstill check current, defaults to `140` |
| `DIP_COATER_TMC5160_RSENSE_MOHM` | Sense resistor value, defaults to `75` |

## Build the Docs

Install docs dependencies:

```bash
uv sync --extra docs
```

Preview:

```bash
uv run --extra docs mkdocs serve
```

Build:

```bash
uv run --extra docs mkdocs build
```

## Publish With GitHub Pages

One simple option is to use GitHub Actions:

```yaml
name: docs

on:
  push:
    branches: [main]

permissions:
  contents: write

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - uses: astral-sh/setup-uv@v5
      - run: uv run --extra docs mkdocs gh-deploy --force
```

Then enable GitHub Pages for the `gh-pages` branch in the repository settings.

## Documentation Style

Write for users who are operating a machine, not for Python developers.

Good docs should:

- show the exact command to run
- say what the user should see next
- explain what to check before moving hardware
- prefer short procedures over long explanations
- put dangerous actions in warnings
