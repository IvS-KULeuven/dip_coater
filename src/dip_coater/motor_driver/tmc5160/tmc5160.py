"""
TMC5160 motor driver for the dip coater application.

Supports both real hardware via a Landungsbrücke + TMC5160-EVAL and dummy mode
for development and UI testing.
"""
import asyncio
import logging
import math
from enum import Enum

try:
    from pytrinamic.connections import ConnectionManager
    from pytrinamic.evalboards import TMC5160_eval
    from pytrinamic.modules import Landungsbruecke
    _PYTRINAMIC_AVAILABLE = True
except ModuleNotFoundError:
    ConnectionManager = None
    TMC5160_eval = None
    Landungsbruecke = None
    _PYTRINAMIC_AVAILABLE = False

from dip_coater.logging.tmc5160_logger import TMC5160LogLevel, TMC5160Logger
from dip_coater.motor_driver.motor_driver_interface import MotorDriver
from dip_coater.motor_driver.tmc5160.tmc5160_dummy import (
    DummyEvalBoard,
    DummyInterface,
    DummyLandungsbruecke,
)


class ChopperMode(Enum):
    SPREAD_CYCLE = (0, "SpreadCycle")
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


class MotorDriverTMC5160(MotorDriver):
    """TMC5160 motor driver.

    Supports both real hardware via PyTrinamic and dummy mode for development
    and UI testing.
    """

    # TMC5160 datasheet current scaling uses a fixed full-scale voltage of 325mV.
    V_FS_MV = 325
    CURRENT_SCALE_MAX = 31

    def __init__(
        self,
        app_state,
        interface_type="usb_tmcl",
        port="interactive",
        step_mode: int = 256,
        current_mA: int = 1200,
        current_standstill_mA: int = 150,
        invert_direction: bool = False,
        interpolation: bool = True,
        global_scaler: int = 0,
        rsense_mOhm: int = 50,
        chopper_mode: ChopperMode = ChopperMode.SPREAD_CYCLE,
        stallguard_enabled: bool = False,
        stallguard_threshold: int = 0,
        coolstep_enabled: bool = False,
        coolstep_threshold: int = 0,
        loglevel: TMC5160LogLevel = TMC5160LogLevel.ERROR,
        log_handlers: list = None,
        log_formatter: logging.Formatter = None,
    ):
        super().__init__(app_state.mechanical_setup)

        self.app_state = app_state

        self.logger = TMC5160Logger(
            loglevel=loglevel,
            handlers=log_handlers,
            formatter=log_formatter,
        )

        self.is_dummy = (
            interface_type == "dummy_tmcl"
            or app_state.config.USE_DUMMY_DRIVER
        )
        if self.is_dummy:
            self.logger.log("Using dummy TMC5160 driver backend", TMC5160LogLevel.INFO)
        elif not _PYTRINAMIC_AVAILABLE:
            msg = (
                "pytrinamic is required for the TMC5160 driver. "
                "Install it or use --use-dummy-driver."
            )
            self.logger.log(msg, TMC5160LogLevel.ERROR)
            raise ModuleNotFoundError(msg)

        # Set up the TMC5160 driver
        interface_txt = f"--interface {interface_type}" if interface_type else ""
        port_txt = f"--port {port}" if port else ""
        if self.is_dummy:
            self.dummy_values = {}
            self.register_values = {}
            self.interface = DummyInterface(self.dummy_values)
            self.lb = DummyLandungsbruecke()
            self.eval_board = DummyEvalBoard(self.dummy_values, self.register_values)
            self.motor = self.eval_board.motors[0]
        else:
            self.interface = ConnectionManager(f"{interface_txt} {port_txt}").connect()
            self.eval_board = TMC5160_eval(self.interface)
            self.lb = Landungsbruecke(self.interface)
            self.motor = self.eval_board.motors[0]

        self.mc = self.eval_board.ics[0]
        self.bank = 0
        self.axis = 0
        self.rsense = rsense_mOhm / 1000
        self.global_scaler_value = global_scaler

        # Driver state
        self.stallguard_threshold = stallguard_threshold
        self.coolstep_threshold = coolstep_threshold
        self.stallguard_enabled = stallguard_enabled
        self.coolstep_enabled = coolstep_enabled
        self.direction_inverted = invert_direction

        # Initialise dummy axis-parameter store
        if self.is_dummy:
            self.dummy_values.update({
                self.lb.GP.DriversEnable: False,
                self.motor.AP.PositionReachedFlag: True,
                self.motor.AP.MicrostepResolution: step_mode,
                self.motor.AP.MaxCurrent: self._convert_current_to_cs(current_mA),
                self.motor.AP.StandbyCurrent: self._convert_current_to_cs(current_standstill_mA),
                self.motor.AP.MaxVelocity: self.app_state.mechanical_setup.rps_to_stepss(1, step_mode),
                self.motor.AP.MaxAcceleration: self.app_state.mechanical_setup.rpss_to_stepss(1, step_mode),
                self.motor.AP.ActualPosition: 0,
                self.motor.AP.A1: 0,
                self.motor.AP.V1: 0,
                self.motor.AP.MaxDeceleration: 0,
                self.motor.AP.D1: 0,
                self.motor.AP.StartVelocity: 0,
                self.motor.AP.StopVelocity: 10,
                self.motor.AP.RampWaitTime: 0,
            })

        # Configure the motor
        self.disable_motor()
        self.set_global_scaler(global_scaler)
        self.set_chopper_mode(chopper_mode)
        self.set_microsteps(step_mode)
        self.set_interpolation(interpolation)
        self.invert_direction(invert_direction)
        self.set_current(current_mA)
        self.set_current_standstill(current_standstill_mA)
        self.set_stallguard_threshold(stallguard_threshold)
        self.set_coolstep_threshold(coolstep_threshold)
        self.set_stallguard_enabled(stallguard_enabled)
        self.set_coolstep_enabled(coolstep_enabled)

    # --------------- MOTOR CONTROL ---------------

    def enable_motor(self):
        self._set_global_parameter(self.lb.GP.DriversEnable, self.bank, 1)
        if self.is_motor_enabled() != 1:
            msg = "Failed to enable motor"
            self.logger.log(msg, TMC5160LogLevel.ERROR)
            raise ValueError(msg)
        self.logger.log("Motor enabled", TMC5160LogLevel.INFO)

    def disable_motor(self):
        self._set_global_parameter(self.lb.GP.DriversEnable, self.bank, 0)
        if self.is_motor_enabled() != 0:
            msg = "Failed to disable motor"
            self.logger.log(msg, TMC5160LogLevel.ERROR)
            raise ValueError(msg)
        self.logger.log("Motor disabled", TMC5160LogLevel.INFO)

    def is_motor_enabled(self):
        return self._get_global_parameter(self.lb.GP.DriversEnable, self.bank)

    def invert_direction(self, invert_direction: bool = False):
        self.direction_inverted = invert_direction
        self.logger.log(f"Direction inverted: {invert_direction}", TMC5160LogLevel.INFO)

    def rotate(self, revs: float, rps: float, rpss: float = None):
        revs = -revs if self.direction_inverted else revs
        self.set_speed_rps(rps)
        self.set_acceleration_rpss(rpss)
        steps = self.mechanical_setup.revs_to_steps(revs, self.microsteps)
        self.logger.log(f"Rotating {revs} revolutions, {steps} steps", TMC5160LogLevel.DEBUG)
        self.interface.move_by(0, int(steps))

    def move(self, distance_mm: float, speed_mm_s: float, acceleration_mm_s2: float = None):
        revs = self.mechanical_setup.mm_to_revs(distance_mm)
        rps = self.mechanical_setup.mm_s_to_rps(speed_mm_s)
        rpss = self.mechanical_setup.mm_s2_to_rpss(acceleration_mm_s2)
        self.rotate(revs, rps, rpss)

    def move_up(
        self,
        distance_mm: float,
        speed_mm_s: float,
        acceleration_mm_s2: float = None,
        *args,
        **kwargs,
    ):
        self.move(distance_mm, speed_mm_s, acceleration_mm_s2)

    def move_down(
        self,
        distance_mm: float,
        speed_mm_s: float,
        acceleration_mm_s2: float = None,
        *args,
        **kwargs,
    ):
        self.move(-distance_mm, speed_mm_s, acceleration_mm_s2)

    def stop_motor(self):
        self.motor.stop()
        self.logger.log("Motor stopped", TMC5160LogLevel.INFO)

    def get_current_position_mm(self):
        pos = self.get_actual_position()
        return self.mechanical_setup.steps_to_mm(pos, self.microsteps)

    def run_to_position(
        self,
        position_mm: float,
        speed_mm_s: float = None,
        acceleration_mm_s2: float = None,
    ):
        self.set_speed(speed_mm_s)
        self.set_acceleration(acceleration_mm_s2)
        steps = self.mechanical_setup.mm_to_steps(position_mm, self.microsteps)
        self.motor.move_to(steps)

    def is_target_reached(self):
        return self._get_axis_parameter(self.motor.AP.PositionReachedFlag, self.axis)

    def wait_for_motor_done(self):
        while not self.is_target_reached():
            pass
        self.logger.log("Motor done", TMC5160LogLevel.INFO)

    async def wait_for_motor_done_async(self):
        while not self.is_target_reached():
            await asyncio.sleep(0.1)
        self.logger.log("Motor done", TMC5160LogLevel.INFO)

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
            self.logger.log(msg, TMC5160LogLevel.ERROR)
            raise ValueError(msg)
        self.logger.log(f"Microsteps set to {microsteps}", TMC5160LogLevel.INFO)

    def get_microsteps(self) -> int:
        return self._get_axis_parameter(self.motor.AP.MicrostepResolution, self.axis)

    def set_current(self, current_mA: float):
        cs = self._convert_current_to_cs(current_mA)
        self._set_axis_parameter(self.motor.AP.MaxCurrent, cs)
        self._write_register_field(self.mc.FIELD.IRUN, cs)

        verify_cs = self.get_current()
        if cs != verify_cs:
            msg = f"Set max current CS={cs} does not match read back value {verify_cs}"
            self.logger.log(msg, TMC5160LogLevel.ERROR)
            raise ValueError(msg)
        actual_mA = self._convert_cs_to_current(verify_cs)
        self.logger.log(
            f"Max current set to {current_mA:.1f} mA, CS: {cs}, actual: {actual_mA:.1f} mA",
            TMC5160LogLevel.INFO,
        )

    def get_current(self):
        return self._get_axis_parameter(self.motor.AP.MaxCurrent, self.axis)

    def set_current_standstill(self, current_mA: float):
        cs = self._convert_current_to_cs(current_mA)
        self._set_axis_parameter(self.motor.AP.StandbyCurrent, cs)
        self._write_register_field(self.mc.FIELD.IHOLD, cs)

        if cs == 0:
            self._set_axis_parameter(self.motor.AP.FreewheelingMode, 1)
        else:
            self._set_axis_parameter(self.motor.AP.FreewheelingMode, 0)

        verify_cs = self.get_current_standstill()
        if cs != verify_cs:
            msg = f"Set standby current CS={cs} does not match read back value {verify_cs}"
            self.logger.log(msg, TMC5160LogLevel.ERROR)
            raise ValueError(msg)
        actual_mA = self._convert_cs_to_current(verify_cs)
        self.logger.log(
            f"Standstill current set to {current_mA:.1f} mA, CS: {cs}, actual: {actual_mA:.1f} mA",
            TMC5160LogLevel.INFO,
        )

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
            self.logger.log(msg, TMC5160LogLevel.ERROR)
            raise ValueError(msg)
        self.logger.log(
            f"Max velocity set to {rps:.2f} rps, value: {verify_speed:.2f} rps",
            TMC5160LogLevel.INFO,
        )

    def get_speed_rps(self) -> float:
        steps_per_second = self._get_axis_parameter(self.motor.AP.MaxVelocity, self.axis)
        return self.mechanical_setup.stepss_to_rps(steps_per_second, self.microsteps)

    def set_acceleration_rpss(self, rpss: float):
        if rpss is None or rpss == 0:
            return
        steps_per_second2 = self.mechanical_setup.rpss_to_stepss(rpss, self.microsteps)
        self._set_axis_parameter(self.motor.AP.MaxAcceleration, int(steps_per_second2))

        verify_accel = self.get_acceleration_rpss()
        if not math.isclose(rpss, verify_accel, rel_tol=1e-3, abs_tol=1e-3):
            msg = f"Set max acceleration {rpss} does not match read back value {verify_accel}"
            self.logger.log(msg, TMC5160LogLevel.ERROR)
            raise ValueError(msg)
        self.logger.log(
            f"Max acceleration set to {rpss:.2f} rpss, value: {verify_accel:.2f} rpss",
            TMC5160LogLevel.INFO,
        )

    def get_acceleration_rpss(self) -> float:
        steps_per_second2 = self._get_axis_parameter(self.motor.AP.MaxAcceleration, self.axis)
        return self.mechanical_setup.stepss_to_rpss(steps_per_second2, self.microsteps)

    # --------------- S-CURVE RAMP CONFIGURATION ---------------

    def set_ramp_parameters(
        self,
        a1: int,
        v1: int,
        amax: int,
        vmax: int,
        dmax: int,
        d1: int,
        vstart: int = 0,
        vstop: int = 10,
        tzerowait: int = 0,
    ):
        """Set all S-curve ramp parameters at once.

        Uses direct register writes, matching the PyTrinamic demo pattern:
            eval_board.write_register(mc.REG.A1, value)

        Parameters are in TMC5160 internal units. For velocity:
            v_internal = v_Hz * 2^24 / fCLK  (fCLK typically 12 MHz)
        For acceleration:
            a_internal = a_Hz_per_s * 2^41 / fCLK^2
        """
        self._write_register(self.mc.REG.VSTART, vstart)
        self._write_register(self.mc.REG.A1, a1)
        self._write_register(self.mc.REG.V1, v1)
        self._write_register(self.mc.REG.AMAX, amax)
        self._write_register(self.mc.REG.VMAX, vmax)
        self._write_register(self.mc.REG.DMAX, dmax)
        self._write_register(self.mc.REG.D1, d1)
        self._write_register(self.mc.REG.VSTOP, max(vstop, 1))
        self._write_register(self.mc.REG.TZEROWAIT, tzerowait)
        self.logger.log(
            f"Ramp parameters set: A1={a1}, V1={v1}, AMAX={amax}, VMAX={vmax}, "
            f"DMAX={dmax}, D1={d1}, VSTART={vstart}, VSTOP={vstop}",
            TMC5160LogLevel.INFO,
        )

    def set_a1(self, value: int):
        self._write_register(self.mc.REG.A1, value)
        self.logger.log(f"A1 set to {value}", TMC5160LogLevel.INFO)

    def get_a1(self) -> int:
        return self._read_register(self.mc.REG.A1)

    def set_v1(self, value: int):
        self._write_register(self.mc.REG.V1, value)
        self.logger.log(f"V1 set to {value}", TMC5160LogLevel.INFO)

    def get_v1(self) -> int:
        return self._read_register(self.mc.REG.V1)

    def set_amax(self, value: int):
        self._write_register(self.mc.REG.AMAX, value)
        self.logger.log(f"AMAX set to {value}", TMC5160LogLevel.INFO)

    def get_amax(self) -> int:
        return self._read_register(self.mc.REG.AMAX)

    def set_vmax(self, value: int):
        self._write_register(self.mc.REG.VMAX, value)
        self.logger.log(f"VMAX set to {value}", TMC5160LogLevel.INFO)

    def get_vmax(self) -> int:
        return self._read_register(self.mc.REG.VMAX)

    def set_dmax(self, value: int):
        self._write_register(self.mc.REG.DMAX, value)
        self.logger.log(f"DMAX set to {value}", TMC5160LogLevel.INFO)

    def get_dmax(self) -> int:
        return self._read_register(self.mc.REG.DMAX)

    def set_d1(self, value: int):
        self._write_register(self.mc.REG.D1, value)
        self.logger.log(f"D1 set to {value}", TMC5160LogLevel.INFO)

    def get_d1(self) -> int:
        return self._read_register(self.mc.REG.D1)

    def set_vstart(self, value: int):
        self._write_register(self.mc.REG.VSTART, value)
        self.logger.log(f"VSTART set to {value}", TMC5160LogLevel.INFO)

    def get_vstart(self) -> int:
        return self._read_register(self.mc.REG.VSTART)

    def set_vstop(self, value: int):
        if value < 1:
            msg = "VSTOP must be >= 1 (recommended >= 10)"
            self.logger.log(msg, TMC5160LogLevel.WARNING)
            value = 1
        self._write_register(self.mc.REG.VSTOP, value)
        self.logger.log(f"VSTOP set to {value}", TMC5160LogLevel.INFO)

    def get_vstop(self) -> int:
        return self._read_register(self.mc.REG.VSTOP)

    def set_tzerowait(self, value: int):
        self._write_register(self.mc.REG.TZEROWAIT, value)
        self.logger.log(f"TZEROWAIT set to {value}", TMC5160LogLevel.INFO)

    def get_tzerowait(self) -> int:
        return self._read_register(self.mc.REG.TZEROWAIT)

    # --------------- GLOBAL SCALER / CURRENT SCALING ---------------

    def set_global_scaler(self, value: int):
        """Set GLOBAL_SCALER register.

        Valid values are 0-255. Per the datasheet, 0 means full scale (256/256).
        """
        if value < 0 or value > 255:
            msg = f"GLOBAL_SCALER must be between 0 and 255, got {value}"
            self.logger.log(msg, TMC5160LogLevel.ERROR)
            raise ValueError(msg)
        self.global_scaler_value = value
        self._write_register(self.mc.REG.GLOBAL_SCALER, value)
        self.logger.log(f"GLOBAL_SCALER set to {value}", TMC5160LogLevel.INFO)

    def get_global_scaler(self) -> int:
        return self._read_register(self.mc.REG.GLOBAL_SCALER)

    # --------------- ADVANCED MOTOR CONFIGURATION ---------------

    # Chopper configuration

    def set_chopper_mode(self, mode: ChopperMode):
        if mode not in [ChopperMode.SPREAD_CYCLE, ChopperMode.CONSTANT_TOFF]:
            msg = f"Invalid chopper mode: {mode}. Must be 0 or 1."
            self.logger.log(msg, TMC5160LogLevel.ERROR)
            raise ValueError(msg)
        self._set_axis_parameter(self.motor.AP.ConstantTOffMode, mode.value)
        self.logger.log(f"Chopper mode set to {mode.label}", TMC5160LogLevel.INFO)

    def configure_chopper(
        self, hysteresis_start: int, hysteresis_end: int, blank_time: int, off_time: int
    ):
        self._set_axis_parameter(self.motor.AP.ChopperHysteresisStart, hysteresis_start)
        self._set_axis_parameter(self.motor.AP.ChopperHysteresisEnd, hysteresis_end)
        self._set_axis_parameter(self.motor.AP.ChopperBlankTime, blank_time)
        self._set_axis_parameter(self.motor.AP.TOff, off_time)
        self.logger.log("Chopper configured", TMC5160LogLevel.INFO)

    # Interpolation

    def set_interpolation(self, enable: bool):
        self._write_register_field(self.mc.FIELD.INTPOL, 1 if enable else 0)
        self.logger.log(
            f"Interpolation {'enabled' if enable else 'disabled'}",
            TMC5160LogLevel.INFO,
        )

    # StallGuard2

    def set_stallguard_enabled(self, enable: bool):
        self.stallguard_enabled = enable
        self._apply_stallguard_threshold()
        self.logger.log(
            f"StallGuard2 {'enabled' if enable else 'disabled'}",
            TMC5160LogLevel.INFO,
        )

    def set_stallguard_filter_enabled(self, enable: bool):
        self._set_axis_parameter(self.motor.AP.SG2FilterEnable, 1 if enable else 0)
        self.logger.log(
            f"StallGuard2 filter {'enabled' if enable else 'disabled'}",
            TMC5160LogLevel.INFO,
        )

    def set_stallguard_threshold(self, threshold: int):
        self.stallguard_threshold = threshold
        self._apply_stallguard_threshold()
        self.logger.log(f"StallGuard2 threshold set to {threshold}", TMC5160LogLevel.INFO)

    def get_stallguard_result(self) -> int:
        return self._get_axis_parameter(self.motor.AP.LoadValue, self.axis)

    # CoolStep

    def configure_coolstep(
        self,
        min_current: int,
        current_down_step: int,
        current_up_step: int,
        hysteresis: int,
        threshold_speed: int,
    ):
        self._set_axis_parameter(self.motor.AP.SEIMIN, min_current)
        self._set_axis_parameter(self.motor.AP.SECDS, current_down_step)
        self._set_axis_parameter(self.motor.AP.SECUS, current_up_step)
        self._set_axis_parameter(self.motor.AP.smartEnergyHysteresis, hysteresis)
        self._set_axis_parameter(self.motor.AP.smartEnergyThresholdSpeed, threshold_speed)
        self.logger.log("CoolStep configured", TMC5160LogLevel.INFO)

    def set_coolstep_enabled(self, enable: bool):
        self.coolstep_enabled = enable
        self._apply_coolstep_threshold()
        self.logger.log(
            f"CoolStep {'enabled' if enable else 'disabled'}",
            TMC5160LogLevel.INFO,
        )

    def set_coolstep_threshold(self, threshold: int):
        self.coolstep_threshold = threshold
        self._apply_coolstep_threshold()
        self.logger.log(f"CoolStep threshold set to {threshold}", TMC5160LogLevel.INFO)

    def get_coolstep_current(self) -> int:
        return self._get_axis_parameter(self.motor.AP.smartEnergyActualCurrent, self.axis)

    # --------------- STATUS / DIAGNOSTICS ---------------

    def read_ramp_status(self) -> int:
        return self._read_register(self.mc.REG.RAMP_STAT)

    def read_drv_status(self) -> int:
        return self._read_register(self.mc.REG.DRV_STATUS)

    # --------------- HELPER METHODS ---------------

    def get_actual_position(self):
        return self.eval_board.get_axis_parameter(self.motor.AP.ActualPosition, self.axis)

    def verify_microsteps(self, microsteps: int) -> int:
        """Verify microsteps are valid (1, 2, 4, ..., 256). Returns the microstep index."""
        if microsteps in [1, 2, 4, 8, 16, 32, 64, 128, 256]:
            return int.bit_length(microsteps) - 1
        else:
            msg = f"Invalid number of microsteps: {microsteps}. Must be a power of 2 between 1 and 256."
            self.logger.log(msg, TMC5160LogLevel.ERROR)
            raise ValueError(msg)

    def _effective_global_scaler(self) -> int:
        """Return effective global scaler (0 is treated as 256)."""
        return 256 if self.global_scaler_value == 0 else self.global_scaler_value

    def _convert_current_to_cs(self, current_mA: float) -> int:
        """Convert desired RMS current in mA to the IRUN/IHOLD CS value.
        Formula taken from TMCL-IDE, Current settings, Sense Resistors tah
        """
        if current_mA < 0:
            msg = f"Invalid current value: {current_mA}. Must be non-negative."
            self.logger.log(msg, TMC5160LogLevel.ERROR)
            raise ValueError(msg)

        gs = self._effective_global_scaler()
        current_a = current_mA / 1000
        cs = round(
            (current_a * 32 * 256 * self.rsense * math.sqrt(2))
            / (gs * (self.V_FS_MV / 1000))
            - 1
        )
        cs = max(cs, 0) # Can be -1 if current setting is low

        if not 0 <= cs <= self.CURRENT_SCALE_MAX:
            max_current_mA = self._convert_cs_to_current(self.CURRENT_SCALE_MAX)
            msg = (
                f"Requested current {current_mA:.1f} mA is out of range for "
                f"GLOBAL_SCALER={self.global_scaler_value} and RSENSE={self.rsense:.3f} ohm. "
                f"Maximum is {max_current_mA:.1f} mA."
                f"Calculated cs is {cs}."
            )
            self.logger.log(msg, TMC5160LogLevel.ERROR)
            raise ValueError(msg)
        return cs

    def _convert_cs_to_current(self, cs: int) -> float:
        """Convert IRUN/IHOLD CS value (0-31) to RMS current in mA."""
        if not 0 <= cs <= self.CURRENT_SCALE_MAX:
            msg = f"Invalid current scale value: {cs}. Must be between 0 and 31."
            self.logger.log(msg, TMC5160LogLevel.ERROR)
            raise ValueError(msg)

        gs = self._effective_global_scaler()
        current_a = (
            (gs / 256)
            * ((cs + 1) / 32)
            * ((self.V_FS_MV / 1000) / self.rsense)
            * (1 / math.sqrt(2))
        )
        return current_a * 1000

    def _apply_stallguard_threshold(self):
        self._set_axis_parameter(
            self.motor.AP.SG2Threshold,
            self.stallguard_threshold if self.stallguard_enabled else 0,
        )

    def _apply_coolstep_threshold(self):
        self._set_axis_parameter(
            self.motor.AP.smartEnergyThresholdSpeed,
            self.coolstep_threshold if self.coolstep_enabled else 0,
        )

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

    def _write_register(self, register_address, value):
        if self.is_dummy:
            self.register_values[register_address] = value
        else:
            self.eval_board.write_register(register_address, value)

    def _write_register_field(self, field, value):
        self.eval_board.write_register_field(field, value)

    def _read_register(self, register_address, signed=False):
        if self.is_dummy:
            return self.register_values.get(register_address, 0)
        return self.eval_board.read_register(register_address, signed)

    # --------------- LOGGING ---------------

    def set_loglevel(self, loglevel: TMC5160LogLevel):
        self.logger.set_loglevel(loglevel)
        self.logger.log(f"Log level set to {loglevel.name}", TMC5160LogLevel.INFO)

    def add_log_handler(self, handler):
        self.logger.add_handler(handler)

    def remove_log_handler(self, handler):
        self.logger.remove_handler(handler)

    def cleanup(self):
        self.disable_motor()
        self.interface.close()
        self.logger.log("TMC5160 driver cleaned up", TMC5160LogLevel.INFO)
    
    def register_dump(self):
        print("GCONF:         0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.GCONF)))
        print("GSTAT:         0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.GSTAT)))
        print("SLAVECONF:     0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.SLAVECONF)))
        print("IOIN / OUTPUT: 0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.IOIN_OUTPUT)))
        print("X_COMPARE:     0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.X_COMPARE)))
        print("OTP_PROG:      0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.OTP_PROG)))
        print("OTP_READ:      0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.OTP_READ)))
        print("FACTORY_CONF:  0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.FACTORY_CONF)))
        print("SHORT_CONF:    0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.SHORT_CONF)))
        print("DRV_CONF:      0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.DRV_CONF)))
        print("GLOBAL_SCALER: 0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.GLOBAL_SCALER)))
        print("OFFSET_READ:   0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.OFFSET_READ)))
        print("IHOLD_IRUN:    0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.IHOLD_IRUN)))
        print("TPOWERDOWN:    0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.TPOWERDOWN)))
        print("TSTEP:         0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.TSTEP)))
        print("TPWMTHRS:      0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.TPWMTHRS)))
        print("TCOOLTHRS:     0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.TCOOLTHRS)))
        print("THIGH:         0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.THIGH)))
        print("RAMPMODE:      0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.RAMPMODE)))
        print("XACTUAL:       0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.XACTUAL)))
        print("VACTUAL:       0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.VACTUAL)))
        print("VSTART:        0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.VSTART)))
        print("A1:            0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.A1)))
        print("V1:            0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.V1)))
        print("AMAX:          0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.AMAX)))
        print("VMAX:          0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.VMAX)))
        print("DMAX:          0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.DMAX)))
        print("D1:            0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.D1)))
        print("VSTOP:         0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.VSTOP)))
        print("TZEROWAIT:     0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.TZEROWAIT)))
        print("XTARGET:       0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.XTARGET)))
        print("VDCMIN:        0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.VDCMIN)))
        print("SW_MODE:       0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.SW_MODE)))
        print("RAMP_STAT:     0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.RAMP_STAT)))
        print("XLATCH:        0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.XLATCH)))
        print("ENCMODE:       0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.ENCMODE)))
        print("X_ENC:         0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.X_ENC)))
        print("ENC_CONST:     0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.ENC_CONST)))
        print("ENC_STATUS:    0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.ENC_STATUS)))
        print("ENC_LATCH:     0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.ENC_LATCH)))
        print("ENC_DEVIATION: 0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.ENC_DEVIATION)))
        print("MSLUT0:        0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.MSLUT0)))
        print("MSLUT1:        0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.MSLUT1)))
        print("MSLUT2:        0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.MSLUT2)))
        print("MSLUT3:        0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.MSLUT3)))
        print("MSLUT4:        0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.MSLUT4)))
        print("MSLUT5:        0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.MSLUT5)))
        print("MSLUT6:        0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.MSLUT6)))
        print("MSLUT7:        0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.MSLUT7)))
        print("MSLUTSEL:      0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.MSLUTSEL)))
        print("MSLUTSTART:    0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.MSLUTSTART)))
        print("MSCNT:         0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.MSCNT)))
        print("MSCURACT:      0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.MSCURACT)))
        print("CHOPCONF:      0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.CHOPCONF)))
        print("COOLCONF:      0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.COOLCONF)))
        print("DCCTRL:        0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.DCCTRL)))
        print("DRV_STATUS:    0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.DRV_STATUS)))
        print("PWM_CONF:      0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.PWM_CONF)))
        print("PWM_SCALE:     0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.PWM_SCALE)))
        print("PWM_AUTO:      0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.PWM_AUTO)))
        print("LOST_STEPS:    0x{0:08X}".format(self.eval_board.read_register(self.mc.REG.LOST_STEPS)))
