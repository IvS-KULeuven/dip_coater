# The DIP Coater

## Keyboard actions

- `d` toggles dark/light mode
- `q` quits the application
- `h` show this help screen (`escape` to exit)
- `tab` will navigate through different input possibilities
- `return` will accept the currently selected input

## Description

Step mode is in mm/s. You will have to adjust the drivers DIP switches according to the selected step mode. The values for the DIP switches are:

| Step mode | Switches |||
| --- |----------| --- | --- |
|Full | MS3: 0   | MS2: 0 | MS1: 0
|Half | MS3: 0   | MS2: 0 | MS1: 1
|1/4  | MS3: 0   | MS2: 1 | MS1: 0
|1/8  | MS3: 0   | MS2: 1 | MS1: 1
|1/16 | MS3: 1   | MS2: 1 | MS1: 1


The movement speed and the vertical distance is the same for up or down movements. You can change the speed and distance with the UP and DOWN buttons. The application has defined minimum and maximum values for the speed and distance. You will not be able to go passed these limits.

After startup the motor will have been initialised, but disabled. Press the `enable motor` button before moving. You will not be able to move when the motor is disabled.

The right part of the screen shows the current values and the state of the motor.


Author: Rik Huygen (https://github.com/rhuygen)

Press ESCAPE to Exit.
