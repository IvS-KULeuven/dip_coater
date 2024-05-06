from TMC_2209.TMC_2209_StepperDriver import *
from TMC_2209._TMC_2209_logger import Loglevel
from TMC_2209._TMC_2209_move import MovementAbsRel, StopMode
import time
import logging
import asyncio
from RPi import GPIO

# ======== CONSTANTS ========
TRANS_PER_REV = 4  # The vertical translation in mm of the coater for one revolution of the motor


class TMC2209_MotorDriver:
    homing_found = False
    limit_switch_bindings = {}      # Stores the limit switch pin and the corresponding edge trigger event

    """ Class to control the TMC2209 motor driver for the dip coater"""
    def __init__(self, stepmode: int = 8, current: int = 1000, invert_direction: bool = False, interpolation: bool = True,
                 spread_cycle: bool = False, loglevel: Loglevel = Loglevel.ERROR, log_handlers: list = None,
                 log_formatter: logging.Formatter = None):
        """ Initialize the motor driver

        :param stepmode: The step mode to set (1, 2, 4, 8, 16, 32, 64, 128, 256)
        :param current: The current to set for the motor driver in mA
        :param invert_direction: Whether to invert the direction of the motor (default: False)
        :param interpolation: Whether to use interpolation for the motor driver
        :param spreadcycle: Whether to use spread_cycle for the motor driver (true) or stealthchop (false)
        :param loglevel: The log level to set for the motor driver (NONE, ERROR, INFO, DEBUG, MOVEMENT, ALL)
        :param log_handlers: The log handlers to use for the motor driver (default: None = log to console)
        :param log_formatter: The log formatter log the motor driver messages with (default: None = use default formatter)
        """
        # GPIO pins
        GPIO.setmode(GPIO.BCM)
        self.en_pin = 11
        self.step_pin = 9
        self.dir_pin = 10
        self.diag_pin = 5

        # Motor driver
        self.tmc = TMC_2209(self.en_pin, self.step_pin, self.dir_pin, loglevel=loglevel, log_handlers=log_handlers,
                            log_formatter=log_formatter)

        # Set motor driver settings
        self.tmc.set_vactual(False)      # Motor is not controlled by UART
        self.tmc.set_direction_reg(invert_direction)
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

    def set_direction(self, invert_direction: bool = False):
        """ Set the direction of the motor driver

        :param invert_direction: Whether to invert the direction of the motor (default: False)
        """
        self.tmc.set_direction_reg(invert_direction)

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

    def drive_motor(self, distance_mm: float, speed_mm_s: float, acceleration_mm_s2: float = 0, limit_switch_pins: list = None):
        """ Drive the motor to move the coater up or down by the given distance at the given speed

        :param distance_mm: The distance to move the coater in mm (positive for up, negative for down)
        :param speed_mm_s: The speed at which to move the coater in mm/s (always positive)
        :param acceleration_mm_s2: The acceleration/deceleration to use for the movement in mm/s^2 (default: 0)
        :param limit_switch_pins: The GPIO pins of the limit switches to use for stopping the motor (default: None)
        """
        if limit_switch_pins is not None:
            for pin in limit_switch_pins:
                if self._is_limit_switch_triggered(pin):
                    raise ValueError(f"Limit switch on pin {pin} is triggered. Please check the limit switches.")
        revs = self.calculate_revs_from_distance(distance_mm)
        self.set_speed(speed_mm_s)
        self.set_acceleration(acceleration_mm_s2)
        self.tmc.run_to_position_revolutions_threaded(revs)

    def set_speed(self, speed_mm_s: float):
        """ Set the speed at which to move the coater

        :param speed_mm_s: The speed at which to move the coater in mm/s
        """
        if speed_mm_s is None:
            return
        rps = self.calculate_rps_from_speed(speed_mm_s)
        max_speed = rps * self.tmc.read_steps_per_rev()
        self.tmc.set_max_speed(max_speed)

    def set_acceleration(self, acceleration_mm_s2: float):
        """ Set the acceleration at which to move the coater

        :param acceleration_mm_s2: The acceleration/deceleration to use for the movement in mm/s^2
        """
        if acceleration_mm_s2 is None:
            return
        rpss = self.calculate_rpss_from_acceleration(acceleration_mm_s2)
        acceleration = rpss * self.tmc.read_steps_per_rev()
        self.tmc.set_acceleration(acceleration)

    def wait_for_motor_done(self) -> StopMode:
        """ Wait for the motor to finish moving

        :return: The StopMode of the movement (StopMode.NO for normal stop, other StopMode for early stop)
        """
        return self.tmc.wait_for_movement_finished_threaded()

    async def wait_for_motor_done_async(self) -> StopMode:
        """ Wait for the motor to finish moving asynchronously

        :return: The StopMode of the movement (StopMode.NO for normal stop, other StopMode for early stop)
        """
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, self.wait_for_motor_done)
        return result

    def move_up(self, distance_mm: float, speed_mm_s: float, acceleration_mm_s2: float = 0, limit_switch_pins: list = None):
        """ Move the coater up by the given distance at the given speed

        :param distance_mm: The distance to move the coater up in mm
        :param speed_mm_s: The speed at which to move the coater up in mm/s
        :param acceleration_mm_s2: The acceleration/deceleration to use for the movement in mm/s^2 (default: 0)
        :param limit_switch_pins: The GPIO pins of the limit switches to use for stopping the motor (default: None)
        """
        self.drive_motor(distance_mm, speed_mm_s, acceleration_mm_s2, limit_switch_pins)

    def move_down(self, distance_mm: float, speed_mm_s: float, acceleration_mm_s2: float = 0, limit_switch_pins: list = None):
        """ Move the coater down by the given distance at the given speed

        :param distance_mm: The distance to move the coater down in mm
        :param speed_mm_s: The speed at which to move the coater down in mm/s
        :param acceleration_mm_s2: The acceleration/deceleration to use for the movement in mm/s^2 (default: 0)
        :param limit_switch_pins: The GPIO pins of the limit switches to use for stopping the motor (default: None)
        """
        self.drive_motor(-distance_mm, speed_mm_s, acceleration_mm_s2, limit_switch_pins)

    def stop_motor(self, stop_mode: StopMode = StopMode.HARDSTOP):
        """ Stop the motor when it is moving

        :param stop_mode: The stop mode to use (SOFTSTOP, HARDSTOP)
        """
        self.tmc.stop(stop_mode)

    def bind_limit_switch(self, limit_switch_pin: int, NC: bool = True):
        """ Bind a limit switch to stop the motor driver if it is triggered.

        :param limit_switch_pin: The GPIO pin of the limit switch
        :param NC: Whether the limit switch is normally closed (NC) or normally open (NO) (default: True)
            For safety reasons, it is recommended to use NC limit switches
        """
        event = GPIO.RISING if NC else GPIO.FALLING
        self.limit_switch_bindings[limit_switch_pin] = event
        GPIO.add_event_callback(limit_switch_pin, callback=self._stop_motor_callback)

    def _stop_motor_callback(self, pin_number):
        if self._wait_for_debounce(pin_number):
            self.stop_motor(StopMode.HARDSTOP)

    def _wait_for_debounce(self, pin_number, debounce_time_ms=10) -> bool:
        """ Wait for the debounce time of the limit switch

        :param pin_number: The GPIO pin of the limit switch
        :param debounce_time_ms: The debounce time in ms

        :return: True if the limit switch is triggered, False otherwise
        """
        time.sleep(debounce_time_ms / 1000)
        return self._is_limit_switch_triggered(pin_number)

    def _is_limit_switch_triggered(self, pin_number) -> bool:
        """ Check whether the limit switch is triggered

        :param pin_number: The GPIO pin of the limit switch

        :return: True if the limit switch is triggered (pressed), False otherwise
        """
        event = self.limit_switch_bindings[pin_number]
        if event == GPIO.RISING:
            return GPIO.input(pin_number) == 1
        elif event == GPIO.FALLING:
            return GPIO.input(pin_number) == 0
        else:
            return False

    def do_limit_switch_homing(self, limit_switch_up_pin: int, limit_switch_down_pin: int,
                               distance_mm: float, speed_mm_s: float = 2,
                               switch_up_nc: bool = True, switch_down_nc: bool = True) -> bool:
        """ Perform the homing routine for the motor driver using limit switches

        !!! Removes the existing limit switch event bindings !!!

        :param limit_switch_up_pin: The GPIO pin of the NC (normally closed) limit switch at the top of the guide
        :param limit_switch_down_pin: The GPIO pin of the NC (normally closed)  limit switch at the bottom of the guide
        :param distance_mm: The maximal distance to move the coater in mm (positive for up, negative for down)
        :param speed_mm_s: The speed to use for the homing routine in mm/s (default: 2 mm/s)
        :param switch_up_nc: Whether the top limit switch is normally closed (NC) or normally open (NO) (default: True)
        :param switch_down_nc: Whether the bottom limit switch is normally closed (NC) or normally open (NO) (default: True)

        :return: True if the homing routine was successful, False otherwise
        """
        # Set up the limit switches IO
        GPIO.remove_event_detect(limit_switch_up_pin)
        GPIO.remove_event_detect(limit_switch_down_pin)

        # Check whether the homing is done with the top or bottom limit switch
        home_down = distance_mm <= 0
        home_pin = limit_switch_down_pin if home_down else limit_switch_up_pin
        other_pin = limit_switch_up_pin if home_down else limit_switch_down_pin

        # Get the condition for the limit switches (when they are triggered)
        home_switch_nc = switch_down_nc if home_down else switch_up_nc
        other_switch_nc = switch_up_nc if home_down else switch_down_nc
        home_triggered = GPIO.input(home_pin) == 1 if home_switch_nc else GPIO.input(home_pin) == 0
        other_triggered = GPIO.input(other_pin) == 1 if other_switch_nc else GPIO.input(other_pin) == 0
        home_trigger_event = GPIO.RISING if home_switch_nc else GPIO.FALLING
        other_trigger_event = GPIO.RISING if other_switch_nc else GPIO.FALLING

        # The home switch is already pressed
        if home_triggered:
            if other_triggered:
                raise ValueError("Both limit switches are triggered. Please check the limit switches.")

            # Move the coater away from the home switch to start the homing routine
            if home_down:
                self.move_up(10, speed_mm_s)
                self.wait_for_motor_done()
            else:
                self.move_down(10, speed_mm_s)
                self.wait_for_motor_done()

        # If the limit switch is still triggered after moving away, raise an error
        home_triggered = GPIO.input(home_pin) == 1 if home_switch_nc else GPIO.input(home_pin) == 0
        if home_triggered:
            raise ValueError("The home switch is still triggered after backing off. Please check the limit switches.")

        # Move the coater towards the home switch and wait for the home switch to be triggered
        self.homing_found = False
        GPIO.add_event_detect(home_pin, home_trigger_event, callback=self._stop_homing_callback, bouncetime=5)
        GPIO.add_event_detect(other_pin, other_trigger_event, callback=self._stop_homing_callback_other_pin, bouncetime=5)
        self.drive_motor(distance_mm, speed_mm_s)
        self.wait_for_motor_done()
        GPIO.remove_event_detect(home_pin)
        GPIO.remove_event_detect(other_pin)

        # Move the coater away from the home switch if homing was found
        if self.homing_found:
            if home_down:
                self.move_up(10, speed_mm_s)
                self.wait_for_motor_done()
            else:
                self.move_down(10, speed_mm_s)
                self.wait_for_motor_done()

        return self.homing_found

    def _stop_homing_callback(self, home_pin):
        if self._wait_for_debounce(home_pin):
            self.homing_found = True
            self.stop_motor(StopMode.HARDSTOP)
            self.tmc.set_current_position(0)

    def _stop_homing_callback_other_pin(self, other_pin):
        if self._wait_for_debounce(other_pin):
            self.homing_found = False
            self.stop_motor(StopMode.HARDSTOP)
            raise ValueError("The other limit switch was triggered. Please check the limit switches.")

    def do_stallguard_homing(self, revolutions: int = 25, threshold: int = 100, speed_mm_s: float = 2):
        """ Perform the homing routine for the motor driver using StallGuard

        :param revolutions: The number of revolutions to perform the homing routine. (Default: 25; the max stroke of the
        guide is 100 mm, so 25 revolutions should be enough to reach the top or bottom)
        :param threshold: The threshold to use for the homing routine (default: None)
        :param speed_mm_s: The speed to use for the homing routine in mm/s (default: 2 mm/s)
        """
        # Homing sets the spreadcycle to StealthChop, so we need to store the original setting and restore it afterwards
        spread_cycle = self.tmc.get_spreadcycle()
        speed_rpm = speed_mm_s / TRANS_PER_REV * 60
        self.tmc.do_homing(
            diag_pin=self.diag_pin,
            revolutions=revolutions,
            threshold=threshold,
            speed_rpm=speed_rpm
        )
        self.tmc.set_spreadcycle(spread_cycle)

    def is_homing_found(self) -> bool:
        """ Check whether the motor driver is homed

        :return: True if the motor driver is homed, False otherwise
        """
        return self.homing_found

    def test_stallguard_threshold(self, steps: int = None):
        """test method for tuning stallguard threshold

        run this function with your motor settings and your motor load
        the function will determine the minimum stallguard results for each movement phase

        :param steps: number of steps to move the motor
        """
        if steps is None:
            # Perform 2 revolutions
            steps = 2 * self.tmc.read_steps_per_rev()
        self.tmc.test_stallguard_threshold(steps)

    def get_current_position(self, homed_up: bool = True):
        """ Get the current position of the motor in mm

        :param homed_up: Whether the motor is homed up (True) or down (False)

        :return: The current position of the motor in mm, or None if the motor is not homed
        """
        if not self.homing_found:
            return None
        pos = (self.tmc.get_current_position() / self.tmc.read_steps_per_rev()) * TRANS_PER_REV
        if homed_up:
            pos = -pos
        return pos

    def run_to_position(self, position_mm: float, speed_mm_s: float = None, acceleration_mm_s2: float = None,
                        homed_up: bool = True):
        """ Set the current position of the motor in mm

        :param position_mm: The position to set the motor to in mm
        :param speed_mm_s: The speed at which to move the motor to the position in mm/s (default: None = use current speed)
        :param acceleration_mm_s2: The acceleration to use for the movement in mm/s^2 (default: None = use current acceleration)
        :param homed_up: Whether the motor is homed up (True) or down (False)
        """
        if not self.homing_found:
            raise ValueError("The motor is not homed.")
        position_steps = round((position_mm / TRANS_PER_REV) * self.tmc.read_steps_per_rev())
        if homed_up:
            position_steps = -position_steps

        self.set_speed(speed_mm_s)
        self.set_acceleration(acceleration_mm_s2)
        self.tmc.run_to_position_steps_threaded(position_steps, movement_abs_rel=MovementAbsRel.ABSOLUTE)


    def cleanup(self):
        """ Clean up the motor driver for shutdown"""
        self.disable_motor()
        del self.tmc

    @staticmethod
    def calculate_revs_from_distance(distance_mm: float) -> float:
        """ Transform distance from the linear to the angular domain

        :param distance_mm: The distance to move the coater in mm (positive for up, negative for down)

        :return: The number of revolutions to achieve the desired distance
        """
        return distance_mm / TRANS_PER_REV

    @staticmethod
    def calculate_rps_from_speed(speed_mm_s: float) -> float:
        """ Transform speed from the linear to the angular domain

        :param speed_mm_s: The speed at which to move the coater in mm/s (always positive)

        :return: The number of revolutions per second to achieve the desired speed
        """
        return speed_mm_s / TRANS_PER_REV

    @staticmethod
    def calculate_rpss_from_acceleration(acceleration_mm_s2: float = 0) -> float:
        """ Transform acceleration from the linear to the angular domain

        :param acceleration_mm_s2: The acceleration/deceleration to use for the movement in mm/s^2 (default: 0)

        :return: The number of revolutions per second per second to achieve the desired acceleration
        """
        return acceleration_mm_s2 / TRANS_PER_REV


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
