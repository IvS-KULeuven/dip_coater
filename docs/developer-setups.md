# Developer Setup Profiles

This page is for maintainers adding or changing machine setup profiles.

Setup profiles live in:

```text
src/dip_coater/setup_profiles/
```

The main files are:

- `machine_profile.py` defines the data model.
- `registry.py` defines the bundled profiles and default setup per driver.

## Profile Model

A setup profile describes machine geometry, direction, travel limits, homing direction, and limit switches.

Core fields:

```python
MachineProfile(
    key=AvailableMachineSetups.CUSTOM,
    label="Custom",
    mechanical_setup=MechanicalSetup(...),
    invert_motor_direction=False,
    home_direction=HomeDirection.UP,
    limit_switches=None,
    min_position_mm=0.0,
    max_position_mm=100.0,
    homing_max_distance_mm=100.0,
)
```

`mechanical_setup` controls unit conversion between motor revolutions and millimeters:

```python
MechanicalSetup(
    mm_per_revolution=4.0,
    gearbox_ratio=1.0,
    steps_per_revolution=200,
)
```

## Limit Switches

Limit switches are configured with a `LimitSwitchSetup`. Each setup has one `up` switch and one `down` switch.

Each switch has:

- `source`: where the state is read from.
- `polarity`: which raw state means triggered.
- `pin`: GPIO pin, only for GPIO switches.

Supported sources:

```python
LimitSwitchSource.GPIO
LimitSwitchSource.DRIVER_REFERENCE
```

Supported polarities:

```python
LimitSwitchPolarity.ACTIVE_HIGH
LimitSwitchPolarity.ACTIVE_LOW
```

`ACTIVE_HIGH` means raw `True` is triggered.

`ACTIVE_LOW` means raw `False` is triggered.

## GPIO Switches

Use GPIO switches for Raspberry Pi wiring, such as the small TMC2209 setup:

```python
LimitSwitchSetup.gpio(
    up_pin=19,
    down_pin=26,
    up_nc=True,
    down_nc=True,
)
```

For GPIO switches, `up_nc=True` and `down_nc=True` preserve the historical normally-closed behavior:

- GPIO high means triggered.
- GPIO low means open.

The app creates a GPIO backend only when the selected setup uses GPIO switches.

## TMC5160 Reference Switches

Use driver reference switches for Landungsbruecke/TMC5160 L/R reference inputs:

```python
LimitSwitchSetup.tmc5160_reference(
    up_polarity=LimitSwitchPolarity.ACTIVE_LOW,
    down_polarity=LimitSwitchPolarity.ACTIVE_LOW,
)
```

For the current Landungsbruecke wiring:

- L/R tied to GND is safe.
- L/R open or floating is triggered.

That is why the large setup uses `ACTIVE_LOW` for both directions.

The app reads these states through the motor driver methods:

```python
get_left_endstop()
get_right_endstop()
```

The TMC5160 startup config also enables automatic reference stops by default:

```python
DEFAULT_REFERENCE_LEFT_STOP_ENABLED = True
DEFAULT_REFERENCE_RIGHT_STOP_ENABLED = True
```

## Bundled Profiles

The bundled profiles are defined in `registry.py`.

`small`:

- Uses `SetupSmallCoater`.
- Uses GPIO limit switches on pins 19 and 26.
- Defaults to `HomeDirection.UP`.

`large`:

- Uses `SetupLargeCoater`.
- Uses Landungsbruecke/TMC5160 driver reference switches.
- Defaults to `HomeDirection.UP`.

Default setup per driver is also configured in `registry.py`:

```python
DEFAULT_SETUP_BY_DRIVER = {
    AvailableMotorDrivers.TMC2209: AvailableMachineSetups.SMALL_COATER,
    AvailableMotorDrivers.TMC2660: AvailableMachineSetups.LARGE_COATER,
    AvailableMotorDrivers.TMC5160: AvailableMachineSetups.LARGE_COATER,
}
```

## Add a New Setup

1. Add a new enum value to `AvailableMachineSetups`.
2. Add a `MachineProfile` entry in `_PROFILES`.
3. Choose the correct `MechanicalSetup`.
4. Configure motor direction with `invert_motor_direction`.
5. Configure homing with `home_direction` and `homing_max_distance_mm`.
6. Configure `limit_switches` with `LimitSwitchSetup.gpio(...)`, `LimitSwitchSetup.tmc5160_reference(...)`, or `None`.
7. Update `DEFAULT_SETUP_BY_DRIVER` only if the new profile should become a default.
8. Add or update tests in `src/test/test_motion_architecture.py`.

Example:

```python
AvailableMachineSetups.MY_COATER = "my-coater"

_PROFILES[AvailableMachineSetups.MY_COATER] = MachineProfile(
    key=AvailableMachineSetups.MY_COATER,
    label="My Coater",
    mechanical_setup=MechanicalSetup(
        mm_per_revolution=4.0,
        gearbox_ratio=1.0,
        steps_per_revolution=200,
    ),
    invert_motor_direction=False,
    home_direction=HomeDirection.UP,
    limit_switches=LimitSwitchSetup.tmc5160_reference(
        up_polarity=LimitSwitchPolarity.ACTIVE_LOW,
        down_polarity=LimitSwitchPolarity.ACTIVE_LOW,
    ),
    min_position_mm=0.0,
    max_position_mm=100.0,
    homing_max_distance_mm=100.0,
)
```

## Safety Checks

After changing a setup profile:

1. Run non-hardware tests.
2. Start the app in dummy mode and confirm the selected setup label.
3. With hardware powered safely, check that limit switch status changes correctly before moving.
4. Move only a short distance at low speed.
5. Confirm that the motor stops when the active direction's limit switch is triggered.

```bash
uv run pytest src/test src/trinamic_wrapper/tests -q
```
