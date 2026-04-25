# Troubleshooting

Use this page when something does not work as expected.

## The App Does Not Start

Run:

```bash
dip-coater --help
```

If the command is not found, the package is not installed in your current environment. Activate the Poetry shell or virtual environment and try again.

```bash
poetry shell
dip-coater --help
```

## I Do Not Know Which Port to Use

For TMC2660 and TMC5160 hardware, the serial port must match the connected controller.

Common ports:

- macOS: `/dev/tty.usbmodemTMCEVAL1`
- Raspberry Pi or Linux: `/dev/ttyACM0`, `/dev/ttyACM1`, or `/dev/ttyUSB0`

You can also ask the app to select interactively:

```bash
dip-coater --driver TMC5160 --interface usb_tmcl --port interactive
```

## Connection Error on `/dev/ttyACM0`

If you see:

```text
ConnectionError: Couldn't connect to port /dev/ttyACM0. Connection failed.
```

Then `/dev/ttyACM0` is probably not the correct port. Re-run with the correct `--port`.

## The Motor Does Not Move

Check:

- the motor is enabled in the UI
- the motor power supply is on
- the correct driver is selected
- the correct setup profile is selected
- the movement distance is not zero
- the speed is not zero
- no limit switch is currently triggered
- the app log does not show an error

Try a small movement first:

```bash
dip-coater --driver TMC5160 --use-dummy-driver
```

If dummy mode works but hardware does not, the problem is likely connection, driver, power, or wiring.

## Movement Direction Is Wrong

Stop the motor and restart with:

```bash
dip-coater --setup small --invert-direction
```

Or use the correct setup profile if one already has the right direction configured.

## Position Controls Are Disabled

Absolute position movement requires homing.

Press `Home` first. After homing succeeds, the position controls become available.

## Raspberry Pi Serial Port Setup

For the TMC2209 library, Raspberry Pi serial settings may need to be enabled.

Run:

```bash
sudo raspi-config
```

Then choose:

```text
3 Interface Options -> P3 Serial Port
```

Answer:

- login shell over serial: `No`
- serial port hardware enabled: `Yes`

Finish and reboot.

You may also need to add your user to the `dialout` group:

```bash
sudo usermod -a -G dialout pi
```

Then log out and log back in.

## I Do Not Know the Raspberry Pi IP Address

If the Raspberry Pi is on the same network, scan the network.

Install `nmap`:

```bash
sudo apt install nmap
```

On macOS:

```bash
brew install nmap
```

Find your network range:

```bash
ip addr show
```

On macOS:

```bash
ifconfig
```

Then scan the network, replacing the range with your own:

```bash
sudo nmap -sn 192.168.1.0/24
```

Look for an entry that mentions Raspberry Pi.
