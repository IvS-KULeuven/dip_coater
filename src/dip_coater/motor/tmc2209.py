from TMC_2209.TMC_2209_StepperDriver import *
from TMC_2209._TMC_2209_logger import Loglevel
from TMC_2209._TMC_2209_move import MovementAbsRel, StopMode
import time
import logging
import asyncio
import platform

from dip_coater.gpio import get_gpio_instance, GpioEdge, GpioState
from dip_coater.motor.motor_driver_interface import MotorDriver


class TMC2209_MotorDriver(MotorDriver):
    homing_found = False
    # Stores the limit switch pin and the corresponding edge trigger event
    limit_switch_bindings = {}

    """ Class to control the TMC2209 motor driver for the dip coater"""
    def __init__(self, app_state, step_mode: int = 8, current_mA: int = 1000, current_standstill_mA: int = 150,
                 invert_direction: bool = False, interpolation: bool = True,
                 spread_cycle: bool = False, loglevel: Loglevel = Loglevel.ERROR,
                 log_handlers: list = None,
                 log_formatter: logging.Formatter = None):
        """ Initialize the motor driver

        :param app_state: The application state to use for the motor driver
        :param step_mode: The step mode to set (1, 2, 4, 8, 16, 32, 64, 128, 256)
        :param current_mA: The current to set for the motor driver in mA
        :param current_standstill_mA: The current to set for the motor driver in mA when the motor is at standstill
        :param invert_direction: Whether to invert the direction of the motor (default: False)
        :param interpolation: Whether to use interpolation for the motor driver
        :param spreadcycle: Whether to use spread_cycle for the motor driver (true) or
                    stealthchop (false)
        :param loglevel: The log level to set for the motor driver (NONE, ERROR, INFO, DEBUG,
                    MOVEMENT, ALL)
        :param log_handlers: The log handlers to use for the motor driver
                    (default: None = log to console)
        :param log_formatter: The log formatter log the motor driver messages with
                    (default: None = use default formatter)
        """
        super().__init__(app_state.mechanical_setup)

        # Get the appropriate GPIO instance
        self.GPIO = app_state.gpio

        # GPIO pins
        self.en_pin = 11
        self.step_pin = 9
        self.dir_pin = 10
        self.diag_pin = 5

        # Motor driver
        if platform.system() == "Darwin" or platform.system() == "Windows":
            print("Running on non-Raspberry Pi system. Using mock TMC2209 driver.")
            self.tmc = TMC_2209(self.en_pin, self.step_pin, self.dir_pin, loglevel=loglevel,
                                log_handlers=log_handlers,
                                serialport=None, skip_uart_init=True)
        else:
            self.tmc = TMC_2209(self.en_pin, self.step_pin, self.dir_pin, loglevel=loglevel,
                                log_handlers=log_handlers,
                                log_formatter=log_formatter)
        # Set motor driver settings
        self.tmc.set_vactual(0)      # Motor is not controlled by UART
        self.tmc.set_direction_reg(invert_direction)
        self.current = current_mA
        self.current_standstill = current_standstill_mA
        self.tmc.set_pdn_disable(False)
        self.set_current(current_mA)
        self.set_current_standstill(current_standstill_mA)
        self.tmc.set_interpolation(interpolation)
        self.tmc.set_spreadcycle(spread_cycle)  # True: spreadcycle, False: stealthchop
        self.tmc.set_microstepping_resolution(step_mode)  # 1, 2, 4, 8, 16, 32, 64, 128, 256
        self.tmc.set_internal_rsense(False)

        self.tmc.set_movement_abs_rel(MovementAbsRel.RELATIVE)
        self.microsteps = step_mode

    # --------------- MOTOR CONTROL ---------------

    def enable_motor(self):
        """ Arm the motor"""
        self.tmc.set_motor_enabled(True)
        time.sleep(0.3)

    def disable_motor(self):
        """ Disarm the motor """
        self.tmc.set_motor_enabled(False)

    def move(self, distance_mm: float, speed_mm_s: float, acceleration_mm_s2: float = 0,
             limit_switch_pins: list = None):
        """ Drive the motor to move the coater up or down by the given distance at the given speed

        :param distance_mm: The distance to move the coater in mm
                    (positive for up, negative for down)
        :param speed_mm_s: The speed at which to move the coater in mm/s (always positive)
        :param acceleration_mm_s2: The acceleration/deceleration to use for the movement in mm/s^2
                    (default: 0)
        :param limit_switch_pins: The GPIO pins of the limit switches to use for stopping the motor
                    (default: None)
        """
        if limit_switch_pins is not None:
            for pin in limit_switch_pins:
                if self._is_limit_switch_triggered(pin):
                    raise ValueError(f"Limit switch on pin {pin} is triggered. "
                                     f"Please check the limit switches.")
        revs = self.mechanical_setup.mm_to_revs(distance_mm)
        rps = self.mechanical_setup.mm_s_to_rps(speed_mm_s)
        rpss = self.mechanical_setup.mm_s2_to_rpss(acceleration_mm_s2)
        self.rotate(revs, rps, rpss)

    def rotate(self, revs: float, rps: float, rpss: float = None):
        self.set_speed_rps(rps)
        self.set_acceleration_rpss(rpss)
        self.tmc.run_to_position_revolutions_threaded(revs)

    def move_up(self, distance_mm: float, speed_mm_s: float, acceleration_mm_s2: float = None,
                limit_switch_pins: list = None, *args, **kwargs):
        """ Move the coater up by the given distance at the given speed

        :param distance_mm: The distance to move the coater up in mm
        :param speed_mm_s: The speed at which to move the coater up in mm/s
        :param acceleration_mm_s2: The acceleration/deceleration to use for the movement in mm/s^2
                    (default: None = default accel)
        :param limit_switch_pins: The GPIO pins of the limit switches to use for stopping the motor
                    (default: None)
        """
        self.move(distance_mm, speed_mm_s, acceleration_mm_s2, limit_switch_pins)

    def move_down(self, distance_mm: float, speed_mm_s: float, acceleration_mm_s2: float = None,
                  limit_switch_pins: list = None, *args, **kwargs):
        """ Move the coater down by the given distance at the given speed

        :param distance_mm: The distance to move the coater down in mm
        :param speed_mm_s: The speed at which to move the coater down in mm/s
        :param acceleration_mm_s2: The acceleration/deceleration to use for the movement in mm/s^2
                    (default: None = default accel)
        :param limit_switch_pins: The GPIO pins of the limit switches to use for stopping the motor
                    (default: None)
        """
        self.move(-distance_mm, speed_mm_s, acceleration_mm_s2, limit_switch_pins)

    def stop_motor(self, stop_mode: StopMode = StopMode.HARDSTOP):
        """ Stop the motor when it is moving

        :param stop_mode: The stop mode to use (SOFTSTOP, HARDSTOP)
        """
        self.tmc.stop(stop_mode)

    def wait_for_motor_done(self) -> StopMode:
        """ Wait for the motor to finish moving

        :return: The StopMode of the movement (StopMode.NO for normal stop, other StopMode for
                    early stop)
        """
        return self.tmc.wait_for_movement_finished_threaded()

    async def wait_for_motor_done_async(self) -> StopMode:
        """ Wait for the motor to finish moving asynchronously

        :return: The StopMode of the movement (StopMode.NO for normal stop, other StopMode for early stop)
        """
        while self.tmc.distance_to_go() > 0:
            await asyncio.sleep(0.1)  # Check every 100ms
        return self.tmc.wait_for_movement_finished_threaded()

    def do_limit_switch_homing(self, limit_switch_up_pin: int, limit_switch_down_pin: int,
                               distance_mm: float, speed_mm_s: float = 2,
                               switch_up_nc: bool = True, switch_down_nc: bool = True) -> bool:
        """ Perform the homing routine for the motor driver using limit switches

        !!! Removes the existing limit switch event bindings !!!

        :param limit_switch_up_pin: The GPIO pin of the NC (normally closed) limit switch at the
                    top of the guide
        :param limit_switch_down_pin: The GPIO pin of the NC (normally closed)  limit switch at the
                    bottom of the guide
        :param distance_mm: The maximal distance to move the coater in mm (positive for up, negative
                    for down)
        :param speed_mm_s: The speed to use for the homing routine in mm/s (default: 2 mm/s)
        :param switch_up_nc: Whether the top limit switch is normally closed (NC) or normally open
                    (NO) (default: True)
        :param switch_down_nc: Whether the bottom limit switch is normally closed (NC) or normally
                    open (NO) (default: True)

        :return: True if the homing routine was successful, False otherwise
        """
        # Set up the limit switches IO
        self.GPIO.remove_event_detect(limit_switch_up_pin)
        self.GPIO.remove_event_detect(limit_switch_down_pin)

        # Check whether the homing is done with the top or bottom limit switch
        home_down = distance_mm <= 0
        home_pin = limit_switch_down_pin if home_down else limit_switch_up_pin
        other_pin = limit_switch_up_pin if home_down else limit_switch_down_pin

        # Get the condition for the limit switches (when they are triggered)
        home_switch_nc = switch_down_nc if home_down else switch_up_nc
        other_switch_nc = switch_up_nc if home_down else switch_down_nc
        home_triggered = self.GPIO.input(home_pin) == GpioState.HIGH if home_switch_nc \
            else self.GPIO.input(home_pin) == GpioState.LOW
        other_triggered = self.GPIO.input(other_pin) == GpioState.HIGH if other_switch_nc \
            else self.GPIO.input(other_pin) == GpioState.LOW
        home_trigger_event = GpioEdge.RISING if home_switch_nc else GpioEdge.FALLING
        other_trigger_event = GpioEdge.RISING if other_switch_nc else GpioEdge.FALLING

        # The home switch is already pressed
        if home_triggered:
            if other_triggered:
                raise ValueError("Both limit switches are triggered. "
                                 "Please check the limit switches.")

            # Move the coater away from the home switch to start the homing routine
            if home_down:
                self.move_up(10, speed_mm_s)
                self.wait_for_motor_done()
            else:
                self.move_down(10, speed_mm_s)
                self.wait_for_motor_done()

        # If the limit switch is still triggered after moving away, raise an error
        home_triggered = self.GPIO.input(home_pin) == GpioState.HIGH if home_switch_nc \
            else self.GPIO.input(home_pin) == GpioState.LOW
        if home_triggered:
            raise ValueError("The home switch is still triggered after backing off. "
                             "Please check the limit switches.")

        # Move the coater towards the home switch and wait for the home switch to be triggered
        self.homing_found = False
        self.GPIO.add_event_detect(home_pin, home_trigger_event,
                                   callback=self._stop_homing_callback, bouncetime=5)
        self.GPIO.add_event_detect(other_pin, other_trigger_event,
                                   callback=self._stop_homing_callback_other_pin, bouncetime=5)
        self.move(distance_mm, speed_mm_s)
        self.wait_for_motor_done()
        self.GPIO.remove_event_detect(home_pin)
        self.GPIO.remove_event_detect(other_pin)

        # Move the coater away from the home switch if homing was found
        if self.homing_found:
            if home_down:
                self.move_up(10, speed_mm_s)
                self.wait_for_motor_done()
            else:
                self.move_down(10, speed_mm_s)
                self.wait_for_motor_done()

        return self.homing_found

    def do_stallguard_homing(self, revolutions: int = 25, threshold: int = 100,
                             speed_mm_s: float = 2):
        """ Perform the homing routine for the motor driver using StallGuard

        :param revolutions: The number of revolutions to perform the homing routine. (Default: 25;
                    the max stroke of the
        guide is 100 mm, so 25 revolutions should be enough to reach the top or bottom)
        :param threshold: The threshold to use for the homing routine (default: None)
        :param speed_mm_s: The speed to use for the homing routine in mm/s (default: 2 mm/s)
        """
        # Homing sets the SpreadCycle to StealthChop, so we need to store the original setting and
        # restore it afterwards
        spread_cycle = self.tmc.get_spreadcycle()
        speed_rpm = self.mechanical_setup.mm_s_to_rpm(speed_mm_s)
        self.tmc.do_homing(
            diag_pin=self.diag_pin,
            revolutions=revolutions,
            threshold=threshold,
            speed_rpm=speed_rpm
        )
        self.tmc.set_spreadcycle(spread_cycle)

    def get_current_position_mm(self, homed_up: bool = True):
        """ Get the current position of the motor in mm

        :param homed_up: Whether the motor is homed up (True) or down (False)

        :return: The current position of the motor in mm, or None if the motor is not homed
        """
        if not self.homing_found:
            return None
        steps = self.tmc.get_current_position()
        pos = self.mechanical_setup.distance_for_steps(steps, self.microsteps)
        if homed_up:
            pos = -pos
        return pos

    def run_to_position(self, position_mm: float, speed_mm_s: float = None,
                        acceleration_mm_s2: float = None, homed_up: bool = True):
        """ Set the current position of the motor in mm

        :param position_mm: The position to set the motor to in mm
        :param speed_mm_s: The speed at which to move the motor to the position in mm/s
                    (default: None = use current speed)
        :param acceleration_mm_s2: The acceleration to use for the movement in mm/s^2
                    (default: None = use current acceleration)
        :param homed_up: Whether the motor is homed up (True) or down (False)
        """
        if not self.homing_found:
            raise ValueError("The motor is not homed.")
        steps = self.mechanical_setup.steps_for_distance(position_mm, self.microsteps)
        if homed_up:
            steps = -steps

        self.set_speed(speed_mm_s)
        self.set_acceleration(acceleration_mm_s2)
        self.tmc.run_to_position_steps_threaded(steps, movement_abs_rel=MovementAbsRel.ABSOLUTE)

    # --------------- MOTOR CONFIGURATION ---------------

    def set_microsteps(self, microsteps: int):
        self.microsteps = microsteps
        self.tmc.set_microstepping_resolution(microsteps)

    def get_microsteps(self) -> int:
        return self.tmc.get_microstepping_resolution()

    def set_current(self, current_mA: int = 1000):
        """ Set the current of the motor driver

        :param current: The current to set for the motor driver in mA
        """
        self.current = current_mA
        multiplier = self.calculate_hold_current_multiplier()
        self.tmc.set_current(current_mA, hold_current_multiplier=multiplier, pdn_disable=False)

    def set_current_standstill(self, current_mA: int = 150):
        self.current_standstill = current_mA
        multiplier = self.calculate_hold_current_multiplier()
        self.tmc.set_current(self.current, hold_current_multiplier=multiplier, pdn_disable=False)

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

    def set_spread_cycle(self, spread_cycle: bool = False):
        """ Set the spread cycle/stealth chop setting of the motor driver

        :param spread_cycle: Whether to use spread_cycle for the motor driver (true) or
                    stealth chop (false)
        """
        self.tmc.set_spreadcycle(spread_cycle)

    def set_loglevel(self, loglevel: Loglevel = Loglevel.INFO):
        """ Set the log level for the motor driver

        :param loglevel: The log level to set for the motor driver (NONE, ERROR, INFO, DEBUG,
                    MOVEMENT, ALL)
        """
        self.tmc.tmc_logger.set_loglevel(loglevel)

    def set_speed_rps(self, rps: float):
        if rps is None:
            return
        steps_per_second = self.mechanical_setup.rps_to_stepss(rps, self.microsteps)
        self.tmc.set_max_speed(steps_per_second)

    def set_acceleration_rpss(self, rpss: float):
        if rpss is None:
            return
        steps_per_second2 = self.mechanical_setup.rpss_to_stepss(rpss, self.microsteps)
        self.tmc.set_acceleration(steps_per_second2)

    def bind_limit_switch(self, limit_switch_pin: int, NC: bool = True):
        """ Bind a limit switch to stop the motor driver if it is triggered.

        :param limit_switch_pin: The GPIO pin of the limit switch
        :param NC: Whether the limit switch is normally closed (NC) or normally open (NO)
                    (default: True)
            For safety reasons, it is recommended to use NC limit switches
        """
        event = GpioEdge.RISING if NC else GpioEdge.FALLING
        self.limit_switch_bindings[limit_switch_pin] = event
        self.GPIO.remove_event_detect(limit_switch_pin)
        self.GPIO.add_event_detect(limit_switch_pin, event, callback=self._stop_motor_callback, bouncetime=5)

    # --------------- HELPER METHODS ---------------

    def calculate_hold_current_multiplier(self):
        return self.current_standstill / self.current

    def read_back_config(self):
        self.tmc.read_ioin()
        self.tmc.read_chopconf()
        self.tmc.read_drv_status()
        self.tmc.read_gconf()

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
        if event == GpioEdge.RISING:
            return self.GPIO.input(pin_number) == GpioState.HIGH
        elif event == GpioEdge.FALLING:
            return self.GPIO.input(pin_number) == GpioState.LOW
        else:
            return False

    def _stop_homing_callback(self, home_pin):
        if self._wait_for_debounce(home_pin):
            self.homing_found = True
            self.stop_motor(StopMode.HARDSTOP)
            self.tmc.set_current_position(0)

    def _stop_homing_callback_other_pin(self, other_pin):
        if self._wait_for_debounce(other_pin):
            self.homing_found = False
            self.stop_motor(StopMode.HARDSTOP)
            raise ValueError("The other limit switch was triggered. "
                             "Please check the limit switches.")

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

    def cleanup(self):
        """ Clean up the motor driver for shutdown"""
        self.disable_motor()
        self.GPIO.cleanup()
        del self.tmc


if __name__ == "__main__":
    # ======== SETTINGS ========
    # Step mode
    _step_mode = 8  # 1 (full), 2 (half), 4 (1/4), 8, 16, 32, 64, 128, 256

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
    motor_driver = TMC2209_MotorDriver(get_gpio_instance(), step_mode=_step_mode,
                                       loglevel=_loglevel)

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
