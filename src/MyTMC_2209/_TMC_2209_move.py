from enum import Enum
import time

class MovementAbsRel(Enum):
    """movement absolute or relative"""
    ABSOLUTE = 0
    RELATIVE = 1

class StopMode(Enum):
    """stopmode"""
    NO = 0
    SOFTSTOP = 1
    HARDSTOP = 2


def set_max_speed(self, speed):
    pass

def set_acceleration(self, acceleration):
    pass

def run_to_position_revolutions(self, revolutions, movement_abs_rel = None):
    time.sleep(1)   # Simulate the movement

def run_to_position_revolutions_threaded(self, revolutions, movement_abs_rel = None):
    pass

def wait_for_movement_finished_threaded(self):
    return StopMode.NO

def set_movement_abs_rel(self, movement_abs_rel):
    pass

def get_current_position(self):
    """returns the current motor position in µsteps

    Returns:
        bool: current motor position
    """
    return 0

def set_current_position(self, new_pos):
    """overwrites the current motor position in µsteps

    Args:
        new_pos (bool): new position of the motor in µsteps
    """
    pass
