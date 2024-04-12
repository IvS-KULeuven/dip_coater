# The DIP Coater

## Keyboard actions

- `d` toggles dark/light mode
- `q` quits the application
- `h` show this help screen (`escape` to exit)
- `tab` will navigate through different input possibilities
- `return` will accept the currently selected input

## Description

### Main tab

The movement speed and the vertical distance is the same for up or down movements. You can change the speed and distance 
with the `+` and `-` buttons, or by entering a new value in the text input fields (the widget that displays the 
speed/distance value) and then pressing the Enter key on your keyboard. The application has defined minimum and maximum 
values for the speed and distance. You will not be able to go passed these limits.

For high motor speeds (> 10 mm/s) and/or high step mode (> 16), the motor may overshoot (a larger travel distance than 
the set distance), or not respond as fast as you would expect for the given speed input. This is due to the limitation 
of how fast Python and the Raspberry Pi can handle the motor control timing.

After startup the motor will have been initialised, but disabled. Press the `enable motor` button before moving. You will 
not be able to move when the motor is disabled.

The right part of the screen shows the current values and the state of the motor.

### Advanced tab
To access more advanced control settings, you can switch to the `Advanced` tab on top of the screen (by default, 
the `Main` tab is selected).

### Coder tab
To run custom, automated routines you can use the `Coder` tab. Here you can write your own Python code to control the 
motor using the Coder API. The code is executed when you press the `RUN code` button. You can view the available 
Coder API calls in the collapsible section at the top of the screen, or in the help menu. If you do not want to use the 
default code, you can enter the file path to a Python file on the bottom of the coder panel. The new file will be loaded 
when you press the `LOAD code from file` button.

---

If the UI is too small, you can zoom out by selecting `Edit` in the terminal toolbar and then select `Zoom out`.

Authors: Rik Huygen (https://github.com/rhuygen), Sibo Van Gool (https://github.com/SiboVG)

Press ESCAPE to Exit.

## Coder API

You can create custom control routines using the coder in the `Coder` tab. To do so, you must write Python code with the 
following functions (the so-called 'Coder API'):
- `self.enable_motor()`: arm the motor
- `self.disable_motor()`: disarm the motor
- `self.move_down(distance_mm, speed_mm_s, acceleration_mm_s=None)`: move the motor down by supplying the following parameters:
  - `distance_mm`: the distance in mm to move down
  - `speed_mm_s`: the speed in mm/s to move down
  - `acceleration_mm_s`: the acceleration in mm/s^2 to move down (optional, leave empty for default acceleration)
- `self.move_up(distance_mm, speed_mm_s, acceleration_mm_s=None)`: move the motor up by supplying the following parameters:
  - `distance_mm`: the distance in mm to move up
  - `speed_mm_s`: the speed in mm/s to move up
  - `acceleration_mm_s`: the acceleration in mm/s^2 to move up (optional, leave empty for default acceleration)
- `self.sleep(seconds)`: wait for a number of seconds

For example, to move the motor down by 10 mm at a speed of 5 mm/s, then wait 5 seconds, and then move up by 10 mm at 2 mm/s,
you can write the following code in the `Coder` tab:

```python
# Arm the motor
self.enable_motor()

# Move down
self.move_down(10, 5)

# Wait for 5 seconds
self.sleep(5)

# Move up
self.move_up(10, 2)

# Disarm the motor
self.disable_motor()
```
