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
                 step_mode: int = 8, current_mA: int = 2000, current_standstill_mA: int = 2000,
                 loglevel: Loglevel = Loglevel.ERROR, log_handlers: list = None,
                 log_formatter: logging.Formatter = None):
        super().__init__(app_state.mechanical_setup)

        self.app_state = app_state
        interface_txt = f"--interface {interface_type}" if interface_type else ""
        port_txt = f"--port {port}" if port else ""
        self.interface = ConnectionManager(f"{interface_txt} {port_txt}").connect()
        self.eval_board = TMC2660_eval(self.interface)
        self.lb = Landungsbruecke(self.interface)
        self.bank = 0
        self.axis = 0
        self.motor = self.eval_board.motors[0]
        self.set_microsteps(step_mode)
        self.microsteps = self.get_microsteps()

        #self.set_max_current(current_mA)
        #self.set_standby_current(current_standstill_mA)

    # --------------- MOTOR CONTROL ---------------

    def enable_motor(self):
        self.interface.set_global_parameter(self.lb.GP.DriversEnable, self.bank, 1)

    def disable_motor(self):
        self.interface.set_global_parameter(self.lb.GP.DriversEnable, self.bank, 0)

    def move_up(self, distance_mm: float, speed_mm_s: float, acceleration_mm_s2: float = 0):
        self.set_speed(speed_mm_s)
        self.set_acceleration(acceleration_mm_s2)
        steps = self.mechanical_setup.mm_to_steps(distance_mm, self.microsteps)
        self.interface.move_by(0, int(steps))

    def move_down(self, distance_mm: float, speed_mm_s: float, acceleration_mm_s2: float = 0):
        self.move_up(-distance_mm, speed_mm_s, acceleration_mm_s2)

    def stop_motor(self):
        self.motor.stop()

    def get_current_position_mm(self):
        pos = self.get_actual_position()
        return self.mechanical_setup.steps_to_mm(pos, self.microsteps)

    def run_to_position(self, position_mm: float, speed_mm_s: float = None, acceleration_mm_s2: float = None):
        self.set_speed(speed_mm_s)
        self.set_acceleration(acceleration_mm_s2)
        steps = self.mechanical_setup.mm_to_steps(position_mm, self.microsteps)
        self.motor.move_to(steps)

    # --------------- MOTOR CONFIGURATION ---------------

    def set_microsteps(self, microsteps: int):
        self.microsteps = microsteps
        _step_mode = self.microstep_steps_to_idx(microsteps)
        self.motor.set_axis_parameter(self.motor.AP.MicrostepResolution, int(_step_mode))

    def get_microsteps(self) -> int:
        mstep = self.eval_board.get_axis_parameter(self.motor.AP.MicrostepResolution, self.axis)
        return self.microstep_idx_to_steps(mstep)

    def set_max_current(self, current_mA: float):
        self.motor.set_axis_parameter(self.motor.AP.MaxCurrent, int(current_mA))

    def set_standby_current(self, current_mA: float):
        self.motor.set_axis_parameter(self.motor.AP.StandbyCurrent, int(current_mA))

    def set_speed(self, speed_mm_s: float):
        if speed_mm_s is None:
            return
        steps_per_second = self.mechanical_setup.mm_s_to_stepss(speed_mm_s, self.microsteps)
        self.motor.set_axis_parameter(self.motor.AP.MaxVelocity, int(steps_per_second))

    def set_acceleration(self, acceleration_mm_s2: float):
        if acceleration_mm_s2 is None or acceleration_mm_s2 == 0:
            return
        steps_per_second2 = self.mechanical_setup.mm_s2_to_rpss(acceleration_mm_s2)
        self.motor.set_axis_parameter(self.motor.AP.MaxAcceleration, int(steps_per_second2))

    # --------------- HELPER METHODS ---------------

    def get_actual_position(self):
        return self.eval_board.get_axis_parameter(self.motor.AP.ActualPosition, self.axis)

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
