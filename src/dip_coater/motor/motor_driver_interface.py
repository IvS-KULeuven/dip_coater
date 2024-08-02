from abc import ABC, abstractmethod

from dip_coater.motor.mechanical_setup import MechanicalSetup

class MotorDriver(ABC):
    def __init__(self, mechanical_setup: MechanicalSetup):
        self.mechanical_setup = mechanical_setup

    # --------------- MOTOR CONTROL ---------------

    @abstractmethod
    def enable_motor(self):
        pass

    @abstractmethod
    def disable_motor(self):
        pass

    @abstractmethod
    def move_up(self, distance_mm: float, speed_mm_s: float, acceleration_mm_s2: float = 0):
        pass

    @abstractmethod
    def move_down(self, distance_mm: float, speed_mm_s: float, acceleration_mm_s2: float = 0):
        pass

    @abstractmethod
    def stop_motor(self):
        pass

    @abstractmethod
    def get_current_position_mm(self):
        pass

    @abstractmethod
    def run_to_position(self, position_mm: float, speed_mm_s: float = None, acceleration_mm_s2: float = None):
        pass

    # --------------- MOTOR CONFIGURATION ---------------

    @abstractmethod
    def set_speed(self, speed_mm_s: float):
        pass

    @abstractmethod
    def set_acceleration(self, acceleration_mm_s2: float):
        pass

    @abstractmethod
    def set_microsteps(self, microsteps: int):
        pass

    @abstractmethod
    def get_microsteps(self) -> int:
        """ Returns the current microsteps setting (e.g. 1, 2, 4, 8, 16, 32, 64, 128, 256) """
        pass

    @abstractmethod
    def set_max_current(self, current_mA: float):
        pass

    @abstractmethod
    def set_standby_current(self, current_mA: float):
        pass

    @abstractmethod
    def cleanup(self):
        pass
