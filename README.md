# The Dip Coater App

This small App is developed for IvS to drive the motor for the dip coater. The motor is connected to a Raspberry Pi through the GPIO bus.

This App is developed with [Textual](https://www.textualize.io).

## Installation

Always install in a dedicated virtual environment!

```bash
$ cd </path/to/dip-coater>
$ python3 -m venv venv --prompt=dip-coater
$ source venv/bin/activate
$ pip install --upgrade pip setuptools wheel
$ pip install -e .
```

On a Raspberry Pi, install the project together with the RPi package:

```bash
$ pip install dip-coater[rpi] 
```

When you want to develop and test on a macOS or Linux system, install without the RPi package. The App will mock the imports and functions.

```bash
$ pip install dip-coater
```

## Usage

Start the App from the command line in a terminal. You can start it also from a remote ssh session in a terminal, e.g. if you have the installation on the Raspberry Pi and you have a remote connection to your RPi.

```bash
$ dip-coater
```

This will show the following App in your terminal:

![](https://raw.githubusercontent.com/IvS-KULeuven/dip_coater/develop/images/dip-coater-dark.png)

By default, the `Main` tab is selected. You can switch to the `Advanced` tab on top of the screen to access more advanced settings.

![](https://raw.githubusercontent.com/IvS-KULeuven/dip_coater/develop/images/dip-coater-dark-advanced.png)

To run custom, automated routines, you can use the `Coder` tab. Here you can write your own Python code to control the motor
using the Coder API. The code is executed when you press the `RUN code` button. You can view the available Coder API calls in the 
collapsible section at the top of the screen, or in the help menu. If you do not want to use the default code, you can 
enter the file path to a Python file on the bottom of the coder panel. The new file will be loaded when you press the 
`LOAD code from file` button

![](https://raw.githubusercontent.com/IvS-KULeuven/dip_coater/develop/images/dip-coater-dark-coder.png)

If you prefer light mode, press the `d` key.

![](https://raw.githubusercontent.com/IvS-KULeuven/dip_coater/develop/images/dip-coater-light.png)

Further help is available in the App by pressing the 'h' key:

![](https://raw.githubusercontent.com/IvS-KULeuven/dip_coater/develop/images/dip-coater-help-screen.png)
