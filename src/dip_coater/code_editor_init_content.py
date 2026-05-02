"""
!!! USE THIS EDITOR WITH CAUTION !!!
Stick to the provided API and do not import any modules or use any functions that are not part of
the API.
"""

# ruff: noqa: F821

# ====== PARAMETERS ======
distance_down = 10  # mm
distance_up = distance_down    # mm

speed_down = 5      # mm/s
speed_up = 2        # mm/s

wait_time = 5       # s

# ====== CODE ======
self.enable_motor()

# == MOVE DOWN ==
self.move_down(distance_mm=distance_down, speed_mm_s=speed_down)

# == WAIT ==
self.sleep(seconds=wait_time)

# == MOVE UP ==
self.move_up(distance_mm=distance_up, speed_mm_s=speed_up)

self.disable_motor()
