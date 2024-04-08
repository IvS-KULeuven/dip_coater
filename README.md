# The Dip Coater App

This small App is developed for IvS to drive the motor for the dip coater. The motor is connected to a Raspberry Pi through the GPIO bus.

This App is develop with [Textual](https://www.textualize.io).

## Installation

Always install in a dedicated virtual environment!

On a Raspberry Pi, install the project together with the RPi package:

```
$ pip install dip-coater[rpi] 
```

When you want to develop and test on a macOS or Linux system, install without the RPi package. The App will mock the imports and functions.

```
$ pip install dip-coater
```

## Usage

Start the App from the command line in a terminal. You can start it also from a remote ssh session in a terminal, e.g. if you have the installation on the Raspberry Pi and you have a remote connection to your RPi.

```
$ dip-coater
```

This will show the following App in your terminal:

![](https://raw.githubusercontent.com/IvS-KULeuven/dip_coater/develop/images/dip-coater-dark.png)

If you prefer light mode, press the `d` key.

![](https://raw.githubusercontent.com/IvS-KULeuven/dip_coater/develop/images/dip-coater-light.png)

Further help is available in the App by pressing the 'h' key:

![](https://raw.githubusercontent.com/IvS-KULeuven/dip_coater/develop/images/dip-coater-help-screen.png)
