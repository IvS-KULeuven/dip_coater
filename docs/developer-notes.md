# Developer Notes

This page is for maintainers and developers.

For machine setup profiles, geometry, and limit-switch configuration, see
[Developer Setup Profiles](developer-setups.md).

## Run Tests

Run all non-hardware tests:

```bash
uv run pytest -q -m "not hardware"
```

Run the same branch-coverage gate used by CI:

```bash
uv run pytest -q -m "not hardware" --cov=dip_coater --cov=trinamic_wrapper \
  --cov-branch --cov-report=term-missing --cov-report=xml
```

The configured floor is 80% across the application and Trinamic wrapper. Raise
it as coverage improves; do not lower it to accommodate untested changes.

Run the real Textual application against all dummy backends, including button
dispatch, motion, shutdown, session events, and simulated TMC5160 homing:

```bash
uv run pytest -q src/test/test_app_integration.py
```

These are full application tests but never access physical hardware. They use
the same `initialize_runtime()` construction path as the command-line entry
point.

## Gradual typing

Run the current static-analysis scope with:

```bash
uv run mypy
```

The `[tool.mypy]` `files` list in `pyproject.toml` deliberately starts with the
mechanical model, machine profiles, driver interface, and motion service. New
code in those boundaries must keep the check green. Expand the list one module
at a time, fixing that module's errors in the same commit; do not silence whole
packages to make the scope appear larger.

Run hardware tests only when the correct hardware is connected.

The main CI workflow runs the non-hardware suite on the minimum supported
Python (3.10), current Python (3.14), and Windows. Separate jobs lint the whole
repository, build the documentation strictly, build both distributions, and
launch the installed wheel outside the source tree.

## TMC5160 Hardware Tests

Set the hardware port:

```bash
DIP_COATER_TMC5160_HARDWARE=1 \
DIP_COATER_TMC5160_PORT=/dev/tty.usbmodemTMCEVAL1 \
uv run pytest -m "hardware and not hardware_motion" src/test/test_tmc5160_hardware.py
```

Optional motion smoke test:

```bash
DIP_COATER_TMC5160_HARDWARE=1 \
DIP_COATER_TMC5160_PORT=/dev/tty.usbmodemTMCEVAL1 \
DIP_COATER_TMC5160_RUN_MOTION=1 \
uv run pytest -m hardware_motion src/test/test_tmc5160_hardware.py
```

Supported hardware-test variables:

| Variable | Meaning |
|---|---|
| `DIP_COATER_TMC5160_HARDWARE` | Required explicit hardware opt-in; set to `1` |
| `DIP_COATER_TMC5160_PORT` | Required serial port |
| `DIP_COATER_TMC5160_INTERFACE` | Interface type, defaults to `usb_tmcl` |
| `DIP_COATER_TMC5160_STEP_MODE` | Step mode, defaults to `16` |
| `DIP_COATER_TMC5160_CURRENT_MA` | Run current, defaults to `500` |
| `DIP_COATER_TMC5160_STANDSTILL_MA` | Standstill current, defaults to `0` |
| `DIP_COATER_TMC5160_STANDSTILL_NONZERO_MA` | Non-zero standstill check current, defaults to `140` |
| `DIP_COATER_TMC5160_RSENSE_MOHM` | Sense resistor value, defaults to `75` |
| `DIP_COATER_TMC5160_RUN_MOTION` | Separate motion opt-in; set to `1` |

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

## Publish to PyPI

Use this when releasing a new package version for `pip install dip-coater`.
PyPI package versions are immutable, so bump `project.version` in
`pyproject.toml` before building if that version has already been uploaded.

1. Update the version in `pyproject.toml`.

2. Refresh the lock file after changing package metadata:

   ```bash
   uv lock
   ```

3. Run the non-hardware tests:

   ```bash
   uv run pytest -q -m "not hardware"
   ```

4. Build fresh distributions:

   ```bash
   uv build --clear
   ```

5. Inspect the wheel metadata before uploading:

   ```bash
   unzip -p dist/dip_coater-<version>-py3-none-any.whl \
     dip_coater-<version>.dist-info/METADATA
   ```

   For Windows compatibility, confirm the metadata includes these environment
   markers:

   ```text
   Requires-Dist: uvloop>=0.19.0; sys_platform != "win32"
   Requires-Dist: winloop; sys_platform == "win32"
   ```

6. Dry-run the upload:

   ```bash
   uv publish --dry-run
   ```

7. Upload to PyPI with a project API token:

   ```bash
   export UV_PUBLISH_TOKEN="pypi-..."
   uv publish
   ```

8. Verify the published package from a clean environment:

   ```bash
   python -m pip install --upgrade --no-cache-dir dip-coater==<version>
   dip-coater --version
   ```

For a Windows install check, use PowerShell:

```powershell
py -m pip install --upgrade --no-cache-dir dip-coater==<version>
dip-coater --version
```

## Publish With GitHub Pages

The active [`.github/workflows/docs.yml`](https://github.com/IvS-KULeuven/dip_coater/blob/develop/.github/workflows/docs.yml)
workflow builds the strict MkDocs site, uploads a GitHub Pages artifact, and
deploys it through the repository's `github-pages` environment. It runs after
documentation, MkDocs configuration, dependency, or public API source changes
on `develop`, and can also be started manually.

Configure the repository's Pages source as **GitHub Actions**. Do not publish a
separate `gh-pages` branch from a developer workstation.

## Hardware-in-the-loop tests

Hardware tests are deliberately excluded from normal CI and require a supervised,
secured bench. Check that the mechanism is restrained, travel is unobstructed,
limit switches and the physical emergency stop work, and the configured current is
safe for the attached motor before arming a test.

The Trinamic wrapper suite has two independent gates. Safe register and current
checks require `--run-hardware`; tests that rotate the motor additionally require
`--run-hardware-motion`:

```console
uv run pytest src/trinamic_wrapper/tests/hardware -m "hardware and not hardware_motion" \
  --run-hardware --hw-port=/dev/tty.usbmodemTMCEVAL1 --hw-chip=TMC5160 \
  --hw-current-mA=500 --hw-max-mA=1000
```

The application-level TMC5160 and TMC2209 suites use the equivalent
`DIP_COATER_TMC5160_HARDWARE=1` and `DIP_COATER_TMC2209_HARDWARE=1`
environment gates. Their motion tests need a separate `*_RUN_MOTION=1` flag.
All fixtures stop, disable, and clean up their driver even when a test fails.

The manual **Hardware-in-the-loop tests** GitHub Actions workflow selects one
self-hosted hardware bench. Non-motion checks run first. Motion is optional and
runs only after those checks pass and a reviewer approves the protected
`dip-coater-hardware-motion` environment. Configure runner labels and serial-port
repository variables before using the workflow; a missing port fails rather than
silently passing a skipped test. Keep each self-hosted Actions runner at version
2.329.0 or newer so the Node 24-based actions can run.

## Documentation Style

Write for users who are operating a machine, not for Python developers.

Good docs should:

- show the exact command to run
- say what the user should see next
- explain what to check before moving hardware
- prefer short procedures over long explanations
- put dangerous actions in warnings
