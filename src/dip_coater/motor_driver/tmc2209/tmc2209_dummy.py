from TMC_2209._TMC_2209_logger import Loglevel
from TMC_2209._TMC_2209_move import MovementAbsRel, StopMode


class DummyTMCLogger:
    def __init__(self, loglevel: Loglevel = Loglevel.ERROR):
        self.loglevel = loglevel

    def set_loglevel(self, loglevel: Loglevel):
        self.loglevel = loglevel

    def add_handler(self, handler):
        pass

    def remove_handler(self, handler):
        pass


class DummyTMC2209:
    def __init__(self, *args, loglevel: Loglevel = Loglevel.ERROR, **kwargs):
        self.tmc_logger = DummyTMCLogger(loglevel=loglevel)
        self._steps_per_rev = 200
        self._microsteps = 8
        self._movement_abs_rel = MovementAbsRel.RELATIVE
        self._current_position_steps = 0
        self._distance_to_go = 0
        self._motor_enabled = False
        self._spreadcycle = False

    def set_vactual(self, value):
        pass

    def set_direction_reg(self, invert_direction: bool):
        pass

    def set_pdn_disable(self, value: bool):
        pass

    def set_current(self, current_mA: int, hold_current_multiplier: float = None,
                    pdn_disable: bool = None):
        pass

    def set_interpolation(self, interpolation: bool):
        pass

    def set_spreadcycle(self, spread_cycle: bool):
        self._spreadcycle = spread_cycle

    def get_spreadcycle(self) -> bool:
        return self._spreadcycle

    def set_microstepping_resolution(self, microsteps: int):
        self._microsteps = microsteps

    def get_microstepping_resolution(self) -> int:
        return self._microsteps

    def set_internal_rsense(self, enabled: bool):
        pass

    def set_movement_abs_rel(self, movement_abs_rel: MovementAbsRel):
        self._movement_abs_rel = movement_abs_rel

    def set_motor_enabled(self, enabled: bool):
        self._motor_enabled = enabled

    def set_max_speed(self, steps_per_second: float):
        pass

    def set_acceleration(self, steps_per_second2: float):
        pass

    def run_to_position_revolutions_threaded(self, revolutions: float):
        steps = int(revolutions * self._steps_per_rev * self._microsteps)
        self.run_to_position_steps_threaded(steps, movement_abs_rel=MovementAbsRel.RELATIVE)

    def run_to_position_steps_threaded(self, steps: int, movement_abs_rel: MovementAbsRel = None):
        movement = movement_abs_rel if movement_abs_rel is not None else self._movement_abs_rel
        if movement == MovementAbsRel.ABSOLUTE:
            self._current_position_steps = steps
        else:
            self._current_position_steps += steps
        self._distance_to_go = 0

    def distance_to_go(self) -> int:
        return self._distance_to_go

    def wait_for_movement_finished_threaded(self) -> StopMode:
        return StopMode.NO

    def stop(self, stop_mode: StopMode = StopMode.HARDSTOP):
        self._distance_to_go = 0

    def do_homing(self, *args, **kwargs):
        pass

    def get_current_position(self) -> int:
        return self._current_position_steps

    def set_current_position(self, steps: int):
        self._current_position_steps = steps

    def read_steps_per_rev(self) -> int:
        return self._steps_per_rev

    def read_ioin(self):
        pass

    def read_chopconf(self):
        pass

    def read_drv_status(self):
        pass

    def read_gconf(self):
        pass

    def test_stallguard_threshold(self, steps: int):
        pass
