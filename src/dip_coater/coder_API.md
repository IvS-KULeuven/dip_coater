```python
self.enable_motor()         # Arm the motor
self.disable_motor()        # Disarm the motor

# Move the motor down by distance_mm at speed_mm_s speed and (optional) acceleration_mm_s acceleration
self.move_down(distance_mm, speed_mm_s, acceleration_mm_s2=None)
### Examples:
self.move_down(10, 5)       # Move the coater down by 10 mm at 5 mm/s
self.move_down(10, 5, 10)   # Move the coater down by 10 mm at 5 mm/s and 10 mm/s^2 acceleration

# Move the motor up by distance_mm at <speed_mm_s> speed and (optional) <acceleration_mm_s> acceleration
self.move_down(distance_mm, speed_mm_s, acceleration_mm_s2=None)
### Examples:
self.move_up(10, 5)         # Move the coater up by 10 mm at 5 mm/s
self.move_up(10, 5, 10)     # Move the coater up by 10 mm at 5 mm/s and 10 mm/s^2 acceleration

# Home the motor (needed to move to motor to absolute positions)
self.home_motor(home_up=True)    # Home the motor. If home_up is True, the motor will move up until the top limit switch is triggered. If home_up is False, the motor will move down until the bottom limit switch is triggered.

# Move the motor to an absolute position (in mm)
self.move_to_position(self, position_mm, speed_mm_s=None, acceleration_mm_s2=None, home_up=True)
### Examples:
self.move_to_position(10)           # Move the coater to 10 mm, using the last set speed and acceleration
self.move_to_position(10, 5)        # Move the coater to 10 mm at 5 mm/s

self.sleep(5)               # Sleep for 5 seconds
```