# Hardware Setup

This page describes the physical setups at a high level. There are two main machine families:

- the small dip coater, usually controlled with a Raspberry Pi and `TMC2209`
- the big dip coater, usually controlled with `TMC2660` or `TMC5160` hardware

The exact wiring can differ between machines, so check the actual machine before powering anything.

!!! warning
    Disconnect motor power before changing wiring.

## Common Parts

Most dip coater setups have:

- a vertical motion axis
- a stepper motor
- a motor driver
- a Raspberry Pi, Landungsbruecke, or other control interface
- optional top and bottom limit switches
- a power supply for the motor
- a moving sample or substrate fixture
- a coating vessel or solution container

![Linear guide components](https://raw.githubusercontent.com/IvS-KULeuven/dip_coater/develop/images/small_lift/LinearGuideComponents.png)

## Small Dip Coater

The small dip coater is the Raspberry Pi based setup documented by the original hardware photos. It uses a compact linear guide and a BIGTREETECH TMC2209 1.3 stepper motor driver.

Use the `small` setup profile unless your machine-specific instructions say otherwise:

```bash
dip-coater --driver TMC2209 --setup small
```

The small setup is the one shown in the images below.

## Limit Switches

Limit switches give the machine a known reference point and can stop motion at the travel limits.

The small setup commonly has:

- one top limit switch
- one bottom limit switch

![Bottom limit switch](https://raw.githubusercontent.com/IvS-KULeuven/dip_coater/develop/images/small_lift/BottomLimitSwitch.jpg)

In the documented small TMC2209 setup, the blue wire is connected to `COM` and the yellow wire to `NC`.

### TMC2209 Raspberry Pi Wiring

The small dip coater uses a BIGTREETECH TMC2209 1.3 stepper motor driver connected to a Raspberry Pi.

| TMC2209 pin | Connect to | Purpose |
|---|---|---|
| `TX` with 1 kOhm | Raspberry Pi UART TX | Send data to TMC2209 |
| `RX` | Raspberry Pi UART RX | Receive data from TMC2209 |
| `VDD` | Raspberry Pi 3.3 V | Logic voltage |
| `GND` | Raspberry Pi GND | Signal ground |
| `VM` | 12 V or 24 V power supply | Motor power |
| `GND` | Power supply GND | Motor power ground |
| `EN` | GPIO11 | Enable motor output |
| `STEP` | GPIO9 | Step pulse |
| `DIR` | GPIO10 | Motor direction |
| `DIAG` | GPIO5 | StallGuard or diagnostic signal |

![Perf board components](https://raw.githubusercontent.com/IvS-KULeuven/dip_coater/develop/images/small_lift/PerfBoardComponents.png)

## Big Dip Coater

The big dip coater uses the `large` setup profile and is intended for the larger machine geometry. It is typically controlled with `TMC2660` or `TMC5160` hardware through PyTrinamic-backed communication.

![Big lift overview](https://raw.githubusercontent.com/IvS-KULeuven/dip_coater/develop/images/big_lift/big-lift.jpeg)

![Stepper motor on the big lift](https://raw.githubusercontent.com/IvS-KULeuven/dip_coater/develop/images/big_lift/tmc5160-motor.jpeg)

Typical big dip coater setups use a Landungsbruecke evaluation board over USB-TMCL.

Common command shape:

```bash
dip-coater --driver TMC5160 --setup large --interface usb_tmcl --port /dev/ttyACM0
```

On macOS, the port may look like:

```bash
/dev/tty.usbmodemTMCEVAL1
```

Examples:

```bash
dip-coater --driver TMC2660 --setup large --interface usb_tmcl --port /dev/ttyACM0
dip-coater --driver TMC5160 --setup large --interface usb_tmcl --port /dev/tty.usbmodemTMCEVAL1
```

The big dip coater may not use the same wiring, limit switches, motor current, travel range, or direction as the small dip coater. Use the machine-specific setup profile and hardware notes for the exact machine.

### TMC5160 Reference Limit Switches

The big dip coater uses two **normally-closed (NC)** mechanical limit switches at the extreme ends of travel. They are wired directly to the reference-switch inputs on the TMC5160 EVAL board.

![Limit switches mounted on the big lift](https://raw.githubusercontent.com/IvS-KULeuven/dip_coater/develop/images/big_lift/big-lift-limit-switches.jpeg)

![TMC5160 EVAL limit-switch wiring](https://raw.githubusercontent.com/IvS-KULeuven/dip_coater/develop/images/big_lift/tmc5160-limit-switch.jpeg)

Wire each switch with `COM` to `GND` and `NC` to the matching reference-switch pin:

| Switch | `COM` | `NC` |
|---|---|---|
| Top (up) limit switch | `GND` on the TMC5160 EVAL | `L` (left reference input) |
| Bottom (down) limit switch | `GND` on the TMC5160 EVAL | `R` (right reference input) |

The home direction for the big coater is `down`, so homing drives toward the bottom switch (the `R` input) and zeros the position there. Positions then increase as the platform moves upward.

With NC switches and this wiring:

- switch closed (untriggered), `L`/`R` tied to `GND` through the switch: open in the UI, motion allowed
- switch released or wire broken, `L`/`R` floats high: triggered in the UI, the TMC5160 hardstops

Using NC switches is intentional: a broken wire or loose connector reads as "triggered" and stops the machine, instead of silently disarming the safety stop.

Put the switches at the physical extremes of the motion axis so triggering one protects the machine from moving farther in that direction.

## Before Powering On

Check:

- motor wires are firmly connected
- limit switches are connected if required
- the moving assembly can travel freely
- the moving fixture is not blocked
- the coating vessel is positioned so it cannot be hit unexpectedly
- the correct driver is selected in the command
- the correct setup profile is selected in the command
- the motor power supply voltage matches the driver setup

## Before Moving

1. Start with low speed and short distance.
2. Enable the motor.
3. Move a small amount down and up.
4. Confirm the physical direction matches the UI.
5. If direction is reversed, stop and use the correct setup or `--invert-direction`.
