from TMC_2209.TMC_2209_StepperDriver import *
from TMC_2209._TMC_2209_logger import Loglevel
from TMC_2209._TMC_2209_move import MovementAbsRel
import time
from RPi import GPIO

# ======== CONSTANTS ========
TRANS_PER_REV = 8  # The vertical translation in mm of the coater for one revolution of the motor


class TMC2209_MotorDriver:
    """ Class to control the TMC2209 motor driver for the dip coater"""
    def __init__(self, stepmode: int = 8, current: int = 1000, interpolation: bool = True, spread_cycle: bool = False,
                 loglevel: Loglevel = Loglevel.ERROR, log_handlers: list = None):
        """ Initialize the motor driver

        :param stepmode: The step mode to set (1, 2, 4, 8, 16, 32, 64, 128, 256)
        :param current: The current to set for the motor driver in mA
        :param interpolation: Whether to use interpolation for the motor driver
        :param spreadcycle: Whether to use spread_cycle for the motor driver (true) or stealthchop (false)
        :param loglevel: The log level to set for the motor driver (NONE, ERROR, INFO, DEBUG, MOVEMENT, ALL)
        :param log_handlers: The log handlers to use for the motor driver (default: None = log to console)
        """
        # GPIO pins
        GPIO.setmode(GPIO.BCM)
        en_pin = 21
        step_pin = 16
        dir_pin = 26

        # Motor driver
        self.tmc = TMC_2209(en_pin, step_pin, dir_pin, loglevel=loglevel, log_handlers=log_handlers)

        # Set motor driver settings
        self.tmc.set_vactual(False)      # Motor is not controlled by UART
        self.tmc.set_direction_reg(True)
        self.tmc.set_current(current, pdn_disable=False)    # mA
        self.tmc.set_interpolation(interpolation)
        self.tmc.set_spreadcycle(spread_cycle)  # True: spreadcycle, False: stealthchop
        self.tmc.set_microstepping_resolution(stepmode)  # 1, 2, 4, 8, 16, 32, 64, 128, 256
        self.tmc.set_internal_rsense(False)

        self.tmc.set_movement_abs_rel(MovementAbsRel.RELATIVE)

    def read_back_config(self):
        self.tmc.read_ioin()
        self.tmc.read_chopconf()
        self.tmc.read_drv_status()
        self.tmc.read_gconf()

    def set_stepmode(self, _stepmode: int = 4):
        """ Set the step mode of the motor driver

        :param _stepmode: The step mode to set (1, 2, 4, 8, 16, 32, 64, 128, 256)
        """
        self.tmc.set_microstepping_resolution(_stepmode)

    def set_current(self, current: int = 1000):
        """ Set the current of the motor driver

        :param current: The current to set for the motor driver in mA
        """
        self.tmc.set_current(current, pdn_disable=False)

    def set_interpolation(self, interpolation: bool = True):
        """ Set the interpolation setting of the motor driver

        :param interpolation: Whether to use interpolation for the motor driver
        """
        self.tmc.set_interpolation(interpolation)

    def set_spreadcycle(self, spread_cycle: bool = False):
        """ Set the spreadcycle setting of the motor driver

        :param spreadcycle: Whether to use spread_cycle for the motor driver (true) or stealthchop (false)
        """
        self.tmc.set_spreadcycle(spread_cycle)

    def set_loglevel(self, loglevel: Loglevel = Loglevel.INFO):
        """ Set the log level for the motor driver

        :param loglevel: The log level to set for the motor driver (NONE, ERROR, INFO, DEBUG, MOVEMENT, ALL)
        """
        self.tmc.tmc_logger.set_loglevel(loglevel)

    def enable_motor(self):
        """ Arm the motor"""
        self.tmc.set_motor_enabled(True)
        time.sleep(0.3)

    def disable_motor(self):
        """ Disarm the motor """
        self.tmc.set_motor_enabled(False)

    def drive_motor(self, distance_mm: float, speed_mm_s: float, acceleration_mm_s2: float = 0):
        """ Drive the motor to move the coater up or down by the given distance at the given speed

        :param distance_mm: The distance to move the coater in mm (positive for up, negative for down)
        :param speed_mm_s: The speed at which to move the coater in mm/s (always positive)
        :param acceleration_mm_s2: The acceleration/deceleration to use for the movement in mm/s^2 (default: 0)
        """
        revs, rps, rpss = self.calculate_revs_rps_and_rpss(distance_mm, speed_mm_s, acceleration_mm_s2)
        max_speed = rps * self.tmc.read_steps_per_rev()
        acceleration = rpss * self.tmc.read_steps_per_rev()
        self.tmc.set_max_speed(max_speed)
        self.tmc.set_acceleration(acceleration)
        self.tmc.run_to_position_revolutions(revs)

    def move_up(self, distance_mm: float, speed_mm_s: float, acceleration_mm_s2: float = 0):
        """ Move the coater up by the given distance at the given speed

        :param distance_mm: The distance to move the coater up in mm
        :param speed_mm_s: The speed at which to move the coater up in mm/s
        :param acceleration_mm_s2: The acceleration/deceleration to use for the movement in mm/s^2 (default: 0)
        """
        self.drive_motor(distance_mm, speed_mm_s, acceleration_mm_s2)

    def move_down(self, distance_mm: float, speed_mm_s: float, acceleration_mm_s2: float = 0):
        """ Move the coater down by the given distance at the given speed

        :param distance_mm: The distance to move the coater down in mm
        :param speed_mm_s: The speed at which to move the coater down in mm/s
        :param acceleration_mm_s2: The acceleration/deceleration to use for the movement in mm/s^2 (default: 0)
        """
        self.drive_motor(-distance_mm, speed_mm_s, acceleration_mm_s2)

    def cleanup(self):
        """ Clean up the motor driver for shutdown"""
        self.disable_motor()
        del self.tmc

    @staticmethod
    def calculate_revs_rps_and_rpss(distance_mm: float, speed_mm_s: float, acceleration_mm_s2: float = 0):
        """ Calculate how many revolutions the motor should turn at what speed to
            achieve the desired vertical distance translation at the speed.

        :param distance_mm: The distance to move the coater in mm (positive for up, negative for down)
        :param speed_mm_s: The speed at which to move the coater in mm/s (always positive)
        :param acceleration_mm_s2: The acceleration/deceleration to use for the movement in mm/s^2 (default: 0)

        :return: The number of revolutions, revolutions per second, and revolutions per second per second (acceleration)
        to achieve the desired movement
        """
        revs = distance_mm / TRANS_PER_REV
        rps = speed_mm_s / TRANS_PER_REV
        rpss = acceleration_mm_s2 / TRANS_PER_REV
        return revs, rps, rpss


if __name__ == "__main__":
    # ======== SETTINGS ========
    # Step mode
    _stepmode = 8  # 1 (full), 2 (half), 4 (1/4), 8, 16, 32, 64, 128, 256

    # Movement speed in mm/s
    speed_up = 2
    speed_down = 5

    # Time to wait (in s) between going up and down
    wait_time = 5

    # Vertical travel distance in mm
    distance_up = 10
    distance_down = distance_up

    # Max acceleration in mm/s^2
    accel_up = 7.5
    accel_down = accel_up

    # ======== DEBUG SETTINGS =======
    _loglevel = Loglevel.INFO  # NONE, ERROR, INFO, DEBUG, MOVEMENT, ALL

    # ======== INIT ========
    motor_driver = TMC2209_MotorDriver(stepmode=_stepmode, loglevel=_loglevel)

    # ======== MOVE DOWN ========
    motor_driver.move_down(distance_down, speed_down, accel_down)

    # ======== WAIT ========
    time.sleep(wait_time)

    # ======== MOVE UP ========
    motor_driver.move_up(distance_up, speed_up, accel_up)

    # ======== FINISH ========
    motor_driver.disable_motor()
    motor_driver.cleanup()
    print("---\nSCRIPT FINISHED\n---")
