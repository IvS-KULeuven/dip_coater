# trinamic_wrapper

A clean, chip-agnostic wrapper around [PyTrinamic](https://github.com/analogdevicesinc/PyTrinamic) for driving a TMC5160 or TMC2660 stepper driver through the Landungsbrücke evaluation interface.

The pytrinamic API exposes a lot of raw axis parameters and magic numbers. This wrapper hides that behind a small, typed interface that works the same for both chips, converts everything to/from physical units (mA, rev/s, rev/s²), validates inputs, and lets you ask whether an advanced feature is available before calling it.

## Install

```bash
pip install pytrinamic
# then drop the trinamic_wrapper/ folder in your project
```

## Quick start

```python
from trinamic_wrapper import (
    connection, create_motor, MotorConfig, Direction, StepMode,
)

with connection("/dev/tty.usbmodemTMCEVAL1") as conn:
    motor = create_motor(
        "TMC5160",                                      # or "TMC2660"
        conn,
        config=MotorConfig(
            full_steps_per_rev=200,
            sense_resistor_ohms=0.075,                  # 0.075 for 5160-EVAL, 0.1 for 2660-EVAL
        ),
    )

    motor.set_step_mode(StepMode.USTEP_256)
    motor.set_run_current_mA(800)
    motor.set_standstill_current_mA(200)
    motor.set_speed_rps(1.0)
    motor.set_acceleration_rps2(5.0)

    if motor.has_feature("stealthchop"):
        motor.set_stealthchop(True, threshold_rps=3.0)

    motor.enable()
    motor.rotate_by(2.0, direction=Direction.CW)
    motor.wait_until_reached(timeout_s=10.0)
    motor.disable()
```

## Connecting to the Landungsbrücke

The `connection()` context manager accepts any port string your OS uses for
the Landungsbrücke's USB-CDC device:

| OS      | Typical port                              |
|---------|-------------------------------------------|
| macOS   | `/dev/tty.usbmodemTMCEVAL1`               |
| Linux   | `/dev/ttyACM0` (or `/dev/serial/by-id/…`) |
| Windows | `COM7` (check Device Manager)             |

```python
from trinamic_wrapper import connection

# explicit port
with connection("/dev/tty.usbmodemTMCEVAL1") as conn: ...

# let pytrinamic pick the first available USB-TMCL device
with connection() as conn: ...

# interactive port picker
with connection("interactive") as conn: ...
```

Under the hood this just builds the argparse-style argv that pytrinamic's
`ConnectionManager` expects. If you'd rather drive it yourself, you can
still do the long form:

```python
from pytrinamic.connections import ConnectionManager
ConnectionManager(["--interface", "usb_tmcl", "--port", "/dev/ttyACM0"]).connect()
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│  StepperMotor (Protocol)   ← type-hint this     │
└──────────────────┬──────────────────────────────┘
                   │ is-a (duck-typed)
        ┌──────────┴──────────┐
        ▼                     ▼
  TMC5160Motor          TMC2660Motor
        │                     │
        └──────────┬──────────┘
                   ▼
           BaseStepperMotor (ABC)
                   │
                   ▼
            pytrinamic evalboard
                   │
                   ▼
          Landungsbrücke (TMCL)
```

- **`interface.py`** — `StepperMotor` Protocol. User code depends on this, never on a concrete class.
- **`config.py`** — `MotorConfig` dataclass with motor/driver parameters. `StepMode`, `Direction`, `RampMode` enums.
- **`conversions.py`** — pure math. Unit-convertible and unit-testable without hardware.
- **`motors/base.py`** — shared behaviour: soft current limits, position tracking, enable/disable semantics, step-mode handling.
- **`motors/tmc5160_motor.py`** — TMC5160-specific: ramp generator, StealthChop, TPWMTHRS, INTPOL via `CHOPCONF`, StallGuard2.
- **`motors/tmc2660_motor.py`** — TMC2660-specific: CS current encoding (5-bit), μsteps/s velocity, VSENSE handling. No StealthChop.
- **`factory.py`** — `create_motor(chip, connection, …)`.

## Unit conversion

Where the formulas come from:

**Current (mA ↔ CS, 5-bit)** — Both chips use the same RMS formula from their datasheets:

```
I_rms = (CS + 1)/32 · V_fs / (R_sense + R_offset) / √2
```

- TMC5160-EVAL: `R_sense=0.075 Ω`, `R_offset=0.02 Ω`, `V_fs=0.325 V` (standard)
- TMC2660-EVAL: `R_sense=0.1 Ω`, `R_offset=0.03 Ω`, `V_fs=0.305 V` (standard)

The Landungsbruecke firmware used here takes `MaxCurrent` / `StandbyCurrent` as the 5-bit CS value directly for both supported eval boards.

**TMC5160 velocity (rev/s ↔ VMAX)** — datasheet §6.3, with `motion_units_per_fullstep` matching the firmware's microstep-resolution code:

```
VMAX = rev/s · motion_units_per_fullstep · steps_per_rev · 2²⁴ / f_clk
```

**TMC5160 acceleration (rev/s² ↔ AMAX)** — datasheet §6.3.1:

```
AMAX = rev/s² · motion_units_per_fullstep · steps_per_rev · 2⁴¹ / f_clk²
```

**TMC2660 velocity (rev/s ↔ μsteps/s)** — the chip has no ramp generator; the Landungsbrücke firmware emulates one and accepts μsteps/s at the currently configured microstep resolution:

```
MaxVelocity = rev/s · steps_per_rev · μsteps_per_fullstep
```

This is why the two chips expose the same `set_speed_rps()` / `set_acceleration_rps2()` methods but with genuinely different conversion math inside.

## Feature discovery

Not everything is supported on both chips. Rather than guess, ask:

```python
if motor.has_feature("stealthchop"):
    motor.set_stealthchop(True)

# names: "stealthchop", "interpolation", "coolstep", "stallguard", "ramp_generator"
```

Calling an unsupported feature raises `UnsupportedFeatureError` (a subclass of `NotImplementedError`) — never silently fails.

## Safety

- `MotorConfig.max_current_mA_limit` (default 2000 mA) is a soft cap enforced in software before any write reaches the hardware. Raise or disable at your own risk.
- `set_run_current_mA()` and `set_standstill_current_mA()` reject negative values.
- `set_speed_rps()` rejects negatives (use `Direction.CCW` for the other direction).
- `set_acceleration_rps2()` rejects zero and negatives.
- `set_stallguard_threshold()` enforces the ±64 range.
- Requested currents that round to CS > 31 are clamped to CS=31 with a `UserWarning` (use `conversions.mA_rms_to_cs(..., clamp=False)` to raise instead).

## Tests

### Offline (no hardware)

```bash
pip install pytest
pytest tests/
```

94 unit tests covering:

- pure conversion math (22 tests — roundtrip, datasheet cross-checks, clamping, monotonicity)
- `TMC5160Motor` behaviour against a fake connection (33 tests)
- `TMC5160Motor` advanced features — StealthChop, interpolation, StallGuard
- `TMC2660Motor` behaviour (22 tests)
- `StepperMotor` Protocol conformance and chip-swap equivalence (17 tests)

All 94 tests run offline against a `FakeConnection` that records TMCL calls — no Landungsbrücke required for CI.

### Hardware (with a real Landungsbrücke)

The `tests/hardware/` suite exercises a real motor and verifies that the
values the wrapper programs actually reach the chip. These are **skipped by
default** and only run if you pass the port:

```bash
pytest tests/hardware/ \
    --hw-port=/dev/tty.usbmodemTMCEVAL1 \
    --hw-chip=TMC5160 \
    --hw-rsense=0.075
```

Full option list:

| Option                  | Default     | Purpose                                 |
|-------------------------|-------------|-----------------------------------------|
| `--hw-port`             | *(none)*    | Port; if omitted all hw tests skip      |
| `--hw-chip`             | `TMC5160`   | Chip on the Eselsbrücke                 |
| `--hw-rsense`           | `0.075`     | Sense resistor in Ω                     |
| `--hw-fullsteps`        | `200`       | Motor full steps per revolution         |
| `--hw-current-mA`       | `500`       | Run current used in tests (conservative)|
| `--hw-standstill-mA`    | `100`       | Standstill current                      |
| `--hw-max-mA`           | `1000`      | Safety cap                              |

All options also read from environment variables `TRINAMIC_HW_PORT`,
`TRINAMIC_HW_CHIP`, etc., so you can export them once per shell session.

What the hardware tests verify that offline tests can't:

- The chip's own current register (`IHOLD_IRUN` for 5160, shadow of
  `SGCSCONF` for 2660) matches the CS the wrapper intended to program —
  this closes the loop on the TMCL firmware's interpretation of
  `MaxCurrent`.
- `disable()` actually zeros the current register, and `enable()` restores
  the cached value.
- A `rotate_by(1.0)` produces exactly 1.0 revolution on the chip's
  `ActualPosition` counter (within one microstep).
- `Direction.CCW` gives a negative position readback.
- `set_speed_rps(1.0)` results in an `ActualVelocity` near 1.0 rot/s
  (within 20 % — velocity readback is quantised).
- `set_stealthchop(True)` sets bit 2 of `GCONF` on the TMC5160.

The fixture is function-scoped and **always calls `stop()` then
`disable()` in teardown**, even on test failure, so a crashed test
won't leave the motor energised.

## Escape hatches

When you need something the wrapper doesn't expose, the underlying pytrinamic objects are right there:

```python
motor._motor                 # the pytrinamic MotorControlModule
motor._eval                  # the pytrinamic TMC5160_eval / TMC2660_eval
motor.raw_ic                 # the pytrinamic TMC5160 / TMC2660 IC definition (REG, FIELD)
```

So `motor._eval.write_register_field(motor.raw_ic.FIELD.VHIGHFS, 1)` stays available for ad-hoc register pokes, which is handy when tuning something the wrapper doesn't expose yet.
