"""
Move a motor back and forth using velocity and position mode of the TMC2660.
"""
import logging
from pytrinamic.connections import ConnectionManager
from pytrinamic.evalboards import TMC2660_eval
from pytrinamic.modules import Landungsbruecke

from TMC_2209._TMC_2209_logger import Loglevel

from dip_coater.motor.motor_driver_interface import MotorDriver


class TMC2660_MotorDriver(MotorDriver):
    def __init__(self, app_state, interface_type="usb_tmcl", port="interactive",
                 loglevel: Loglevel = Loglevel.ERROR, log_handlers: list = None,
                 log_formatter: logging.Formatter = None):
        super().__init__(app_state.mechanical_setup)

        self.app_state = app_state
        interface_txt = f"--interface {interface_type}" if interface_type else ""
        port_txt = f"--port {port}" if port else ""
        self.interface = ConnectionManager(f"{interface_txt} {port_txt}").connect()
        self.eval_board = TMC2660_eval(self.interface)
        self.lb = Landungsbruecke(self.interface)
        self.motor = self.eval_board.motors[0]
        self.bank = 0
        self.microsteps = self.get_microsteps()

    # --------------- MOTOR CONTROL ---------------

    def enable_motor(self):
        self.interface.set_global_parameter(self.lb.GP.DriversEnable, self.bank, 1)

    def disable_motor(self):
        self.interface.set_global_parameter(self.lb.GP.DriversEnable, self.bank, 0)

    def move_up(self, distance_mm: float, speed_mm_s: float, acceleration_mm_s2: float = 0):
        self.set_speed(speed_mm_s)
        self.set_acceleration(acceleration_mm_s2)
        steps = int(distance_mm * self.microsteps * FULL_STEPS / TRANS_PER_REV)
        self.motor.move_to(self.motor.actual_position + steps)

    def move_down(self, distance_mm: float, speed_mm_s: float, acceleration_mm_s2: float = 0):
        self.move_up(-distance_mm, speed_mm_s, acceleration_mm_s2)

    def stop_motor(self):
        self.motor.stop()

    def get_current_position(self):
        return self.motor.actual_position * TRANS_PER_REV / (self.microsteps * FULL_STEPS)

    def run_to_position(self, position_mm: float, speed_mm_s: float = None, acceleration_mm_s2: float = None):
        self.set_speed(speed_mm_s)
        self.set_acceleration(acceleration_mm_s2)
        steps = int(position_mm * self.microsteps * FULL_STEPS / TRANS_PER_REV)
        self.motor.move_to(steps)

    # --------------- MOTOR CONFIGURATION ---------------

    def set_microsteps(self, microsteps: int):
        _step_mode = self.microstep_steps_to_idx(microsteps)
        self.motor.set_axis_parameter(self.motor.AP.MicrostepResolution, _step_mode)

    def get_microsteps(self) -> int:
        mstep = self.eval_board.get_axis_parameter(self.motor.AP.MicrostepResolution, 0)
        return self.microstep_idx_to_steps(mstep)

    def set_max_current(self, current_mA: float):
        self.motor.set_axis_parameter(self.motor.AP.MaxCurrent, current_mA)

    def set_standby_current(self, current_mA: float):
        self.motor.set_axis_parameter(self.motor.AP.StandbyCurrent, current_mA)

    def set_speed(self, speed_mm_s: float):
        if speed_mm_s is not None:
            rps = self.mechanical_setup.mm_s_to_rps(speed_mm_s)
            steps_per_second = rps * self.mechanical_setup.steps_per_revolution * self.get_microsteps()
            self.motor.set_axis_parameter(self.motor.AP.MaxVelocity, int(steps_per_second))

    def set_acceleration(self, acceleration_mm_s2: float):
        if acceleration_mm_s2 is not None:
            self.motor.set_axis_parameter(self.motor.AP.MaxAcceleration, int(acceleration_mm_s2 * 100)) # TODO: convert value

    # --------------- HELPER METHODS ---------------

    @staticmethod
    def microstep_idx_to_steps(idx: int) -> int:
        """Convert microstep index to actual number of microsteps."""
        if 0 <= idx <= 8:
            return 2 ** idx
        else:
            raise ValueError(f"Invalid microstep index: {idx}. Must be between 0 and 8.")

    @staticmethod
    def microstep_steps_to_idx(steps: int) -> int:
        """Convert actual number of microsteps to microstep index."""
        if steps in [1, 2, 4, 8, 16, 32, 64, 128, 256]:
            return int.bit_length(steps) - 1
        else:
            raise ValueError(f"Invalid number of microsteps: {steps}. Must be a power of 2 between 1 and 256.")

    def cleanup(self):
        self.disable_motor()
        self.interface.close()
