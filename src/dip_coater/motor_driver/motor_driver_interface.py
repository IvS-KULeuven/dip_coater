from abc import ABC, abstractmethod
from enum import Enum

from dip_coater.mechanical.mechanical_setup import MechanicalSetup


class AvailableMotorDrivers(str, Enum):
    """Supported motor-driver identifiers."""

    TMC2209 = "TMC2209"
    TMC2660 = "TMC2660"
    TMC5160 = "TMC5160"


class MotorDriver(ABC):
    """Abstract motor-driver API used by the motion controller.

    Concrete drivers convert this common millimeter-based interface to the
    hardware-specific commands required by each driver board.
    """

    def __init__(self, mechanical_setup: MechanicalSetup):
        """Store the mechanical conversion model used by the driver.

        :param mechanical_setup: Mechanical setup used for unit conversions.
        """
        self.mechanical_setup = mechanical_setup
        self.microsteps = None

    # --------------- MOTOR CONTROL ---------------

    @abstractmethod
    def enable_motor(self):
        """Enable motor power or driver output."""
        raise NotImplementedError()

    @abstractmethod
    def disable_motor(self):
        """Disable motor power or driver output."""
        raise NotImplementedError()

    @abstractmethod
    def invert_direction(self, invert_direction: bool = False):
        """Configure whether positive motion should be inverted.

        :param invert_direction: ``True`` to invert the driver's physical direction.
        """
        raise NotImplementedError()

    @abstractmethod
    def rotate(self, revs: float, rps: float, rpss: float = None):
        """Rotate clock-wise (viewed from the top of the motor axle)

        :param revs: number of revolutions to turn (> 0 = clock-wise, < 0 = counter-clock-wise)
        :param rps: rotation speed in rotations per second
        :param rpss: rotation acceleration in rotations per second^2 (or None to use the default
                    value)
        """
        raise NotImplementedError()

    @abstractmethod
    def move_up(
        self,
        distance_mm: float,
        speed_mm_s: float,
        acceleration_mm_s2: float = None,
        *args,
        **kwargs,
    ):
        """Move the lift upward by a relative distance.

        :param distance_mm: Relative travel distance in millimeters.
        :param speed_mm_s: Travel speed in millimeters per second.
        :param acceleration_mm_s2: Optional acceleration in millimeters per second squared.
        """
        raise NotImplementedError()

    @abstractmethod
    def move_down(
        self,
        distance_mm: float,
        speed_mm_s: float,
        acceleration_mm_s2: float = None,
        *args,
        **kwargs,
    ):
        """Move the lift downward by a relative distance.

        :param distance_mm: Relative travel distance in millimeters.
        :param speed_mm_s: Travel speed in millimeters per second.
        :param acceleration_mm_s2: Optional acceleration in millimeters per second squared.
        """
        raise NotImplementedError()

    @abstractmethod
    def stop_motor(self):
        """Stop the active motion as soon as the driver supports."""
        raise NotImplementedError()

    @abstractmethod
    def wait_for_motor_done(self):
        """Block until the current motion is finished.

        :return: Driver-specific completion result, if any.
        """
        raise NotImplementedError()

    @abstractmethod
    async def wait_for_motor_done_async(self):
        """Wait asynchronously until the current motion is finished.

        :return: Driver-specific completion result, if any.
        """
        raise NotImplementedError()

    @abstractmethod
    def get_current_position_mm(self, homed_up: bool = True):
        """Return the current absolute position in millimeters.

        :param homed_up: Whether the configured home point is at the upward end.
        :return: Current position in millimeters, or ``None`` when unknown.
        """
        raise NotImplementedError()

    @abstractmethod
    def run_to_position(
        self,
        position_mm: float,
        speed_mm_s: float = None,
        acceleration_mm_s2: float = None,
        homed_up: bool = True,
    ):
        """Move to an absolute position in the homed coordinate system.

        :param position_mm: Target absolute position in millimeters.
        :param speed_mm_s: Optional travel speed in millimeters per second.
        :param acceleration_mm_s2: Optional acceleration in millimeters per second squared.
        :param homed_up: Whether the configured home point is at the upward end.
        """
        raise NotImplementedError()

    @abstractmethod
    def is_homing_found(self):
        """Report whether the driver has a known home reference.

        :return: ``True`` when the driver has been homed.
        """
        raise NotImplementedError()

    # --------------- MOTOR CONFIGURATION ---------------

    @abstractmethod
    def set_speed_rps(self, rps: float):
        """Set the driver's maximum speed in rotations per second.

        :param rps: Rotations per second.
        """
        raise NotImplementedError()

    def set_speed(self, speed_mm_s: float):
        """Set the motor speed.

        :param speed_mm_s: The speed in mm/s
        """
        if speed_mm_s is None:
            return
        rps = self.mechanical_setup.mm_s_to_rps(speed_mm_s)
        self.set_speed_rps(rps)

    @abstractmethod
    def set_acceleration_rpss(self, rpss: float):
        """Set the driver's maximum acceleration in rotations per second squared.

        :param rpss: Rotations per second squared.
        """
        raise NotImplementedError()

    def set_acceleration(self, acceleration_mm_s2: float):
        """Set the motor acceleration.

        :param acceleration_mm_s2: The acceleration/deceleration to use for the movement in mm/s^2
        """
        if acceleration_mm_s2 is None:
            return
        rpss = self.mechanical_setup.mm_s2_to_rpss(acceleration_mm_s2)
        self.set_acceleration_rpss(rpss)

    @abstractmethod
    def set_microsteps(self, microsteps: int):
        """Set the microstep resolution.

        :param microsteps: Microsteps per full step.
        """
        raise NotImplementedError()

    @abstractmethod
    def get_microsteps(self) -> int:
        """Return the current microstep setting.

        :return: Microsteps per full step.
        """
        raise NotImplementedError()

    @abstractmethod
    def set_current(self, current_mA: float):
        """Set the motor run current.

        :param current_mA: Run current in milliamps.
        """
        raise NotImplementedError()

    @abstractmethod
    def set_current_standstill(self, current_mA: float):
        """Set the motor standstill current.

        :param current_mA: Standstill current in milliamps.
        """
        raise NotImplementedError()

    @abstractmethod
    def add_log_handler(self, handler):
        """Attach a log handler to the driver logger.

        :param handler: Logging handler to attach.
        """
        raise NotImplementedError()

    @abstractmethod
    def remove_log_handler(self, handler):
        """Detach a log handler from the driver logger.

        :param handler: Logging handler to detach.
        """
        raise NotImplementedError()

    @abstractmethod
    def cleanup(self):
        """Release hardware resources held by the driver."""
        raise NotImplementedError()
