"""
Move a motor back and forth using velocity and position mode of the TMC2660.
"""
import asyncio
import logging
import math
import time
from enum import Enum

try:
    from pytrinamic.connections import ConnectionManager
    from pytrinamic.evalboards import TMC2660_eval
    from pytrinamic.modules import Landungsbruecke
    _PYTRINAMIC_AVAILABLE = True
except ModuleNotFoundError:
    ConnectionManager = None
    TMC2660_eval = None
    Landungsbruecke = None
    _PYTRINAMIC_AVAILABLE = False

from dip_coater.logging.tmc2660_logger import TMC2660Logger, TMC2660LogLevel
from dip_coater.motor_driver.motor_driver_interface import MotorDriver
from dip_coater.motor_driver.tmc2660.tmc2660_dummy import (
    DummyEvalBoard,
    DummyInterface,
    DummyLandungsbruecke,
)


_TARGET_POLL_INTERVAL_S = 0.1


def _require_bool(name: str, value: bool) -> None:
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be a boolean")


def _require_int_range(
    name: str,
    value: int,
    minimum: int,
    maximum: int,
) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be in [{minimum}, {maximum}]")


class VSenseFullScale(Enum):
    """
    VSense full scale values for the TMC2660.
    """
    VSENSE_FULL_SCALE_305mV = (0, 305)
    VSENSE_FULL_SCALE_165mV = (1, 165)

    def __init__(self, value, voltage):
        self._value_ = value
        self.voltage = voltage


class ChopperMode(Enum):
    # SpreadCycle chopper mode (provides a smoother operation and greater power efficiency over a wide range of speed
    # and load)
    SPREAD_CYCLE = (0, "SpreadCycle")
    # Classic constant TOff chopper mode
    CONSTANT_TOFF = (1, "Constant TOff")

    def __init__(self, value, label):
        self._value_ = value
        self.label = label

    @classmethod
    def from_int(cls, value: int):
        for mode in cls:
            if mode.value == value:
                return mode
        raise ValueError(f"No ChopperMode with value {value}")

    @classmethod
    def from_label(cls, label: str):
        for mode in cls:
            if mode.label == label:
                return mode
        raise ValueError(f"No ChopperMode with label {label}")


class StepDirSource(Enum):
    # Use the internal motion controller for step and direction signals
    INTERNAL = 0
    # Use the Step/Dir input pins for step and direction signals
    EXTERNAL = 1


