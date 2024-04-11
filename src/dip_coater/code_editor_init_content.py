"""
!!! USE THIS EDITOR WITH CAUTION !!!
Stick to the provided API and do not import any modules or use any functions that are not part of the API.
"""

# ====== PARAMETERS ======
distance_down = 10  # mm
distance_up = distance_down    # mm

speed_down = 5      # mm/s
speed_up = 2        # mm/s

wait_time = 5       # s

# ====== CODE ======
self.enable_motor()

# == MOVE UP ==
self.move_down(distance_down, speed_down)

# == WAIT ==
self.sleep(wait_time)

# == MOVE DOWN ==
self.move_up(distance_up, speed_up)

self.disable_motor()
