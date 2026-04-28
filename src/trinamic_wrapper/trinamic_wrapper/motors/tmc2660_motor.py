"""TMC2660-specific stepper-motor wrapper.

The TMC2660 is driver-only: it has no ramp generator and no StealthChop.
The Landungsbrücke firmware emulates rotation and position moves on its
MCU side, so the user-facing API stays the same as for the TMC5160.

Current is the 5-bit CS field in SGCSCONF. The firmware's ``MaxCurrent``
axis parameter accepts the CS value directly (0..31), not a scaled byte
like the TMC5160 does.
"""

from __future__ import annotations

from typing import Any

from pytrinamic.ic import TMC2660

from ..config import MotorConfig
from ..conversions import (
    cs_to_mA_rms,
    mA_rms_to_cs,
    rps_to_usteps_per_s,
    usteps_per_s_to_rps,
)
from ..exceptions import UnsupportedFeatureError
from .base import BaseStepperMotor


# TMC2660 parasitic sense-resistor offset from datasheet
_TMC2660_RSENSE_OFFSET = 0.03

# TMC2660 full-scale sense voltages — slightly different from TMC5160
_TMC2660_VFS_STANDARD = 0.305   # VSENSE=0
_TMC2660_VFS_HIGH_SENS = 0.165  # VSENSE=1


class TMC2660Motor(BaseStepperMotor):
    """Wrapper for a TMC2660 driven through the Landungsbrücke."""

    SUPPORTED_FEATURES = frozenset({
        "interpolation",
        "coolstep",
        "stallguard",
    })

    def __init__(
        self,
        eval_board: Any,
        config: MotorConfig,
        axis: int = 0,
    ) -> None:
        super().__init__(eval_board, config, axis)
        # Configure VSENSE bit to match config
        self._motor.set_axis_parameter(
            self._motor.AP.VSense,
            1 if config.vsense_high_sensitivity else 0,
        )

    # ------------------------------------------------------------------ #
    # Current: mA <-> CS (direct, 0..31)
    # ------------------------------------------------------------------ #

    def _current_to_raw(self, current_mA: float) -> int:
        vfs = (
            _TMC2660_VFS_HIGH_SENS
            if self._config.vsense_high_sensitivity
            else _TMC2660_VFS_STANDARD
        )
        return mA_rms_to_cs(
            current_mA,
            self._config.sense_resistor_ohms,
            vfs,
            _TMC2660_RSENSE_OFFSET,
        )

    def _raw_to_current(self, raw: int) -> float:
        if raw == 0:
            return 0.0
        vfs = (
            _TMC2660_VFS_HIGH_SENS
            if self._config.vsense_high_sensitivity
            else _TMC2660_VFS_STANDARD
        )
        return cs_to_mA_rms(
            raw,
            self._config.sense_resistor_ohms,
            vfs,
            _TMC2660_RSENSE_OFFSET,
        )

    def _set_run_current_raw(self, raw: int) -> None:
        self._motor.set_axis_parameter(self._motor.AP.MaxCurrent, raw)

    def _set_standstill_current_raw(self, raw: int) -> None:
        self._motor.set_axis_parameter(self._motor.AP.StandbyCurrent, raw)

    # ------------------------------------------------------------------ #
    # Speed / accel (μsteps/s directly)
    # ------------------------------------------------------------------ #

    def _rps_to_raw_speed(self, rps: float) -> int:
        return rps_to_usteps_per_s(
            rps,
            self._config.full_steps_per_rev,
            self._step_mode.microsteps_per_fullstep,
        )

    def _raw_speed_to_rps(self, raw: int) -> float:
        return usteps_per_s_to_rps(
            raw,
            self._config.full_steps_per_rev,
            self._step_mode.microsteps_per_fullstep,
        )

    def _rps2_to_raw_accel(self, rps2: float) -> int:
        # Same units as speed: μsteps/s^2
        return int(round(
            rps2
            * self._config.full_steps_per_rev
            * self._step_mode.microsteps_per_fullstep
        ))

    def _set_speed_raw(self, raw: int) -> None:
        self._motor.set_axis_parameter(self._motor.AP.MaxVelocity, raw)

    def _set_accel_raw(self, raw: int) -> None:
        self._motor.set_axis_parameter(self._motor.AP.MaxAcceleration, raw)

    # ------------------------------------------------------------------ #
    # Advanced features
    # ------------------------------------------------------------------ #

    def set_interpolation(self, enabled: bool) -> None:
        """Enable/disable interpolation to 256 μsteps (INTPOL bit in DRVCTRL)."""
        self._motor.set_axis_parameter(self._motor.AP.Intpol, 1 if enabled else 0)

    def set_stealthchop(
        self,
        enabled: bool,
        threshold_rps: float | None = None,
    ) -> None:
        # The TMC2660 predates StealthChop; explicitly flag this so users
        # can write chip-agnostic code that calls set_stealthchop() and
        # catch the exception to fall back.
        raise UnsupportedFeatureError(
            "TMC2660 does not support StealthChop. Use a TMC5160 for silent "
            "operation, or handle this with has_feature('stealthchop')."
        )

    def set_coolstep_threshold_rps(self, rps: float) -> None:
        """Enable CoolStep above the given speed (0 disables)."""
        if rps < 0:
            raise ValueError("rps must be non-negative")
        self.set_coolstep_threshold_raw(self._rps_to_raw_speed(rps) if rps > 0 else 0)

    @property
    def raw_ic(self) -> TMC2660:
        return self._eval.ics[0]
