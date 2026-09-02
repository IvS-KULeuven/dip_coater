# Python Examples

The repository includes small, standalone Python examples in the `examples/` directory.
Each script is named after the driver it demonstrates and includes setup, safety notes, and runnable commands at the top of the file.

All examples use dummy drivers by default. Pass `--real-hardware` only when the lift is clear, powered, and supervised.

## Down/Up Motion Examples

| Driver | Setup profile | Script |
|---|---|---|
| `TMC2209` | `small` | `examples/tmc2209_example.py` |
| `TMC2660` | `large` (dummy only) | `examples/tmc2660_example.py` |
| `TMC5160` | `large` | `examples/tmc5160_example.py` |

Run a dummy example:

```bash
uv run python examples/tmc2209_example.py
uv run python examples/tmc2660_example.py
uv run python examples/tmc5160_example.py
```

Run with real hardware:

```bash
uv run python examples/tmc2209_example.py --real-hardware
uv run python examples/tmc5160_example.py --real-hardware --port /dev/ttyACM0
```

TMC2660 cannot read the `large` profile's driver-reference limit switches.
Consequently, the bundled TMC2660 example is simulation-only. Real TMC2660
hardware requires a separately verified GPIO-backed profile; the application
rejects `TMC2660` with `large` before opening the motor connection.

Each script builds the app state, selects the setup profile, creates the driver through the driver registry, wraps it in a `MotionController`, and moves down and back up.

## TMC5160 Homing And Positions

Use this script when you want a TMC5160 large-lift example that homes first and then moves to absolute positions:

```bash
uv run python examples/tmc5160_homing_example.py
```

Run with real hardware:

```bash
uv run python examples/tmc5160_homing_example.py --real-hardware --port /dev/ttyACM0
```

Edit `POSITION_MOVES` in the script to change target positions, speeds, and accelerations.
