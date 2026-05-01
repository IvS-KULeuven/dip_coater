from TMC_2209._TMC_2209_logger import Loglevel
from TMC_2209._TMC_2209_move import MovementAbsRel, StopMode
import time


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
        self._max_speed_steps_per_second = 0
        self._motion_start_time_s = None
        self._motion_start_position_steps = 0.0
        self._motion_target_position_steps = None
        self._motion_duration_s = 0.0
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
        self._max_speed_steps_per_second = abs(steps_per_second)

    def set_acceleration(self, steps_per_second2: float):
        pass

    def run_to_position_revolutions_threaded(self, revolutions: float):
        steps = int(revolutions * self._steps_per_rev * self._microsteps)
        self.run_to_position_steps_threaded(steps, movement_abs_rel=MovementAbsRel.RELATIVE)

    def run_to_position_steps_threaded(self, steps: int, movement_abs_rel: MovementAbsRel = None):
        self._update_motion_state()
        movement = movement_abs_rel if movement_abs_rel is not None else self._movement_abs_rel
        if movement == MovementAbsRel.ABSOLUTE:
            target_position_steps = steps
        else:
            target_position_steps = self._current_position_steps + steps
        duration_s = self._duration_for_steps(
            target_position_steps - self._current_position_steps
        )
        if duration_s <= 0:
            self._current_position_steps = target_position_steps
            self._distance_to_go = 0
            self._motion_target_position_steps = None
            return
        self._motion_start_time_s = time.monotonic()
        self._motion_start_position_steps = self._current_position_steps
        self._motion_target_position_steps = target_position_steps
        self._motion_duration_s = duration_s
        self._distance_to_go = abs(target_position_steps - self._current_position_steps)

    def distance_to_go(self) -> int:
        self._update_motion_state()
        return round(self._distance_to_go)

    def wait_for_movement_finished_threaded(self) -> StopMode:
        while self.distance_to_go() > 0:
            time.sleep(0.01)
        return StopMode.NO

    def stop(self, stop_mode: StopMode = StopMode.HARDSTOP):
        self._update_motion_state()
        self._motion_target_position_steps = None
        self._distance_to_go = 0

    def do_homing(self, *args, **kwargs):
        pass

    def get_current_position(self) -> int:
        self._update_motion_state()
        return round(self._current_position_steps)

    def set_current_position(self, steps: int):
        self._motion_target_position_steps = None
        self._current_position_steps = steps
        self._distance_to_go = 0

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

    def _duration_for_steps(self, steps: float) -> float:
        if steps == 0 or self._max_speed_steps_per_second <= 0:
            return 0.0
        return abs(steps) / self._max_speed_steps_per_second

    def _update_motion_state(self) -> None:
        if self._motion_target_position_steps is None:
            return
        if self._motion_start_time_s is None or self._motion_duration_s <= 0:
            self._finish_motion()
            return
        elapsed_s = time.monotonic() - self._motion_start_time_s
        if elapsed_s >= self._motion_duration_s:
            self._finish_motion()
            return
        progress = max(0.0, elapsed_s / self._motion_duration_s)
        travel_steps = (
            self._motion_target_position_steps - self._motion_start_position_steps
        )
        self._current_position_steps = (
            self._motion_start_position_steps + travel_steps * progress
        )
        self._distance_to_go = abs(
            self._motion_target_position_steps - self._current_position_steps
        )

    def _finish_motion(self) -> None:
        if self._motion_target_position_steps is not None:
            self._current_position_steps = self._motion_target_position_steps
        self._motion_target_position_steps = None
        self._distance_to_go = 0
