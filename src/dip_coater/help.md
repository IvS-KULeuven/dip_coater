# The DIP Coater

## Keyboard actions

- `d` toggles dark/light mode
- `q` quits the application
- `h` show this help screen (`escape` to exit)
- `tab` will navigate through different input possibilities
- `return` will accept the currently selected input

## Description

The movement speed and the vertical distance is the same for up or down movements. You can change the speed and distance with the `+` and `-` buttons, or by entering a new value in the text input fields (the widget that displays the speed/distance value) and then pressing the Enter key on your keyboard. The application has defined minimum and maximum values for the speed and distance. You will not be able to go passed these limits.

For high motor speeds (> 10 mm/s), the motor may overshoot (a larger travel distance than the set distance). This is due to the limitation of how fast Python can handle the motor control timing.

After startup the motor will have been initialised, but disabled. Press the `enable motor` button before moving. You will not be able to move when the motor is disabled.

The right part of the screen shows the current values and the state of the motor.

To access more advanced control settings, you can switch to the `Advanced` tab on top of the screen (by default, the `Main` tab is selected).

Authors: Rik Huygen (https://github.com/rhuygen), Sibo Van Gool (https://github.com/SiboVG)

Press ESCAPE to Exit.
