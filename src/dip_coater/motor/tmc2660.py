"""
Move a motor back and forth using velocity and position mode of the TMC2660.
"""
import logging
import asyncio
from pytrinamic.connections import ConnectionManager
from pytrinamic.evalboards import TMC2660_eval
from pytrinamic.modules import Landungsbruecke

from dip_coater.logging.tmc2660_logger import TMC2660Logger, TMC2660LogLevel
from dip_coater.motor.motor_driver_interface import MotorDriver


class VSenseFullScale:
    """
    VSense full scale values for the TMC2660.
    """
    VSENSE_FULL_SCALE_305mV = 0
    VSENSE_FULL_SCALE_165mV = 1


class ChopperMode:
    # SpreadCycle chopper mode (provides a smoother operation and greater power efficiency over a wide range of speed
    # and load)
    SPREAD_CYCLE = 0
    # Classic constant TOff chopper mode
    CONSTANT_TOFF = 1


class StepDirSource:
    # Use the internal motion controller for step and direction signals
    INTERNAL = 0
    # Use the Step/Dir input pins for step and direction signals
    EXTERNAL = 1


class MotorDriverTMC2660(MotorDriver):
    def __init__(self, app_state, interface_type="usb_tmcl", port="interactive",
                 step_mode: int = 8, current_mA: int = 2000, current_standstill_mA: int = 250,
                 chopper_mode: ChopperMode = ChopperMode.SPREAD_CYCLE,
                 vsense_full_scale: int = VSenseFullScale.VSENSE_FULL_SCALE_305mV,
                 step_dir_source: StepDirSource = StepDirSource.INTERNAL,
                 loglevel: TMC2660LogLevel = TMC2660LogLevel.ERROR, log_handlers: list = None,
                 log_formatter: logging.Formatter = None):
        super().__init__(app_state.mechanical_setup)

        self.app_state = app_state

        # Set up logging
        self.logger = TMC2660Logger(
            loglevel=loglevel,
            handlers=log_handlers,
            formatter=log_formatter
        )

        # Set up the TMC2660 driver and motor
        interface_txt = f"--interface {interface_type}" if interface_type else ""
        port_txt = f"--port {port}" if port else ""
        self.interface = ConnectionManager(f"{interface_txt} {port_txt}").connect()
        self.eval_board = TMC2660_eval(self.interface)
        self.lb = Landungsbruecke(self.interface)
        self.bank = 0
        self.axis = 0
        self.motor = self.eval_board.motors[self.axis]
        self.vsense_fs = vsense_full_scale
        self.rsense = 100  # Sense resistor value in mOhm

        # Set up dummy driver interface
        self.is_dummy = True if interface_type == "dummy_tmcl" else False
        if self.is_dummy:
            self.logger.log("Using dummy driver interface", TMC2660LogLevel.INFO)
            # Initialize dummy values
            self.dummy_values = {
                self.lb.GP.DriversEnable: False,
                self.motor.AP.PositionReachedFlag: True,
                self.motor.AP.MicrostepResolution: step_mode,
                self.motor.AP.VSense: VSenseFullScale.VSENSE_FULL_SCALE_305mV,
                self.motor.AP.MaxCurrent: self._convert_current_to_value(current_mA),
                self.motor.AP.StandbyCurrent: self._convert_current_to_value(current_standstill_mA),
                self.motor.AP.MaxVelocity: self.app_state.mechanical_setup.rps_to_stepss(1, step_mode),
                self.motor.AP.MaxAcceleration: self.app_state.mechanical_setup.rpss_to_stepss(1, step_mode),
                self.motor.AP.ActualPosition: 0,
            }

        # Configure the motor
        self.disable_motor()
        self.set_step_dir_source(step_dir_source)
        self.set_chopper_mode(chopper_mode)
        self.set_microsteps(step_mode)
        self.direction_inverted = False
        self.set_current(current_mA)
        self.set_current_standstill(current_standstill_mA)

    # --------------- MOTOR CONTROL ---------------

    def enable_motor(self):
        self._set_global_parameter(self.lb.GP.DriversEnable, self.bank, 1)
        if self.is_motor_enabled() != 1:
            msg = "Failed to enable motor"
            self.logger.log(msg, TMC2660LogLevel.ERROR)
            raise ValueError(msg)
        self.logger.log("Motor enabled", TMC2660LogLevel.INFO)

    def disable_motor(self):
        self._set_global_parameter(self.lb.GP.DriversEnable, self.bank, 0)
        if self.is_motor_enabled() != 0:
            msg = "Failed to disable motor"
            self.logger.log(msg, TMC2660LogLevel.ERROR)
            raise ValueError(msg)
        self.logger.log("Motor disabled", TMC2660LogLevel.INFO)

    def is_motor_enabled(self):
        return self._get_global_parameter(self.lb.GP.DriversEnable, self.bank)

    def invert_direction(self, invert_direction: bool = False):
        self.direction_inverted = invert_direction
        self.logger.log(f"Direction inverted: {invert_direction}", TMC2660LogLevel.INFO)

    def rotate(self, revs: float, rps: float, rpss: float = None):
        revs = -revs if self.direction_inverted else revs
        self.set_speed_rps(rps)
        self.set_acceleration_rpss(rpss)
        steps = self.mechanical_setup.revs_to_steps(revs, self.microsteps)
        self.logger.log(f"Rotating {revs} revolutions, {steps} steps", TMC2660LogLevel.DEBUG)
        self.interface.move_by(0, int(steps))

    def move(self, distance_mm: float, speed_mm_s: float, acceleration_mm_s2: float = None):
        revs = self.mechanical_setup.mm_to_revs(distance_mm)
        rps = self.mechanical_setup.mm_s_to_rps(speed_mm_s)
        rpss = self.mechanical_setup.mm_s2_to_rpss(acceleration_mm_s2)
        self.rotate(revs, rps, rpss)

    def move_up(self, distance_mm: float, speed_mm_s: float, acceleration_mm_s2: float = None, *args, **kwargs):
        self.move(distance_mm, speed_mm_s, acceleration_mm_s2)

    def move_down(self, distance_mm: float, speed_mm_s: float, acceleration_mm_s2: float = None, *args, **kwargs):
        self.move(-distance_mm, speed_mm_s, acceleration_mm_s2)

    def stop_motor(self):
        self.motor.stop()
        self.logger.log("Motor stopped", TMC2660LogLevel.INFO)

    def get_current_position_mm(self):
        pos = self.get_actual_position()
        return self.mechanical_setup.steps_to_mm(pos, self.microsteps)

    def run_to_position(self, position_mm: float, speed_mm_s: float = None, acceleration_mm_s2: float = None):
        self.set_speed(speed_mm_s)
        self.set_acceleration(acceleration_mm_s2)
        steps = self.mechanical_setup.mm_to_steps(position_mm, self.microsteps)
        self.motor.move_to(steps)

    def is_target_reached(self):
        """Check if the target position and actual position are equal."""
        return self._get_axis_parameter(self.motor.AP.PositionReachedFlag, self.axis)

    def wait_for_motor_done(self):
        while not self.is_target_reached():
            pass
        self.logger.log("Motor done", TMC2660LogLevel.INFO)

    async def wait_for_motor_done_async(self):
        while not self.is_target_reached():
            await asyncio.sleep(0.1)
        self.logger.log("Motor done", TMC2660LogLevel.INFO)

    def is_homing_found(self):
        return False

    # --------------- MOTOR CONFIGURATION ---------------

    def set_microsteps(self, microsteps: int):
        self.verify_microsteps(microsteps)
        self.microsteps = microsteps
        self._set_axis_parameter(self.motor.AP.MicrostepResolution, microsteps)

        verify_microsteps = self.get_microsteps()
        if self.microsteps != verify_microsteps:
            msg = f"Set microsteps {microsteps} does not match read back value {verify_microsteps}"
            self.logger.log(msg, TMC2660LogLevel.ERROR)
            raise ValueError(msg)
        self.logger.log(f"Microsteps set to {microsteps}", TMC2660LogLevel.INFO)

    def get_microsteps(self) -> int:
        mstep = self._get_axis_parameter(self.motor.AP.MicrostepResolution, self.axis)
        if self.is_dummy:
            return mstep
        else:
            return self.microstep_idx_to_steps(mstep)

    def set_vsense_full_scale(self, vsense_full_scale: int):
        if vsense_full_scale not in [VSenseFullScale.VSENSE_FULL_SCALE_305mV, VSenseFullScale.VSENSE_FULL_SCALE_165mV]:
            msg = f"Invalid VSense full scale value: {vsense_full_scale}. Must be 0 or 1."
            self.logger.log(msg, TMC2660LogLevel.ERROR)
            raise ValueError(msg)
        self.vsense_fs = vsense_full_scale
        self._set_axis_parameter(self.motor.AP.VSense, vsense_full_scale)

    def get_vsense_full_scale(self) -> int:
        return self._get_axis_parameter(self.motor.AP.VSense, self.axis)

    def set_current(self, current_mA: float):
        current_value = self._convert_current_to_value(current_mA)
        actual_current_mA = self._convert_value_to_current(current_value)
        self._set_axis_parameter(self.motor.AP.MaxCurrent, current_value)

        verify_current = self.get_current()
        if current_value != verify_current:
            msg = f"Set max current {current_value} does not match read back value {verify_current}"
            self.logger.log(msg, TMC2660LogLevel.ERROR)
            raise ValueError(msg)
        self.logger.log(f"Max current set to {current_mA:.1f} mA, value: {current_value}, actual: "
                         f"{actual_current_mA:.1f} mA", TMC2660LogLevel.INFO)

    def get_current(self):
        return self._get_axis_parameter(self.motor.AP.MaxCurrent, self.axis)

    def set_current_standstill(self, current_mA: float):
        current_value = self._convert_current_to_value(current_mA)
        actual_current_mA = self._convert_value_to_current(current_value)
        self._set_axis_parameter(self.motor.AP.StandbyCurrent, current_value)

        verify_current = self.get_current_standstill()
        if current_value != verify_current:
            msg = f"Set standby current {current_value} does not match read back value {verify_current}"
            self.logger.log(msg, TMC2660LogLevel.ERROR)
            raise ValueError(msg)
        self.logger.log(f"Standstill current set to {current_mA:.1f} mA, value: {current_value}, actual: "
                         f"{actual_current_mA:.1f} mA", TMC2660LogLevel.INFO)

    def get_current_standstill(self):
        return self._get_axis_parameter(self.motor.AP.StandbyCurrent, self.axis)

    def set_speed_rps(self, rps: float):
        if rps is None:
            return
        steps_per_second = self.mechanical_setup.rps_to_stepss(rps, self.microsteps)
        self._set_axis_parameter(self.motor.AP.MaxVelocity, int(steps_per_second))

        verify_speed = self.get_speed_rps()
        if rps != verify_speed:
            msg = f"Set max velocity {rps} does not match read back value {verify_speed}"
            self.logger.log(msg, TMC2660LogLevel.ERROR)
            raise ValueError(msg)
        self.logger.log(f"Max velocity set to {rps:.2f} rps, value: {verify_speed:.2f} rps", TMC2660LogLevel.INFO)

    def get_speed_rps(self) -> float:
        steps_per_second = self._get_axis_parameter(self.motor.AP.MaxVelocity, self.axis)
        return self.mechanical_setup.stepss_to_rps(steps_per_second, self.microsteps)

    def set_acceleration_rpss(self, rpss: float):
        if rpss is None or rpss == 0:
            return
        steps_per_second2 = self.mechanical_setup.rpss_to_stepss(rpss, self.microsteps)
        self._set_axis_parameter(self.motor.AP.MaxAcceleration, int(steps_per_second2))

        verify_acceleration = self.get_acceleration_rpss()
        if rpss != verify_acceleration:
            msg = f"Set max acceleration {rpss} does not match read back value {verify_acceleration}"
            self.logger.log(msg, TMC2660LogLevel.ERROR)
            raise ValueError(msg)
        self.logger.log(f"Max acceleration set to {rpss:.2f} rpss, value: {verify_acceleration:.2f} rpss",
                        TMC2660LogLevel.INFO)

    def get_acceleration_rpss(self) -> float:
        steps_per_second2 = self._get_axis_parameter(self.motor.AP.MaxAcceleration, self.axis)
        return self.mechanical_setup.stepss_to_rpss(steps_per_second2, self.microsteps)

    def set_step_dir_source(self, source: StepDirSource):
        if source not in [StepDirSource.INTERNAL, StepDirSource.EXTERNAL]:
            msg = f"Invalid Step/Dir source: {source}. Must be 0 or 1."
            self.logger.log(msg, TMC2660LogLevel.ERROR)
            raise ValueError(msg)
        self._set_axis_parameter(self.motor.AP.StepDirSource, source)
        self.logger.log(f"Step/Dir source set to {source}", TMC2660LogLevel.INFO)

    # --------------- ADVANCED MOTOR CONFIGURATION ---------------

    # Chopper functions

    def set_chopper_mode(self, mode: ChopperMode):
        """
        Set the chopper mode.

        :param mode: Chopper mode (0 = SpreadCycle, 1 = Constant TOff)
        """
        if mode not in [ChopperMode.SPREAD_CYCLE, ChopperMode.CONSTANT_TOFF]:
            msg = f"Invalid chopper mode: {mode}. Must be 0 or 1."
            self.logger.log(msg, TMC2660LogLevel.ERROR)
            raise ValueError(msg)
        self._set_axis_parameter(self.motor.AP.ConstantTOffMode, mode)
        self.logger.log(f"Chopper mode set to {mode}", TMC2660LogLevel.INFO)

    def configure_chopper_mode_advanced_settings(self, hysteresis_start: int, hysteresis_end: int, blank_time: int,
                                                 off_time: int):
        """
        Configure SpreadCycle chopper mode.

        :param hysteresis_start: Hysteresis start (0 to 8)
        :param hysteresis_end: Hysteresis end (0 to 15)
        :param blank_time: Blank time (0 to 3)
        :param off_time: Off time (0 to 15)
        """
        self._set_axis_parameter(self.motor.AP.ChopperHysteresisStart, hysteresis_start)
        self._set_axis_parameter(self.motor.AP.ChopperHysteresisEnd, hysteresis_end)
        self._set_axis_parameter(self.motor.AP.ChopperBlankTime, blank_time)
        self._set_axis_parameter(self.motor.AP.TOff, off_time)
        self.logger.log("SpreadCycle configured", TMC2660LogLevel.INFO)

    # Interpolation (MicroPlyer)

    def set_interpolation(self, enable: bool):
        """Enable or disable microstep interpolation (MicroPlyer).

        :param enable: Enable or disable interpolation. If enabled, the current microstep resolution will be
         interpolated to 256 microsteps. This brings smooth motor operation of high-resolution microstepping to
         applications originally designed for coarser stepping and reduces pulse bandwidth.
        """
        self._set_axis_parameter(self.motor.AP.Intpol, 1 if enable else 0)
        self.logger.log(f"Interpolation {'enabled' if enable else 'disabled'}", TMC2660LogLevel.INFO)

    # StallGuard

    def set_stallguard_filter(self, enable: bool):
        """Enable or disable StallGuard2 filter.

        :param enable: Enable or disable the StallGuard2 filter. If enabled, the StallGuard2 result will be filtered.
                    False:  Faster response time
                    True:   Filtered mode, updated once for each four fullsteps to compensate for variation in motor
                            construction, highest accuracy.
        """
        self._set_axis_parameter(self.motor.AP.SG2FilterEnable, 1 if enable else 0)
        self.logger.log(f"StallGuard2 filter {'enabled' if enable else 'disabled'}", TMC2660LogLevel.INFO)

    def get_stallguard_result(self) -> int:
        """Get the StallGuard2 result."""
        return self._get_axis_parameter(self.motor.AP.LoadValue, self.axis)

    def set_stallguard_threshold(self, threshold: int):
        """Set the StallGuard2 threshold.

        :param threshold: StallGuard2 threshold (-64 to 63). A lower value results in a higher sensitivity and requires
        less torque to indicate a stall. Values below -10 are not recommended.
        """
        self._set_axis_parameter(self.motor.AP.SG2Threshold, threshold)
        self.logger.log(f"StallGuard2 threshold set to {threshold}", TMC2660LogLevel.INFO)

    # CoolStep functions
    def enable_coolstep(self,
                        min_current: int,
                        current_down_step: int,
                        current_up_step: int,
                        hysteresis: int,
                        threshold_speed: int):
        """
        Enable CoolStep feature.

        :param min_current: Minimum current (0 or 1)
        :param current_down_step: Current down step (0 to 3)
        :param current_up_step: Current up step (0 to 3)
        :param hysteresis: Hysteresis (0 to 15)
        :param threshold_speed: Threshold speed [pps]
        """
        self._set_axis_parameter(self.motor.AP.SEIMIN, min_current)
        self._set_axis_parameter(self.motor.AP.SECDS, current_down_step)
        self._set_axis_parameter(self.motor.AP.SECUS, current_up_step)
        self._set_axis_parameter(self.motor.AP.smartEnergyHysteresis, hysteresis)
        self._set_axis_parameter(self.motor.AP.smartEnergyThresholdSpeed, threshold_speed)
        self.logger.log("CoolStep enabled", TMC2660LogLevel.INFO)

    def disable_coolstep(self):
        """Disable CoolStep feature."""
        self._set_axis_parameter(self.motor.AP.smartEnergyThresholdSpeed, 0)
        self.logger.log("CoolStep disabled", TMC2660LogLevel.INFO)

    def get_coolstep_current(self) -> int:
        """Get the current CoolStep current scaling."""
        return self._get_axis_parameter(self.motor.AP.smartEnergyActualCurrent, self.axis)


    # --------------- HELPER METHODS ---------------

    def get_actual_position(self):
        return self.eval_board.get_axis_parameter(self.motor.AP.ActualPosition, self.axis)

    def microstep_idx_to_steps(self, idx: int) -> int:
        """Convert microstep index (0, 1, 2, 3...) to actual number of microsteps (1, 2, 4, 8...)."""
        if 0 <= idx <= 8:
            return 2 ** idx
        else:
            msg = f"Invalid microstep index: {idx}. Must be between 0 and 8."
            self.logger.log(msg, TMC2660LogLevel.ERROR)
            raise ValueError(msg)

    def verify_microsteps(self, microsteps: int) -> int:
        """ Verify that the microsteps are valid (1, 2, 4, 8...). If so, return the microstep index (0, 1, 2, 3...)."""
        if microsteps in [1, 2, 4, 8, 16, 32, 64, 128, 256]:
            return int.bit_length(microsteps) - 1
        else:
            msg = f"Invalid number of microsteps: {microsteps}. Must be a power of 2 between 1 and 256."
            self.logger.log(msg, TMC2660LogLevel.ERROR)
            raise ValueError(msg)

    def _get_vsense_full_scale_voltage(self) -> int:
        return 305 if self.vsense_fs == VSenseFullScale.VSENSE_FULL_SCALE_305mV else 165

    def _convert_current_to_value(self, current_mA: float) -> int:
        vfs = self._get_vsense_full_scale_voltage()
        value = int((current_mA/1000 * 32 * self.rsense * 1.4142) / vfs) - 1         # 1.4142 = sqrt(2)
        if value < 0 or value > 31:
            msg = f"Invalid current value: {current_mA}. Must be between 0 and 31."
            self.logger.log(msg, TMC2660LogLevel.ERROR)
            raise ValueError(msg)
        return value

    def _convert_value_to_current(self, value: int) -> float:
        if value < 0 or value > 31:
            msg = f"Invalid current value: {value}. Must be between 0 and 31."
            self.logger.log(msg, TMC2660LogLevel.ERROR)
            raise ValueError(msg)
        vfs = self._get_vsense_full_scale_voltage()
        return (value + 1) * vfs / (32 * self.rsense * 1.4142) * 1000         # 1.4142 = sqrt(2)

    def set_loglevel(self, loglevel: TMC2660LogLevel):
        self.logger.set_loglevel(loglevel)
        self.logger.log(f"Log level set to {loglevel.name}", TMC2660LogLevel.INFO)

    def _get_axis_parameter(self, parameter, axis):
        if self.is_dummy:
            return self.dummy_values.get(parameter, 0)
        return self.motor.get_axis_parameter(parameter, axis)

    def _set_axis_parameter(self, parameter, value):
        if self.is_dummy:
            self.dummy_values[parameter] = value
        else:
            self.motor.set_axis_parameter(parameter, value)

    def _get_global_parameter(self, parameter, bank):
        if self.is_dummy:
            return self.dummy_values.get(parameter, 0)
        return self.interface.get_global_parameter(parameter, bank)

    def _set_global_parameter(self, parameter, bank, value):
        if self.is_dummy:
            self.dummy_values[parameter] = value
        else:
            self.interface.set_global_parameter(parameter, bank, value)

    def add_log_handler(self, handler):
        self.logger.add_handler(handler)

    def remove_log_handler(self, handler):
        self.logger.remove_handler(handler)

    def cleanup(self):
        self.disable_motor()
        self.interface.close()
        self.logger.log("Motor driver cleaned up", TMC2660LogLevel.INFO)
