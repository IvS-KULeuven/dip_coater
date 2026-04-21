from __future__ import annotations

import asyncio
import logging
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

    def enable_motor(self):
        self._motor.enable()

    def disable_motor(self):
        self._motor.disable()

    def invert_direction(self, invert_direction: bool = False):
        self._invert_direction = invert_direction

    def rotate(self, revs: float, rps: float, rpss: float = None):
        signed_revs = self._apply_direction_inversion(revs)
        direction = Direction.CW if signed_revs >= 0 else Direction.CCW
        self.set_speed_rps(rps)
        self.set_acceleration_rpss(rpss)
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
        self._motor.stop()

    def wait_for_motor_done(self):
        self._motor.wait_until_reached()

    async def wait_for_motor_done_async(self):
        while not self._motor.wait_until_reached(timeout_s=0.0):
            await asyncio.sleep(0.05)

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

    def get_speed_rps(self) -> float | None:
        return self._configured_speed_rps

    def set_acceleration_rpss(self, rpss: float):
        if rpss is None:
            return
        self._configured_accel_rpss = rpss
        self._motor.set_acceleration_rps2(rpss)

    def get_acceleration_rpss(self) -> float | None:
        return self._configured_accel_rpss

    def set_microsteps(self, microsteps: int):
        try:
            mode = _MICROSTEPS_TO_STEP_MODE[microsteps]
        except KeyError as exc:
            raise ValueError(
                f"Unsupported microsteps {microsteps}; expected one of "
                f"{sorted(_MICROSTEPS_TO_STEP_MODE)}"
            ) from exc
        self._motor.set_step_mode(mode)
        self.microsteps = mode.microsteps_per_fullstep

    def get_microsteps(self) -> int:
        return self._motor.get_step_mode().microsteps_per_fullstep

    def set_current(self, current_mA: float):
        self._motor.set_run_current_mA(current_mA)

    def get_current(self) -> float:
        return self._motor.get_run_current_mA()

    def set_current_standstill(self, current_mA: float):
        self._motor.set_standstill_current_mA(current_mA)

    def get_current_standstill(self) -> float:
        return self._motor.get_standstill_current_mA()

    def set_interpolation(self, interpolation: bool = True):
        self._motor.set_interpolation(interpolation)

    def set_stallguard_threshold(self, threshold: int):
        setter = getattr(self._motor, "set_stallguard_threshold", None)
        if setter is None:
            raise NotImplementedError("Underlying trinamic_wrapper motor has no StallGuard threshold API.")
        setter(threshold)

    def set_loglevel(self, loglevel):
        if isinstance(loglevel, int):
            self._logger.setLevel(loglevel)
            return
        if hasattr(loglevel, "value") and isinstance(loglevel.value, int):
            self._logger.setLevel(loglevel.value)
            return
        if hasattr(loglevel, "name"):
            self._logger.setLevel(str(loglevel.name))
            return
        self._logger.setLevel(loglevel)

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
            if self._close is not None:
                self._close()

    # ---- advanced settings not mapped yet ---------------------------------

    def set_chopper_mode(self, mode):
        raise NotImplementedError(
            "Chopper-mode mapping is not implemented in the dip_coater adapter yet."
        )

    def set_stallguard_enabled(self, enable: bool):
        raise NotImplementedError(
            "StallGuard enable/disable is not implemented in the dip_coater adapter yet."
        )

    def set_stallguard_filter_enabled(self, enable: bool):
        raise NotImplementedError(
            "StallGuard filter enable/disable is not implemented in the dip_coater adapter yet."
        )

    def set_coolstep_enabled(self, enable: bool):
        raise NotImplementedError(
            "CoolStep enable/disable is not implemented in the dip_coater adapter yet."
        )

    def set_coolstep_threshold(self, threshold: int):
        raise NotImplementedError(
            "CoolStep threshold in dip_coater units is not mapped to trinamic_wrapper yet."
        )

    def _move_mm(
        self,
        distance_mm: float,
        speed_mm_s: float | None,
        acceleration_mm_s2: float | None,
    ) -> None:
        revs = self.mechanical_setup.mm_to_revs(distance_mm)
        rps = self.mechanical_setup.mm_s_to_rps(speed_mm_s) if speed_mm_s is not None else None
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
        direction = Direction.CW if signed_revs >= 0 else Direction.CCW
        self._motor.rotate_by(abs(signed_revs), direction=direction)

    def _apply_direction_inversion(self, value: float) -> float:
        return -value if self._invert_direction else value
