"""
Move a motor back and forth using velocity and position mode of the TMC2660.
"""
import logging
import asyncio
from enum import Enum
from pytrinamic.connections import ConnectionManager
from pytrinamic.evalboards import TMC2660_eval
from pytrinamic.modules import Landungsbruecke

from dip_coater.motor.motor_driver_interface import MotorDriver


class TMC2660LogLevel(Enum):
    NONE = 0
    ERROR = 1
    WARNING = 2
    INFO = 3
    DEBUG = 4


class VSenseFullScale:
    """
    VSense full scale values for the TMC2660.
    """
    VSENSE_FULL_SCALE_305mV = 0
    VSENSE_FULL_SCALE_165mV = 1


class DriveMode:
    # High-precision load measurement using the back EMF on the coils
    STALL_GUARD = 0
    # Load-adaptive current control which reduces energy consumption by as much as 75%
    COOL_STEP = 1
    # High-precision chopper algorithm available as an alternative to the traditional constant
    # off-time algorithm
    SPREAD_CYCLE = 2
    # High-precision chopper algorithm available as an alternative to the traditional constant
    # off-time algorithm
    MICRO_PLYER = 3


class MotorDriverTMC2660(MotorDriver):
    def __init__(self, app_state, interface_type="usb_tmcl", port="interactive",
                 step_mode: int = 8, current_mA: int = 2000, current_standstill_mA: int = 250,
                 loglevel: TMC2660LogLevel = TMC2660LogLevel.ERROR, log_handlers: list = None,
                 log_formatter: logging.Formatter = None):
        super().__init__(app_state.mechanical_setup)

        self.app_state = app_state

        # Set up logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(loglevel.value * 10)  # Convert our enum to Python logging levels
        if log_handlers:
            for handler in log_handlers:
                if log_formatter:
                    handler.setFormatter(log_formatter)
                self.logger.addHandler(handler)
        else:
            console_handler = logging.StreamHandler()
            if log_formatter:
                console_handler.setFormatter(log_formatter)
            self.logger.addHandler(console_handler)

        interface_txt = f"--interface {interface_type}" if interface_type else ""
        port_txt = f"--port {port}" if port else ""
        self.interface = ConnectionManager(f"{interface_txt} {port_txt}").connect()
        self.eval_board = TMC2660_eval(self.interface)
        self.lb = Landungsbruecke(self.interface)
        self.bank = 0

        self.axis = 0
        self.motor = self.eval_board.motors[0]
        self.disable_motor()
        self.set_microsteps(step_mode)
        self.vsense_fs = VSenseFullScale.VSENSE_FULL_SCALE_305mV
        self.rsense = 100       # Sense resistor value in mOhm

        self.direction_inverted = False

        self.set_current(current_mA)
        self.set_current_standstill(current_standstill_mA)

    # --------------- MOTOR CONTROL ---------------

    def enable_motor(self):
        self.interface.set_global_parameter(self.lb.GP.DriversEnable, self.bank, 1)
        if self.is_motor_enabled() != 1:
            msg = "Failed to enable motor"
            self.logger.error(msg)
            raise ValueError(msg)
        self.logger.info("Motor enabled")

    def disable_motor(self):
        self.interface.set_global_parameter(self.lb.GP.DriversEnable, self.bank, 0)
        if self.is_motor_enabled() != 0:
            msg = "Failed to disable motor"
            self.logger.error(msg)
            raise ValueError(msg)
        self.logger.info("Motor disabled")

    def is_motor_enabled(self):
        return self.interface.get_global_parameter(self.lb.GP.DriversEnable, self.bank)

    def invert_direction(self, invert_direction: bool = False):
        self.direction_inverted = invert_direction
        self.logger.info(f"Direction inverted: {invert_direction}")

    def rotate(self, revs: float, rps: float, rpss: float = None):
        revs = -revs if self.direction_inverted else revs
        self.set_speed_rps(rps)
        self.set_acceleration_rpss(rpss)
        steps = self.mechanical_setup.revs_to_steps(revs, self.microsteps)
        self.logger.debug(f"Rotating {revs} revolutions, {steps} steps")
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
        self.logger.info("Motor stopped")

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
        return self.motor.get_axis_parameter(self.motor.AP.PositionReachedFlag, self.axis)

    def wait_for_motor_done(self):
        while not self.is_target_reached():
            pass
        self.logger.info("Motor done")

    async def wait_for_motor_done_async(self):
        while not self.is_target_reached():
            await asyncio.sleep(0.1)
        self.logger.info("Motor done")
    
    def is_homing_found(self):
        return False

    # --------------- MOTOR CONFIGURATION ---------------

    def set_microsteps(self, microsteps: int):
        self.verify_microsteps(microsteps)
        self.microsteps = microsteps
        self.motor.set_axis_parameter(self.motor.AP.MicrostepResolution, microsteps)

        verify_microsteps = self.get_microsteps()
        if self.microsteps != verify_microsteps:
            msg = f"Set microsteps {microsteps} does not match read back value {verify_microsteps}"
            self.logger.error(msg)
            raise ValueError(msg)
        self.logger.info(f"Microsteps set to {microsteps}")

    def get_microsteps(self) -> int:
        mstep = self.motor.get_axis_parameter(self.motor.AP.MicrostepResolution, self.axis)
        return self.microstep_idx_to_steps(mstep)

    def set_vsense_full_scale(self, vsense_full_scale: int):
        if vsense_full_scale not in [VSenseFullScale.VSENSE_FULL_SCALE_305mV, VSenseFullScale.VSENSE_FULL_SCALE_165mV]:
            msg = f"Invalid VSense full scale value: {vsense_full_scale}. Must be 0 or 1."
            self.logger.error(msg)
            raise ValueError(msg)
        self.vsense_fs = vsense_full_scale
        self.motor.set_axis_parameter(self.motor.AP.VSense, vsense_full_scale)

    def get_vsense_full_scale(self) -> int:
        return self.motor.get_axis_parameter(self.motor.AP.VSense, self.axis)

    def set_current(self, current_mA: float):
        current_value = self._convert_current_to_value(current_mA)
        actual_current_mA = self._convert_value_to_current(current_value)
        self.motor.set_axis_parameter(self.motor.AP.MaxCurrent, current_value)

        verify_current = self.get_current()
        if current_value != verify_current:
            msg = f"Set max current {current_value} does not match read back value {verify_current}"
            self.logger.error(msg)
            raise ValueError(msg)
        self.logger.info(f"Max current set to {current_mA:.1f} mA, value: {current_value}, actual: "
                         f"{actual_current_mA:.1f} mA")

    def get_current(self):
        return self.motor.get_axis_parameter(self.motor.AP.MaxCurrent, self.axis)

    def set_current_standstill(self, current_mA: float):
        current_value = self._convert_current_to_value(current_mA)
        actual_current_mA = self._convert_value_to_current(current_value)
        self.motor.set_axis_parameter(self.motor.AP.StandbyCurrent, current_value)

        verify_current = self.get_current_standstill()
        if current_value != verify_current:
            msg = f"Set standby current {current_value} does not match read back value {verify_current}"
            self.logger.error(msg)
            raise ValueError(msg)
        self.logger.info(f"Standstill current set to {current_mA:.1f} mA, value: {current_value}, actual: "
                         f"{actual_current_mA:.1f} mA")
        
    def get_current_standstill(self):
        return self.motor.get_axis_parameter(self.motor.AP.StandbyCurrent, self.axis)

    def set_speed_rps(self, rps: float):
        if rps is None:
            return
        steps_per_second = self.mechanical_setup.rps_to_stepss(rps, self.microsteps)
        self.motor.set_axis_parameter(self.motor.AP.MaxVelocity, int(steps_per_second))

        verify_speed = self.get_speed_rps()
        if rps != verify_speed:
            msg = f"Set max velocity {rps} does not match read back value {verify_speed}"
            self.logger.error(msg)
            raise ValueError(msg)
        self.logger.info(f"Max velocity set to {rps:.2f} rps, value: {verify_speed:.2f} rps")

    def get_speed_rps(self) -> float:
        steps_per_second = self.motor.get_axis_parameter(self.motor.AP.MaxVelocity, self.axis)
        return self.mechanical_setup.stepss_to_rps(steps_per_second, self.microsteps)

    def set_acceleration_rpss(self, rpss: float):
        if rpss is None or rpss == 0:
            return
        steps_per_second2 = self.mechanical_setup.rpss_to_stepss(rpss, self.microsteps)
        self.motor.set_axis_parameter(self.motor.AP.MaxAcceleration, int(steps_per_second2))

        verify_acceleration = self.get_acceleration_rpss()
        if rpss != verify_acceleration:
            msg = f"Set max acceleration {rpss} does not match read back value {verify_acceleration}"
            self.logger.error(msg)
            raise ValueError(msg)
        self.logger.info(f"Max acceleration set to {rpss:.2f} rpss, value: {verify_acceleration:.2f} rpss")

    def get_acceleration_rpss(self) -> float:
        steps_per_second2 = self.motor.get_axis_parameter(self.motor.AP.MaxAcceleration, self.axis)
        return self.mechanical_setup.stepss_to_rpss(steps_per_second2, self.microsteps)

    # --------------- HELPER METHODS ---------------

    def get_actual_position(self):
        return self.eval_board.get_axis_parameter(self.motor.AP.ActualPosition, self.axis)

    @staticmethod
    def microstep_idx_to_steps(idx: int) -> int:
        """Convert microstep index (0, 1, 2, 3...) to actual number of microsteps (1, 2, 4, 8...)."""
        if 0 <= idx <= 8:
            return 2 ** idx
        else:
            raise ValueError(f"Invalid microstep index: {idx}. Must be between 0 and 8.")

    @staticmethod
    def verify_microsteps(microsteps: int) -> int:
        """ Verify that the microsteps are valid (1, 2, 4, 8...). If so, return the microstep index (0, 1, 2, 3...)."""
        if microsteps in [1, 2, 4, 8, 16, 32, 64, 128, 256]:
            return int.bit_length(microsteps) - 1
        else:
            raise ValueError(f"Invalid number of microsteps: {microsteps}. Must be a power of 2 between 1 and 256.")

    def _get_vsense_full_scale_voltage(self) -> int:
        return 305 if self.vsense_fs == VSenseFullScale.VSENSE_FULL_SCALE_305mV else 165

    def _convert_current_to_value(self, current_mA: float) -> int:
        vfs = self._get_vsense_full_scale_voltage()
        value = int((current_mA/1000 * 32 * self.rsense * 1.4142) / vfs) - 1         # 1.4142 = sqrt(2)
        if value < 0 or value > 31:
            raise ValueError(f"Invalid current value: {value}. Must be between 0 and 31.")
        return value

    def _convert_value_to_current(self, value: int) -> float:
        if value < 0 or value > 31:
            raise ValueError(f"Invalid current value: {value}. Must be between 0 and 31.")
        vfs = self._get_vsense_full_scale_voltage()
        return (value + 1) * vfs / (32 * self.rsense * 1.4142) * 1000         # 1.4142 = sqrt(2)

    def set_loglevel(self, loglevel: TMC2660LogLevel):
        self.logger.setLevel(loglevel.value * 10)
        self.logger.info(f"Log level set to {loglevel.name}")

    def cleanup(self):
        self.disable_motor()
        self.interface.close()
