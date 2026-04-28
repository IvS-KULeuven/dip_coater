"""TMC5160-specific stepper-motor wrapper.

The TMC5160 has an internal motion controller (ramp generator), StealthChop,
CoolStep, and StallGuard2. Current is set via the 5-bit IRUN/IHOLD fields in
the IHOLD_IRUN register. On the Landungsbruecke firmware used with this
wrapper, the ``MaxCurrent`` and ``StandbyCurrent`` axis parameters take the
5-bit CS value directly.
"""

from __future__ import annotations

from typing import Any

from pytrinamic.ic import TMC5160

from ..config import MotorConfig, StepMode
from ..conversions import cs_to_mA_rms, mA_rms_to_cs
from .base import BaseStepperMotor


# TMC5160 parasitic sense-resistor offset from datasheet (§9)
_TMC5160_RSENSE_OFFSET = 0.02


class TMC5160Motor(BaseStepperMotor):
    """Wrapper for a TMC5160 driven through the Landungsbrücke."""

    SUPPORTED_FEATURES = frozenset({
        "stealthchop",
        "interpolation",
        "coolstep",
        "stallguard",
        "ramp_generator",
        "reference_switches",
    })

    def __init__(
        self,
        eval_board: Any,
        config: MotorConfig,
        axis: int = 0,
    ) -> None:
        super().__init__(eval_board, config, axis)
        # Default ramp shape: trapezoidal. A1/V1 are the kink points for
        # the six-point ramp; setting A1=0 disables the first segment and
        # you get a pure trapezoid using AMAX/DMAX/D1.
        # We pick sensible defaults here; user can override via the raw
        # .eval_board / .motor handles.
        self._motor.set_axis_parameter(self._motor.AP.A1, 0)
        self._motor.set_axis_parameter(self._motor.AP.V1, 0)
        self._motor.set_axis_parameter(self._motor.AP.StartVelocity, 1)
        self._motor.set_axis_parameter(self._motor.AP.StopVelocity, 10)

    # ------------------------------------------------------------------ #
    # Current: mA <-> IRUN/IHOLD (via axis parameters MaxCurrent/StandbyCurrent)
    # ------------------------------------------------------------------ #
    #
    # The Landungsbruecke firmware on this setup accepts the 5-bit CS value
    # directly in MaxCurrent / StandbyCurrent, so the axis parameters and
    # the IHOLD_IRUN register stay consistent.

    def _current_to_raw(self, current_mA: float) -> int:
        vfs = (
            self._config.vfs_high_sens
            if self._config.vsense_high_sensitivity
            else self._config.vfs_standard
        )
        cs = mA_rms_to_cs(
            current_mA,
            self._config.sense_resistor_ohms,
            vfs,
            _TMC5160_RSENSE_OFFSET,
        )
        return cs

    def _raw_to_current(self, raw: int) -> float:
        vfs = (
            self._config.vfs_high_sens
            if self._config.vsense_high_sensitivity
            else self._config.vfs_standard
        )
        return cs_to_mA_rms(
            raw,
            self._config.sense_resistor_ohms,
            vfs,
            _TMC5160_RSENSE_OFFSET,
        )

    def _set_run_current_raw(self, raw: int) -> None:
        self._motor.set_axis_parameter(self._motor.AP.MaxCurrent, raw)

    def _set_standstill_current_raw(self, raw: int) -> None:
        self._motor.set_axis_parameter(self._motor.AP.StandbyCurrent, raw)

    # ------------------------------------------------------------------ #
    # Speed / accel
    # ------------------------------------------------------------------ #

    _SUPPORTED_STEP_MODES = frozenset({
        StepMode.USTEP_2,
        StepMode.USTEP_4,
        StepMode.USTEP_16,
        StepMode.USTEP_256,
    })

    def set_step_mode(self, mode: StepMode) -> None:
        if mode not in self._SUPPORTED_STEP_MODES:
            supported = ", ".join(
                m.name for m in sorted(self._SUPPORTED_STEP_MODES, key=int)
            )
            raise ValueError(
                "TMC5160 eval firmware supports only these step modes on this "
                f"setup: {supported}; got {mode.name}"
            )
        super().set_step_mode(mode)

    def _motion_units_per_fullstep(self) -> int:
        """Landungsbruecke firmware uses the MRES code (0..8), not 2**MRES."""
        return max(1, int(self._step_mode))

    def _rps_to_raw_speed(self, rps: float) -> int:
        units_per_rev = (
            self._config.full_steps_per_rev * self._motion_units_per_fullstep()
        )
        return int(round(rps * units_per_rev * (1 << 24) / self._config.clock_hz))

    def _raw_speed_to_rps(self, raw: int) -> float:
        units_per_rev = (
            self._config.full_steps_per_rev * self._motion_units_per_fullstep()
        )
        return raw * self._config.clock_hz / (1 << 24) / units_per_rev

    def _rps2_to_raw_accel(self, rps2: float) -> int:
        units_per_rev = (
            self._config.full_steps_per_rev * self._motion_units_per_fullstep()
        )
        return int(
            round(rps2 * units_per_rev * (1 << 41) / (self._config.clock_hz ** 2))
        )

    def _set_speed_raw(self, raw: int) -> None:
        self._motor.set_axis_parameter(self._motor.AP.MaxVelocity, raw)

    def _set_accel_raw(self, raw: int) -> None:
        self._motor.set_axis_parameter(self._motor.AP.MaxAcceleration, raw)
        # Also set DMAX/D1 to the same value so the decel phase matches
        # the accel phase. Users wanting asymmetric ramps can poke the
        # axis parameters directly.
        self._motor.set_axis_parameter(self._motor.AP.MaxDeceleration, raw)
        self._motor.set_axis_parameter(self._motor.AP.D1, raw)

    # ------------------------------------------------------------------ #
    # Advanced features
    # ------------------------------------------------------------------ #

    def set_interpolation(self, enabled: bool) -> None:
        """Enable/disable 256-microstep interpolation (INTPOL bit)."""
        self._eval.write_register_field(TMC5160.FIELD.INTPOL, 1 if enabled else 0)

    def set_stealthchop(
        self,
        enabled: bool,
        threshold_rps: float | None = None,
    ) -> None:
        """Enable StealthChop silent mode.

        When ``threshold_rps`` is given, StealthChop is used below that speed
        and SpreadCycle above. The TPWMTHRS register holds the transition
        point (lower TPWMTHRS = higher threshold speed — see datasheet §5.4).
        """
        # EN_PWM_MODE bit in GCONF enables StealthChop globally
        self._eval.write_register_field(
            TMC5160.FIELD.EN_PWM_MODE, 1 if enabled else 0
        )
        if not enabled:
            return
        if threshold_rps is None:
            return
        # TPWMTHRS = f_clk / (256 * N * rps) — time-per-ustep threshold
        if threshold_rps <= 0:
            raise ValueError("threshold_rps must be positive")
        ustep_per_s = threshold_rps * 256 * self._config.full_steps_per_rev
        tpwmthrs = int(round(self._config.clock_hz / ustep_per_s))
        tpwmthrs = max(0, min(tpwmthrs, (1 << 20) - 1))  # 20-bit field
        self._eval.write_register(TMC5160.REG.TPWMTHRS, tpwmthrs)

    def set_coolstep_threshold_rps(self, rps: float) -> None:
        """Enable CoolStep above the given speed (0 disables)."""
        if rps < 0:
            raise ValueError("rps must be non-negative")
        self.set_coolstep_threshold_raw(self._rps_to_raw_speed(rps) if rps > 0 else 0)

    @property
    def raw_ic(self) -> TMC5160:
        """Direct handle to the IC definition for register/field access."""
        return self._eval.ics[0]
