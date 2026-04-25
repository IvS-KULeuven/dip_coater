# Use the Interface

The app has four main tabs:

- Main
- Advanced
- Logs
- Coder

## Main Tab

Use the Main tab for normal operation.

![Main tab](https://raw.githubusercontent.com/IvS-KULeuven/dip_coater/develop/images/dip-coater-dark.png)

### Enable the Motor

After startup, the motor is initialized but disabled.

Press `Enable motor` before moving.

!!! warning
    Enabling the motor can energize the hardware. Make sure the moving assembly and coating vessel are clear before pressing it.

### Move Down or Up

Set the movement distance and speed, then press:

- `Move down`
- `Move up`

You can change speed and distance with the `+` and `-` buttons or by typing a number in the input field and pressing `enter`.

The app clamps values to configured minimum and maximum limits.

### Home the Motor

If your setup supports homing, press `Home`.

Homing moves the machine until the selected limit switch is reached. After homing, the app knows the absolute position of the moving assembly.

You must home before using absolute position moves.

### Move to an Absolute Position

After homing, use the position controls to move to a specific position in millimeters.

Example:

1. Press `Home`.
2. Enter `10` in the position field.
3. Press `Move to position`.

The moving assembly moves to the 10 mm position.

## Status Panel

The right side of the Main tab shows:

- driver type
- setup profile
- speed
- distance
- homing status
- limit switch status
- motor state
- current position

Use this panel before every run. If the motor state is `DISABLED`, movement buttons will not move the motor.

## Advanced Tab

Use the Advanced tab when you need to change motor behavior.

![Advanced tab](https://raw.githubusercontent.com/IvS-KULeuven/dip_coater/develop/images/dip-coater-dark-advanced.png)

Common settings include:

- step mode
- acceleration
- motor current
- standstill current
- motor direction
- driver-specific features such as interpolation, StallGuard, CoolStep, or threshold speed

!!! caution
    Do not change current, step mode, or driver-specific settings unless you know the setup values you want. Wrong values can cause missed steps, overheating, or poor motion.

Press `Reset to defaults` if you want to return to the configured defaults.

## Logs Tab

Use the Logs tab for debugging and setup checks.

![Logs tab](https://raw.githubusercontent.com/IvS-KULeuven/dip_coater/develop/images/dip-coater-dark-logs.png)

Increase the logging level when you need more detail.

## Coder Tab

Use the Coder tab for repeatable coating routines.

![Coder tab](https://raw.githubusercontent.com/IvS-KULeuven/dip_coater/develop/images/dip-coater-dark-coder.png)

You can write Python commands using the Coder API, then press `RUN code`.

See [Coder API](coder-api.md) for examples.
