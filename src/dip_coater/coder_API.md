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

self.sleep(5)               # Sleep for 5 seconds
```