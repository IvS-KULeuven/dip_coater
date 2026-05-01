# Run the App

Start the app from a terminal:

```bash
dip-coater
```

By default, the app uses the `TMC2209` driver.

## Choose a Motor Driver

The app supports three drivers:

- `TMC2209`
- `TMC2660`
- `TMC5160`

Examples:

```bash
dip-coater --driver TMC2209
dip-coater --driver TMC2660
dip-coater --driver TMC5160
```

For a TMC5160 evaluation board over USB-TMCL:

```bash
dip-coater --driver TMC5160 --interface usb_tmcl --port /dev/tty.usbmodemTMCEVAL1
```

On Linux or Raspberry Pi, the port may look like this instead:

```bash
dip-coater --driver TMC5160 --interface usb_tmcl --port /dev/ttyACM0
```

## Choose a Machine Setup

Machine setup is selected separately from the motor driver. The bundled setup profiles are:

- `small`: Raspberry Pi GPIO limit switches, usually used with `TMC2209`
- `large`: Landungsbruecke/TMC5160 reference switches, usually used with `TMC2660` or `TMC5160`

Examples:

```bash
dip-coater --setup small
dip-coater --setup large
dip-coater --driver TMC2209 --setup large
```

## Run Without Hardware

Use dummy mode when you want to try the interface without moving a real motor:

```bash
dip-coater --driver TMC2209 --use-dummy-driver
dip-coater --driver TMC2660 --use-dummy-driver
dip-coater --driver TMC5160 --use-dummy-driver
```

Dummy mode is useful for training, demos, and checking scripts before using the real setup.

## Use an Environment File

The app does not automatically read `.env` files. To use one, copy `.env.example` to `.env`, edit it, and load it before running the app.

```bash
set -a
source .env
set +a
dip-coater
```

Example values:

```bash
DIP_COATER_DRIVER=TMC5160
DIP_COATER_INTERFACE=usb_tmcl
DIP_COATER_PORT=/dev/tty.usbmodemTMCEVAL1
DIP_COATER_SESSION_LOG_FILE=logs/dip-coater-session.jsonl
```

## Session Diagnostics

The app writes persistent session diagnostics as JSON lines. By default the file is `logs/dip-coater-session.jsonl` relative to the directory where you start the app.

Use `--session-log-file` or `DIP_COATER_SESSION_LOG_FILE` to choose a different path:

```bash
dip-coater --session-log-file ~/dip-coater-session.jsonl
```

The session log records startup settings, requested motion, homing attempts, motion timeouts, limit-switch stops, and shutdown cleanup.

## Useful Command Options

| Option | Meaning | Example |
|---|---|---|
| `--driver` | Select motor driver | `--driver TMC5160` |
| `--setup` | Select machine setup | `--setup small` |
| `--interface` | Select PyTrinamic interface | `--interface usb_tmcl` |
| `--port` | Select serial port | `--port /dev/ttyACM0` |
| `--log-level` | Select logging detail | `--log-level DEBUG` |
| `--use-dummy-driver` | Run without real hardware | `--use-dummy-driver` |
| `--invert-direction` | Reverse motor direction for this run | `--invert-direction` |
| `--home-direction` | Override homing direction | `--home-direction down` |
| `--session-log-file` | Write persistent JSON-lines diagnostics | `--session-log-file logs/session.jsonl` |

## Keyboard Shortcuts

| Key | Action |
|---|---|
| `t` | Toggle dark/light mode |
| `q` | Quit the application |
| `h` | Show help |
| `a` | Enable the motor |
| `d` | Stop and disable the motor |
| `w` | Move up |
| `s` | Move down |
| `tab` | Move to the next input or button |
| `enter` | Accept the selected input |
