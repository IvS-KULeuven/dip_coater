from abc import ABC, abstractmethod
from enum import Enum

from dip_coater.mechanical.mechanical_setup import MechanicalSetup


class AvailableMotorDrivers(str, Enum):
    TMC2209 = "TMC2209",
    TMC2660 = "TMC2660",



class MotorDriver(ABC):
    def __init__(self, mechanical_setup: MechanicalSetup):
        self.mechanical_setup = mechanical_setup
        self.microsteps = None

    # --------------- MOTOR CONTROL ---------------

    @abstractmethod
    def enable_motor(self):
        raise NotImplementedError()

    @abstractmethod
    def disable_motor(self):
        raise NotImplementedError()

    @abstractmethod
    def invert_direction(self, invert_direction: bool = False):
        raise NotImplementedError()

    @abstractmethod
    def rotate(self, revs: float, rps: float, rpss: float = None):
        """ Rotate clock-wise (viewed from the top of the motor axle)

        :param revs: number of revolutions to turn (> 0 = clock-wise, < 0 = counter-clock-wise)
        :param rps: rotation speed in rotations per second
        :param rpss: rotation acceleration in rotations per second^2 (or None to use the default
                    value)
        """
        raise NotImplementedError()

    @abstractmethod
    def move_up(self, distance_mm: float, speed_mm_s: float, acceleration_mm_s2: float = None, *args, **kwargs):
        raise NotImplementedError()

    @abstractmethod
    def move_down(self, distance_mm: float, speed_mm_s: float, acceleration_mm_s2: float = None, *args, **kwargs):
        raise NotImplementedError()

    @abstractmethod
    def stop_motor(self):
        raise NotImplementedError()

    @abstractmethod
    def wait_for_motor_done(self):
        raise NotImplementedError()
    
    @abstractmethod
    async def wait_for_motor_done_async(self):
        raise NotImplementedError()

    @abstractmethod
    def get_current_position_mm(self):
        raise NotImplementedError()

    @abstractmethod
    def run_to_position(self, position_mm: float, speed_mm_s: float = None,
                        acceleration_mm_s2: float = None):
        raise NotImplementedError()

    @abstractmethod
    def is_homing_found(self):
        raise NotImplementedError()

    # --------------- MOTOR CONFIGURATION ---------------

    @abstractmethod
    def set_speed_rps(self, rps: float):
        raise NotImplementedError()

    def set_speed(self, speed_mm_s: float):
        """ Set the motor speed.

        :param speed_mm_s: The speed in mm/s
        """
        if speed_mm_s is None:
            return
        rps = self.mechanical_setup.mm_s_to_rps(speed_mm_s)
        self.set_speed_rps(rps)

    @abstractmethod
    def set_acceleration_rpss(self, rpss: float):
        raise NotImplementedError()

    def set_acceleration(self, acceleration_mm_s2: float):
        """ Set the motor acceleration.

        :param acceleration_mm_s2: The acceleration/deceleration to use for the movement in mm/s^2
        """
        if acceleration_mm_s2 is None:
            return
        rpss = self.mechanical_setup.mm_s2_to_rpss(acceleration_mm_s2)
        self.set_acceleration_rpss(rpss)

    @abstractmethod
    def set_microsteps(self, microsteps: int):
        raise NotImplementedError()

    @abstractmethod
    def get_microsteps(self) -> int:
        """ Returns the current microsteps setting (e.g. 1, 2, 4, 8, 16, 32, 64, 128, 256) """
        raise NotImplementedError()

    @abstractmethod
    def set_current(self, current_mA: float):
        raise NotImplementedError()

    @abstractmethod
    def set_current_standstill(self, current_mA: float):
        raise NotImplementedError()

    @abstractmethod
    def add_log_handler(self, handler):
        raise NotImplementedError()

    @abstractmethod
    def remove_log_handler(self, handler):
        raise NotImplementedError()

    @abstractmethod
    def cleanup(self):
        raise NotImplementedError()
