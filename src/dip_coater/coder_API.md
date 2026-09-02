Press `STOP code` to disable the motor and interrupt the script between Python
lines or while it waits for a Coder API command. A long-running native-library
call can only stop after that call returns.

```python
self.enable_motor()         # Arm the motor
self.disable_motor()        # Disarm the motor

# Move the motor down by distance_mm at speed_mm_s speed and (optional) acceleration_mm_s acceleration
self.move_down(distance_mm, speed_mm_s, acceleration_mm_s2=None)
### Examples:
self.move_down(distance_mm=10, speed_mm_s=5)
self.move_down(distance_mm=10, speed_mm_s=5, acceleration_mm_s2=10)

# Move the motor up by distance_mm at <speed_mm_s> speed and (optional) <acceleration_mm_s> acceleration
self.move_up(distance_mm, speed_mm_s, acceleration_mm_s2=None)
### Examples:
self.move_up(distance_mm=10, speed_mm_s=5)
self.move_up(distance_mm=10, speed_mm_s=5, acceleration_mm_s2=10)

# Home the motor (needed to move to motor to absolute positions)
self.home_motor(home_up=True)    # Home the motor. If home_up is True, the motor will move up until the top limit switch is triggered. If home_up is False, the motor will move down until the bottom limit switch is triggered.

# Move the motor to an absolute position (in mm)
self.move_to_position(position_mm, speed_mm_s=None, acceleration_mm_s2=None)
### Examples:
self.move_to_position(position_mm=10)
self.move_to_position(position_mm=10, speed_mm_s=5)

self.sleep(seconds=5)       # Sleep for 5 seconds
```
