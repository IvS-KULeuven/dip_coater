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
        self.disable_motor()
        self.set_microsteps(step_mode)

        self.set_max_current(current_mA)
        self.set_standby_current(current_standstill_mA)

    # --------------- MOTOR CONTROL ---------------

    def enable_motor(self):
        self.interface.set_global_parameter(self.lb.GP.DriversEnable, self.bank, 1)
        if self.is_motor_enabled() != 1:
            raise ValueError("Motor should be enabled")

    def disable_motor(self):
        self.interface.set_global_parameter(self.lb.GP.DriversEnable, self.bank, 0)
        if self.is_motor_enabled() != 0:
            raise ValueError("Motor should be enabled")

    def is_motor_enabled(self):
        return self.interface.get_global_parameter(self.lb.GP.DriversEnable, self.bank)

    def rotate(self, revs: float, rps: float, rpss: float = None):
        self.set_speed_rps(rps)
        self.set_acceleration_rpss(rpss)
        steps = self.mechanical_setup.revs_to_steps(revs, self.microsteps)
        self.motor.move_by(0, int(steps))

    def move(self, distance_mm: float, speed_mm_s: float, acceleration_mm_s2: float = None):
        revs = self.mechanical_setup.mm_to_revs(distance_mm)
        rps = self.mechanical_setup.mm_s_to_rps(speed_mm_s)
        rpss = self.mechanical_setup.mm_s2_to_rpss(acceleration_mm_s2)
        self.rotate(revs, rps, rpss)

    def move_up(self, distance_mm: float, speed_mm_s: float, acceleration_mm_s2: float = None):
        self.move(distance_mm, speed_mm_s, acceleration_mm_s2)

    def move_down(self, distance_mm: float, speed_mm_s: float, acceleration_mm_s2: float = None):
        self.move(-distance_mm, speed_mm_s, acceleration_mm_s2)

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
        self.verify_microsteps(microsteps)
        self.microsteps = microsteps
        self.motor.set_axis_parameter(self.motor.AP.MicrostepResolution, microsteps)

        verify_microsteps = self.get_microsteps()
        if self.microsteps != verify_microsteps:
            raise ValueError(f"Set microsteps {microsteps} does not match read back value {verify_microsteps}")

    def get_microsteps(self) -> int:
        mstep = self.motor.get_axis_parameter(self.motor.AP.MicrostepResolution, self.axis)
        return self.microstep_idx_to_steps(mstep)

    def set_max_current(self, current_mA: float):
        self.motor.set_axis_parameter(self.motor.AP.MaxCurrent, int(current_mA))

        verify_current = self.get_max_current()
        if current_mA != verify_current:
            raise ValueError(f"Set max current {current_mA} mA does not match read back value {verify_current} mA")

    def get_max_current(self):
        return self.motor.get_axis_parameter(self.motor.AP.MaxCurrent, self.axis)

    def set_standby_current(self, current_mA: float):
        self.motor.set_axis_parameter(self.motor.AP.StandbyCurrent, int(current_mA))

        verify_current = self.get_standby_current()
        if current_mA != verify_current:
            raise ValueError(f"Set standby current {current_mA} mA does not match read back value {verify_current} mA")
        
    def get_standby_current(self):
        return self.motor.get_axis_parameter(self.motor.AP.StandbyCurrent, self.axis)

    def set_speed_rps(self, rps: float):
        if rps is None:
            return
        steps_per_second = self.mechanical_setup.rps_to_stepss(rps, self.microsteps)
        self.motor.set_axis_parameter(self.motor.AP.MaxVelocity, int(steps_per_second))

    def set_acceleration_rpss(self, rpss: float):
        if rpss is None or rpss == 0:
            return
        steps_per_second2 = self.mechanical_setup.rpss_to_stepss(rpss, self.microsteps)
        self.motor.set_axis_parameter(self.motor.AP.MaxAcceleration, int(steps_per_second2))

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

    def cleanup(self):
        self.disable_motor()
        self.interface.close()
