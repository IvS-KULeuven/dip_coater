from enum import Enum
import time

class MovementAbsRel(Enum):
    """movement absolute or relative"""
    ABSOLUTE = 0
    RELATIVE = 1

def set_max_speed(self, speed):
    pass

def set_acceleration(self, acceleration):
    pass

def run_to_position_revolutions(self, revolutions, movement_abs_rel = None):
    time.sleep(1)   # Simulate the movement

def run_to_position_revolutions_threaded(self, revolutions, movement_abs_rel = None):
    pass

def wait_for_movement_finished_threaded(self):
    pass

def set_movement_abs_rel(self, movement_abs_rel):
    pass
