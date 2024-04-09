""" Coder API:

self.enable_motor()         # Arm the motor
self.disable_motor()        # Disarm the motor

self.move_down(10, 5)       # Move the coater down by 10 mm at 5 mm/s
self.move_down(10, 5, 10)   # Move the coater down by 10 mm at 5 mm/s and 10 mm/s^2 acceleration

self.move_up(10, 5)         # Move the coater up by 10 mm at 5 mm/s
self.move_up(10, 5, 10)     # Move the coater up by 10 mm at 5 mm/s and 10 mm/s^2 acceleration

self.sleep(5)               # Sleep for 5 seconds

!!! USE THIS EDITOR WITH CAUTION !!!
Stick to the provided API and do not import any modules or use any functions that are not part of the API.
"""

self.enable_motor()

# ====== PARAMETERS ======
distance_down = 10  # mm
distance_up = 10    # mm

speed_down = 5      # mm/s
speed_up = 2        # mm/s

wait_time = 5       # s

# ====== MOVE UP ======
self.move_down(distance_down, speed_down)

# ====== WAIT ======
self.sleep(wait_time)

# ====== MOVE DOWN ======
self.move_up(distance_up, speed_up)

self.disable_motor()