class MotorDriverTMC2660(MotorDriver):
    def __init__(self,
                 app_state,
                 interface_type="usb_tmcl",
                 port="interactive",
                 step_mode: int = 8,
                 current_mA: int = 2000,
                 current_standstill_mA: int = 250,
                 invert_direction: bool = False,
                 chopper_mode: ChopperMode = ChopperMode.SPREAD_CYCLE,
                 stallguard_enabled: bool = True,
                 stallguard_threshold: int = 0,
                 coolstep_enabled: bool = False,
                 coolstep_threshold: int = 0,
                 vsense_full_scale: VSenseFullScale = VSenseFullScale.VSENSE_FULL_SCALE_305mV,
                 step_dir_source: StepDirSource = StepDirSource.INTERNAL,
                 loglevel: TMC2660LogLevel = TMC2660LogLevel.ERROR,
                 log_handlers: list = None,
                 log_formatter: logging.Formatter = None):
        super().__init__(app_state.mechanical_setup)

        self.app_state = app_state

        # Set up logging
        self.logger = TMC2660Logger(
            loglevel=loglevel,
            handlers=log_handlers,
            formatter=log_formatter
        )

        self.is_dummy = (
            interface_type == "dummy_tmcl"
            or app_state.config.USE_DUMMY_DRIVER
        )
        if self.is_dummy:
            self.logger.log("Using dummy driver interface", TMC2660LogLevel.INFO)
        elif not _PYTRINAMIC_AVAILABLE:
            msg = ("pytrinamic is required for the TMC2660 driver. "
                   "Install it or use --use-dummy-driver.")
            self.logger.log(msg, TMC2660LogLevel.ERROR)
            raise ModuleNotFoundError(msg)

        # Set up the TMC2660 driver and motor
        interface_txt = f"--interface {interface_type}" if interface_type else ""
        port_txt = f"--port {port}" if port else ""
        if self.is_dummy:
            self.dummy_values = {}
            self.interface = DummyInterface(self.dummy_values)
            self.lb = DummyLandungsbruecke()
            self.eval_board = DummyEvalBoard(self.dummy_values)
            self.motor = self.eval_board.motors[0]
            self._initialize_motor(
                step_mode=step_mode,
                current_mA=current_mA,
                current_standstill_mA=current_standstill_mA,
                invert_direction=invert_direction,
                chopper_mode=chopper_mode,
                stallguard_enabled=stallguard_enabled,
                stallguard_threshold=stallguard_threshold,
                coolstep_enabled=coolstep_enabled,
                coolstep_threshold=coolstep_threshold,
                vsense_full_scale=vsense_full_scale,
                step_dir_source=step_dir_source,
            )
        else:
            self.interface = ConnectionManager(f"{interface_txt} {port_txt}").connect()
            try:
                self.eval_board = TMC2660_eval(self.interface)
                self.lb = Landungsbruecke(self.interface)
                self._initialize_motor(
                    step_mode=step_mode,
                    current_mA=current_mA,
                    current_standstill_mA=current_standstill_mA,
                    invert_direction=invert_direction,
                    chopper_mode=chopper_mode,
                    stallguard_enabled=stallguard_enabled,
                    stallguard_threshold=stallguard_threshold,
                    coolstep_enabled=coolstep_enabled,
                    coolstep_threshold=coolstep_threshold,
                    vsense_full_scale=vsense_full_scale,
                    step_dir_source=step_dir_source,
                )
            except BaseException:
                try:
                    self.interface.close()
                except Exception:
                    pass
                raise

    def _initialize_motor(
        self,
        *,
        step_mode: int,
        current_mA: int,
        current_standstill_mA: int,
        invert_direction: bool,
        chopper_mode: ChopperMode,
        stallguard_enabled: bool,
        stallguard_threshold: int,
        coolstep_enabled: bool,
        coolstep_threshold: int,
        vsense_full_scale: VSenseFullScale,
        step_dir_source: StepDirSource,
    ) -> None:
        """Finish initialization after the transport objects exist."""
        self.bank = 0
        self.axis = 0
        if not self.is_dummy:
            self.motor = self.eval_board.motors[self.axis]
        self.vsense_fs = vsense_full_scale
        self.rsense = 100  # Sense resistor value in mOhm
        self.homing_found = False

        # Set up motor driver parameters
        self.stallguard_threshold = 0
        self.coolstep_threshold = 0

        # Set up dummy driver interface
        if self.is_dummy:
            # Initialize dummy values
            self.dummy_values.update({
                self.lb.GP.DriversEnable: False,
                self.motor.AP.PositionReachedFlag: True,
                self.motor.AP.MicrostepResolution: self.verify_microsteps(step_mode),
                self.motor.AP.VSense: vsense_full_scale.value,
                self.motor.AP.MaxCurrent: self._convert_current_to_value(current_mA),
                self.motor.AP.StandbyCurrent: self._convert_current_to_value(current_standstill_mA),
                self.motor.AP.MaxVelocity: self.app_state.mechanical_setup.rps_to_stepss(1, step_mode),
                self.motor.AP.MaxAcceleration: self.app_state.mechanical_setup.rpss_to_stepss(1, step_mode),
                self.motor.AP.ActualPosition: 0,
            })

        # Configure the motor
        self.disable_motor()
        self.set_step_dir_source(step_dir_source)
        self.set_vsense_full_scale(vsense_full_scale)
        self.set_chopper_mode(chopper_mode)
        self.set_microsteps(step_mode)
        self.invert_direction(invert_direction)
        self.set_current(current_mA)
        self.set_current_standstill(current_standstill_mA)
        self.set_stallguard_threshold(stallguard_threshold)
        self.set_stallguard_enabled(stallguard_enabled)
        self.set_coolstep_threshold(coolstep_threshold)
        self.set_coolstep_enabled(coolstep_enabled)

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
        _require_bool("invert_direction", invert_direction)
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

    def get_current_position_mm(self, homed_up: bool = True):
        if not self.homing_found:
            return None
        pos = self.get_actual_position()
        raw_position_mm = self.mechanical_setup.steps_to_mm(pos, self.microsteps)
        return raw_position_mm * self._invert_sign() * self._home_sign(homed_up)

    def run_to_position(
        self,
        position_mm: float,
        speed_mm_s: float = None,
        acceleration_mm_s2: float = None,
        homed_up: bool = True,
    ):
        if not self.homing_found:
            raise ValueError("The motor is not homed.")
        self.set_speed(speed_mm_s)
        self.set_acceleration(acceleration_mm_s2)
        raw_position_mm = (
            position_mm * self._invert_sign() * self._home_sign(homed_up)
        )
        steps = self.mechanical_setup.mm_to_steps(
            raw_position_mm, self.microsteps
        )
        self.motor.move_to(steps)

    def is_target_reached(self):
        """Check if the target position and actual position are equal."""
        return self._get_axis_parameter(self.motor.AP.PositionReachedFlag, self.axis)

    def wait_for_motor_done(self):
        while not self.is_target_reached():
            time.sleep(_TARGET_POLL_INTERVAL_S)
        self.logger.log("Motor done", TMC2660LogLevel.INFO)

    async def wait_for_motor_done_async(self):
        while not self.is_target_reached():
            await asyncio.sleep(_TARGET_POLL_INTERVAL_S)
        self.logger.log("Motor done", TMC2660LogLevel.INFO)

    def is_homing_found(self):
        return self.homing_found

    def mark_homed(self):
        self._set_axis_parameter(self.motor.AP.ActualPosition, 0)
        self.homing_found = True

    def clear_homing(self):
        self.homing_found = False

    def _invert_sign(self) -> int:
        return -1 if self.direction_inverted else 1

    @staticmethod
    def _home_sign(homed_up: bool) -> int:
        return -1 if homed_up else 1

    # --------------- MOTOR CONFIGURATION ---------------

    def set_microsteps(self, microsteps: int):
        microstep_index = self.verify_microsteps(microsteps)
        # EvalSystem SAP 140 accepts 1, 2, ..., 256, but GAP 140 on the
        # TMC2660 reports log2(microsteps). Store the readback form only in
        # the dummy backend so it reproduces that asymmetric firmware API.
        parameter_value = microstep_index if self.is_dummy else microsteps
        self._set_axis_parameter(
            self.motor.AP.MicrostepResolution, parameter_value
        )

        verify_microsteps = self.get_microsteps()
        if microsteps != verify_microsteps:
            msg = f"Set microsteps {microsteps} does not match read back value {verify_microsteps}"
            self.logger.log(msg, TMC2660LogLevel.ERROR)
            raise ValueError(msg)
        self.microsteps = microsteps
        self.logger.log(f"Microsteps set to {microsteps}", TMC2660LogLevel.INFO)

    def get_microsteps(self) -> int:
        mstep = self._get_axis_parameter(self.motor.AP.MicrostepResolution, self.axis)
        return self.microstep_idx_to_steps(mstep)

    def set_vsense_full_scale(self, vsense_full_scale: VSenseFullScale):
        if vsense_full_scale not in [VSenseFullScale.VSENSE_FULL_SCALE_305mV, VSenseFullScale.VSENSE_FULL_SCALE_165mV]:
            msg = f"Invalid VSense full scale value: {vsense_full_scale}. Must be 0 or 1."
            self.logger.log(msg, TMC2660LogLevel.ERROR)
            raise ValueError(msg)
        self._set_axis_parameter(self.motor.AP.VSense, vsense_full_scale.value)
        self.vsense_fs = vsense_full_scale

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
        if not math.isclose(rps, verify_speed, rel_tol=1e-3, abs_tol=1e-3):
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
        if not math.isclose(rpss, verify_acceleration, rel_tol=1e-3, abs_tol=1e-3):
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
        self._set_axis_parameter(self.motor.AP.StepDirSource, source.value)
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
        self._set_axis_parameter(self.motor.AP.ConstantTOffMode, mode.value)
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
        _require_int_range("hysteresis_start", hysteresis_start, 0, 8)
        _require_int_range("hysteresis_end", hysteresis_end, 0, 15)
        _require_int_range("blank_time", blank_time, 0, 3)
        _require_int_range("off_time", off_time, 0, 15)
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
        _require_bool("enable", enable)
        self._set_axis_parameter(self.motor.AP.Intpol, 1 if enable else 0)
        self.logger.log(f"Interpolation {'enabled' if enable else 'disabled'}", TMC2660LogLevel.INFO)

    # StallGuard
    def set_stallguard_enabled(self, enable: bool):
        """Enable or disable StallGuard2.

        :param enable: Enable or disable StallGuard2. If enabled, the StallGuard2 feature will be active.
        """
        _require_bool("enable", enable)
        self._set_axis_parameter(self.motor.AP.SG2Threshold, self.stallguard_threshold if enable else 0)
        self.logger.log(f"StallGuard2 {'enabled' if enable else 'disabled'}", TMC2660LogLevel.INFO)

    def set_stallguard_filter_enabled(self, enable: bool):
        """Enable or disable StallGuard2 filter.

        :param enable: Enable or disable the StallGuard2 filter. If enabled, the StallGuard2 result will be filtered.
                    False:  Faster response time
                    True:   Filtered mode, updated once for each four fullsteps to compensate for variation in motor
                            construction, highest accuracy.
        """
        _require_bool("enable", enable)
        self._set_axis_parameter(self.motor.AP.SG2FilterEnable, 1 if enable else 0)
        self.logger.log(f"StallGuard2 filter {'enabled' if enable else 'disabled'}", TMC2660LogLevel.INFO)

    def set_stallguard_threshold(self, threshold: int):
        """Set the StallGuard2 threshold.

        :param threshold: StallGuard2 threshold (-64 to 63). A lower value results in a higher sensitivity and requires
        less torque to indicate a stall. Values below -10 are not recommended.
        """
        _require_int_range("threshold", threshold, -64, 63)
        self._set_axis_parameter(self.motor.AP.SG2Threshold, threshold)
        self.stallguard_threshold = threshold
        self.logger.log(f"StallGuard2 threshold set to {threshold}", TMC2660LogLevel.INFO)

    def get_stallguard_result(self) -> int:
        """Get the StallGuard2 result."""
        return self._get_axis_parameter(self.motor.AP.LoadValue, self.axis)

    # CoolStep functions
    def configure_coolstep(self,
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
        _require_int_range("min_current", min_current, 0, 1)
        _require_int_range("current_down_step", current_down_step, 0, 3)
        _require_int_range("current_up_step", current_up_step, 0, 3)
        _require_int_range("hysteresis", hysteresis, 0, 15)
        _require_int_range("threshold_speed", threshold_speed, 0, (1 << 31) - 1)
        self._set_axis_parameter(self.motor.AP.SEIMIN, min_current)
        self._set_axis_parameter(self.motor.AP.SECDS, current_down_step)
        self._set_axis_parameter(self.motor.AP.SECUS, current_up_step)
        self._set_axis_parameter(self.motor.AP.smartEnergyHysteresis, hysteresis)
        self._set_axis_parameter(self.motor.AP.smartEnergyThresholdSpeed, threshold_speed)
        self.logger.log("CoolStep enabled", TMC2660LogLevel.INFO)

    def set_coolstep_enabled(self, enable: bool):
        """Enable or disable CoolStep feature."""
        _require_bool("enable", enable)
        self._set_axis_parameter(self.motor.AP.smartEnergyThresholdSpeed, self.coolstep_threshold if enable else 0)
        self.logger.log(f"CoolStep {'enabled' if enable else 'disabled'}", TMC2660LogLevel.INFO)

    def set_coolstep_threshold(self, threshold: int):
        """Set the CoolStep threshold.

        :param threshold: CoolStep threshold (0 to 15). The CoolStep feature is enabled when the actual speed is below
        this threshold.
        """
        _require_int_range("threshold", threshold, 0, 15)
        self._set_axis_parameter(self.motor.AP.smartEnergyThresholdSpeed, threshold)
        self.coolstep_threshold = threshold
        self.logger.log(f"CoolStep threshold set to {threshold}", TMC2660LogLevel.INFO)

    def get_coolstep_current(self) -> int:
        """Get the current CoolStep current scaling."""
        return self._get_axis_parameter(self.motor.AP.smartEnergyActualCurrent, self.axis)


    # --------------- HELPER METHODS ---------------

    def get_actual_position(self):
        return self.eval_board.get_axis_parameter(
            self.motor.AP.ActualPosition, self.axis, signed=True
        )

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
        return self.vsense_fs.voltage

    def _convert_current_to_value(self, current_mA: float) -> int:
        try:
            valid_current = (
                not isinstance(current_mA, bool) and math.isfinite(current_mA)
            )
        except (TypeError, ValueError):
            valid_current = False
        if not valid_current:
            msg = "current_mA must be a finite number"
            self.logger.log(msg, TMC2660LogLevel.ERROR)
            raise ValueError(msg)

        vfs = self._get_vsense_full_scale_voltage()
        value = int((current_mA/1000 * 32 * self.rsense * 1.4142) / vfs) - 1         # 1.4142 = sqrt(2)
        if value < 0 or value > 31:
            msg = (
                f"Current {current_mA} mA is outside the representable range "
                "for the configured sense circuit."
            )
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
            return self.eval_board.get_axis_parameter(parameter, axis)
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
        """Stop motion, disable outputs, and close the interface fail-safely."""
        first_error = None
        for cleanup_step in (
            self.stop_motor,
            self.disable_motor,
            self.interface.close,
        ):
            try:
                cleanup_step()
            except Exception as exc:
                if first_error is None:
                    first_error = exc

        if first_error is None:
            try:
                self.logger.log("Motor driver cleaned up", TMC2660LogLevel.INFO)
            except Exception as exc:
                first_error = exc
        try:
            self.logger.remove_all_handlers()
        except Exception as exc:
            if first_error is None:
                first_error = exc
        if first_error is not None:
            raise first_error
