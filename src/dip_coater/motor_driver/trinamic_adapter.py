from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from typing import Any

from trinamic_wrapper import Direction, StepMode, StepperMotor

from dip_coater.mechanical.mechanical_setup import MechanicalSetup
from dip_coater.motor_driver.motor_driver_interface import MotorDriver


_MICROSTEPS_TO_STEP_MODE = {
    1: StepMode.FULLSTEP,
    2: StepMode.USTEP_2,
    4: StepMode.USTEP_4,
    8: StepMode.USTEP_8,
    16: StepMode.USTEP_16,
    32: StepMode.USTEP_32,
    64: StepMode.USTEP_64,
    128: StepMode.USTEP_128,
    256: StepMode.USTEP_256,
}


class TrinamicWrapperMotorAdapter(MotorDriver):
    """Adapt ``trinamic_wrapper.StepperMotor`` to the legacy dip-coater API.

    This keeps all dip-coater-specific units and semantics on the application
    side, while leaving ``trinamic_wrapper`` focused on chip-level motion.
    """

    def __init__(
        self,
        motor: StepperMotor,
        mechanical_setup: MechanicalSetup,
        *,
        invert_direction: bool = False,
        close: Callable[[], None] | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        super().__init__(mechanical_setup)
        self._motor = motor
        self._close = close
        self._invert_direction = invert_direction
        self._logger = logger or logging.getLogger(
            f"{__name__}.{type(self).__name__}"
        )
        self._log_handlers: list[Any] = []
        self._configured_speed_rps: float | None = None
        self._configured_accel_rpss: float | None = None
        self._target_position_rot: float | None = None
        self._stealthchop_enabled: bool = False
        self._stealthchop_threshold_rps: float | None = None

    def enable_motor(self):
        self._motor.enable()
        self._logger.info("Motor enabled")

    def disable_motor(self):
        self._motor.disable()
        self._logger.info("Motor disabled")

    def invert_direction(self, invert_direction: bool = False):
        self._invert_direction = invert_direction
        self._logger.info(f"Direction inverted: {invert_direction}")

    def rotate(self, revs: float, rps: float, rpss: float = None):
        signed_revs = self._apply_direction_inversion(revs)
        direction = Direction.CW if signed_revs >= 0 else Direction.CCW
        self.set_speed_rps(rps)
        self.set_acceleration_rpss(rpss)
        self._target_position_rot = None
        self._logger.debug(
            f"Rotating {signed_revs:.4f} revolutions at {rps:.2f} rps "
            f"({direction.name})"
        )
        self._motor.rotate_by(abs(signed_revs), direction=direction)

    def move_up(
        self,
        distance_mm: float,
        speed_mm_s: float,
        acceleration_mm_s2: float = None,
        *args,
        **kwargs,
    ):
        self._move_mm(distance_mm, speed_mm_s, acceleration_mm_s2)

    def move_down(
        self,
        distance_mm: float,
        speed_mm_s: float,
        acceleration_mm_s2: float = None,
        *args,
        **kwargs,
    ):
        self._move_mm(-distance_mm, speed_mm_s, acceleration_mm_s2)

    def stop_motor(self):
        self._target_position_rot = None
        self._motor.stop()
        self._logger.info("Motor stopped")

    def wait_for_motor_done(self):
        self._wait_for_target_reached()
        self._logger.info("Motor done")

    async def wait_for_motor_done_async(self):
        while True:
            if self._is_target_reached():
                if await self._finalize_completed_move_async():
                    break
            await asyncio.sleep(0.05)
        self._target_position_rot = None
        self._logger.info("Motor done")

    def get_current_position_mm(self, homes_up: bool | None = None):
        return self.mechanical_setup.revs_to_mm(self._motor.get_actual_position_rot())

    def run_to_position(
        self,
        position_mm: float,
        speed_mm_s: float = None,
        acceleration_mm_s2: float = None,
        homes_up: bool | None = None,
    ):
        current_mm = self.get_current_position_mm(homes_up=homes_up)
        self._move_mm(position_mm - current_mm, speed_mm_s, acceleration_mm_s2)

    def is_homing_found(self):
        return False

    def set_speed_rps(self, rps: float):
        if rps is None:
            return
        self._configured_speed_rps = rps
        self._motor.set_speed_rps(rps)
        self._logger.info(f"Max velocity set to {rps:.2f} rps")

    def get_speed_rps(self) -> float | None:
        return self._configured_speed_rps

    def set_acceleration_rpss(self, rpss: float):
        if rpss is None:
            return
        self._configured_accel_rpss = rpss
        self._motor.set_acceleration_rps2(rpss)
        self._logger.info(f"Max acceleration set to {rpss:.2f} rpss")

    def get_acceleration_rpss(self) -> float | None:
        return self._configured_accel_rpss

    def set_microsteps(self, microsteps: int):
        try:
            mode = _MICROSTEPS_TO_STEP_MODE[microsteps]
        except KeyError as exc:
            msg = (
                f"Unsupported microsteps {microsteps}; expected one of "
                f"{sorted(_MICROSTEPS_TO_STEP_MODE)}"
            )
            self._logger.error(msg)
            raise ValueError(msg) from exc
        self._motor.set_step_mode(mode)
        self.microsteps = mode.microsteps_per_fullstep
        self._logger.info(f"Microsteps set to {self.microsteps}")

    def get_microsteps(self) -> int:
        return self._motor.get_step_mode().microsteps_per_fullstep

    def set_current(self, current_mA: float):
        self._motor.set_run_current_mA(current_mA)
        self._logger.info(f"Max current set to {current_mA:.1f} mA")

    def get_current(self) -> float:
        return self._motor.get_run_current_mA()

    def set_current_standstill(self, current_mA: float):
        self._motor.set_standstill_current_mA(current_mA)
        self._logger.info(f"Standstill current set to {current_mA:.1f} mA")

    def get_current_standstill(self) -> float:
        return self._motor.get_standstill_current_mA()

    def set_interpolation(self, interpolation: bool = True):
        self._motor.set_interpolation(interpolation)
        self._logger.info(
            f"Interpolation {'enabled' if interpolation else 'disabled'}"
        )

    def set_stealthchop_enabled(self, enable: bool):
        self._stealthchop_enabled = enable
        threshold = self._active_stealthchop_threshold()
        self._motor.set_stealthchop(enable, threshold if enable else None)
        self._logger.info(f"StealthChop {'enabled' if enable else 'disabled'}")

    def set_stealthchop_threshold(self, threshold_rps: float):
        if threshold_rps < 0:
            raise ValueError("StealthChop threshold must be non-negative")
        self._stealthchop_threshold_rps = threshold_rps
        if self._stealthchop_enabled:
            self._motor.set_stealthchop(
                True,
                self._active_stealthchop_threshold(),
            )
        self._logger.info(f"StealthChop threshold set to {threshold_rps:.2f} rps")

    def set_stallguard_threshold(self, threshold: int):
        setter = getattr(self._motor, "set_stallguard_threshold", None)
        if setter is None:
            msg = "Underlying trinamic_wrapper motor has no StallGuard threshold API."
            self._logger.error(msg)
            raise NotImplementedError(msg)
        setter(threshold)
        self._logger.info(f"StallGuard threshold set to {threshold}")

    def set_loglevel(self, loglevel):
        if isinstance(loglevel, int):
            self._logger.setLevel(loglevel)
        elif hasattr(loglevel, "value") and isinstance(loglevel.value, int):
            self._logger.setLevel(loglevel.value)
        elif hasattr(loglevel, "name"):
            self._logger.setLevel(str(loglevel.name))
        else:
            self._logger.setLevel(loglevel)
        level_name = getattr(loglevel, "name", str(loglevel))
        self._logger.info(f"Log level set to {level_name}")

    def add_log_handler(self, handler):
        self._log_handlers.append(handler)
        add_handler = getattr(self._logger, "addHandler", None)
        if add_handler is not None:
            add_handler(handler)

    def remove_log_handler(self, handler):
        if handler in self._log_handlers:
            self._log_handlers.remove(handler)
        remove_handler = getattr(self._logger, "removeHandler", None)
        if remove_handler is not None:
            remove_handler(handler)

    def cleanup(self):
        try:
            self.disable_motor()
        finally:
            self._target_position_rot = None
            if self._close is not None:
                self._close()
            self._logger.info("Motor driver cleaned up")

    def set_chopper_mode(self, mode):
        coerced = self._coerce_chopper_mode(mode)
        self._motor.set_chopper_mode(coerced)
        self._logger.info(f"Chopper mode set to {coerced}")

    def set_stallguard_enabled(self, enable: bool):
        self._motor.set_stallguard_enabled(enable)
        self._logger.info(f"StallGuard {'enabled' if enable else 'disabled'}")

    def set_stallguard_filter_enabled(self, enable: bool):
        self._motor.set_stallguard_filter_enabled(enable)
        self._logger.info(
            f"StallGuard filter {'enabled' if enable else 'disabled'}"
        )

    def set_coolstep_enabled(self, enable: bool):
        self._motor.set_coolstep_enabled(enable)
        self._logger.info(f"CoolStep {'enabled' if enable else 'disabled'}")

    def set_coolstep_threshold(self, threshold: int):
        setter = getattr(self._motor, "set_coolstep_threshold_raw", None)
        if setter is None:
            msg = "Underlying trinamic_wrapper motor has no CoolStep threshold API."
            self._logger.error(msg)
            raise NotImplementedError(msg)
        setter(threshold)
        self._logger.info(f"CoolStep threshold set to {threshold}")

    def enable_reference_stops(
        self,
        *,
        left: bool = True,
        right: bool = True,
    ):
        self._motor.enable_reference_stops(left=left, right=right)
        self._logger.info(
            f"Reference stops configured: left={left}, right={right}"
        )

    def get_left_endstop(self) -> bool:
        return self._motor.get_left_endstop()

    def get_right_endstop(self) -> bool:
        return self._motor.get_right_endstop()

    def _active_stealthchop_threshold(self) -> float | None:
        if self._stealthchop_threshold_rps is None:
            return None
        if self._stealthchop_threshold_rps <= 0:
            return None
        return self._stealthchop_threshold_rps

    def _move_mm(
        self,
        distance_mm: float,
        speed_mm_s: float | None,
        acceleration_mm_s2: float | None,
    ) -> None:
        revs = self.mechanical_setup.mm_to_revs(distance_mm)
        rps = (
            self.mechanical_setup.mm_s_to_rps(speed_mm_s)
            if speed_mm_s is not None
            else None
        )
        rpss = (
            self.mechanical_setup.mm_s2_to_rpss(acceleration_mm_s2)
            if acceleration_mm_s2 is not None
            else None
        )
        if rps is not None:
            self.set_speed_rps(rps)
        if rpss is not None:
            self.set_acceleration_rpss(rpss)
        signed_revs = self._apply_direction_inversion(revs)
        current_rot = self._motor.get_actual_position_rot()
        self._target_position_rot = current_rot + signed_revs
        if abs(signed_revs) <= self._position_tolerance_rot():
            self._logger.debug(
                f"Move {distance_mm:.4f} mm skipped (below tolerance)"
            )
            return
        direction = Direction.CW if signed_revs >= 0 else Direction.CCW
        self._logger.debug(
            f"Moving {distance_mm:.4f} mm "
            f"({signed_revs:.4f} revs, {direction.name})"
        )
        self._motor.rotate_by(abs(signed_revs), direction=direction)

    def _apply_direction_inversion(self, value: float) -> float:
        return -value if self._invert_direction else value

    @staticmethod
    def _coerce_chopper_mode(mode) -> int:
        if isinstance(mode, int):
            value = mode
        elif hasattr(mode, "value") and isinstance(mode.value, int):
            value = mode.value
        elif hasattr(mode, "label"):
            value = TrinamicWrapperMotorAdapter._coerce_chopper_mode(mode.label)
        else:
            normalized = str(mode).strip().lower().replace("_", " ")
            if normalized in {"0", "spreadcycle", "spread cycle"}:
                value = 0
            elif normalized in {"1", "constant toff", "constant off", "classic constant toff"}:
                value = 1
            else:
                raise ValueError(f"Unsupported chopper mode: {mode!r}")
        if value not in (0, 1):
            raise ValueError("chopper mode must be 0 (SpreadCycle) or 1 (Constant TOff)")
        return value

    def _wait_for_target_reached(self) -> None:
        while True:
            if self._is_target_reached():
                if self._finalize_completed_move():
                    break
        self._target_position_rot = None

    def _is_target_reached(self) -> bool:
        if self._target_position_rot is None:
            return (
                self._motor.wait_until_reached(timeout_s=0.0)
                or abs(self._motor.get_actual_speed_rps()) <= self._speed_tolerance_rps()
            )
        position_error = abs(
            self._motor.get_actual_position_rot() - self._target_position_rot
        )
        actual_speed_rps = abs(self._motor.get_actual_speed_rps())
        return (
            position_error <= self._position_tolerance_rot()
            and actual_speed_rps <= self._speed_tolerance_rps()
        )

    def _position_tolerance_rot(self) -> float:
        motion_units = self._motion_units_per_fullstep()
        full_steps = max(1, self.mechanical_setup.steps_per_revolution)
        return 2.0 / (full_steps * motion_units)

    @staticmethod
    def _speed_tolerance_rps() -> float:
        return 0.02

    def _motion_units_per_fullstep(self) -> int:
        getter = getattr(self._motor, "_motion_units_per_fullstep", None)
        if callable(getter):
            try:
                return max(1, int(getter()))
            except Exception:
                pass
        return max(1, self.get_microsteps())

    def _sync_target_to_actual_position(self) -> None:
        raw_motor = getattr(self._motor, "_motor", None)
        if raw_motor is None or not hasattr(raw_motor, "set_axis_parameter"):
            return
        actual_position = getattr(raw_motor.AP, "ActualPosition", None)
        target_position = getattr(raw_motor.AP, "TargetPosition", None)
        if actual_position is None or target_position is None:
            return
        try:
            actual = raw_motor.get_axis_parameter(actual_position, signed=True)
            raw_motor.set_axis_parameter(target_position, actual)
        except Exception:
            pass

    def _hold_completed_move_position(self) -> None:
        if self._target_position_rot is None:
            return
        self._motor.stop()
        self._sync_target_to_actual_position()

    def _completed_move_is_stable(self) -> bool:
        if self._target_position_rot is None:
            return True
        position_error = abs(
            self._motor.get_actual_position_rot() - self._target_position_rot
        )
        actual_speed_rps = abs(self._motor.get_actual_speed_rps())
        return (
            position_error <= self._position_tolerance_rot()
            and actual_speed_rps <= self._speed_tolerance_rps()
        )

    def _finalize_completed_move(self) -> bool:
        if self._target_position_rot is None:
            return True
        self._hold_completed_move_position()
        for _ in range(4):
            time.sleep(0.05)
            if not self._completed_move_is_stable():
                return False
        return True

    async def _finalize_completed_move_async(self) -> bool:
        if self._target_position_rot is None:
            return True
        self._hold_completed_move_position()
        for _ in range(4):
            await asyncio.sleep(0.05)
            if not self._completed_move_is_stable():
                return False
        return True
