"""Base class for chip-specific stepper-motor wrappers.

Holds all the logic that is *not* chip-specific: soft-limit checks, state
tracking, feature-discovery defaults, position-reached polling, etc.

Subclasses provide:
- ``_set_run_current_raw`` / ``_set_standstill_current_raw``
- ``_set_speed_raw`` / ``_set_accel_raw``
- ``_current_to_raw`` / ``_raw_to_current``
- the ``SUPPORTED_FEATURES`` set
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

from ..config import Direction, MotorConfig, StepMode
from ..conversions import (
    revolutions_to_usteps,
    usteps_to_revolutions,
)
from ..exceptions import OutOfRangeError, UnsupportedFeatureError


class BaseStepperMotor(ABC):
    """Shared implementation for TMC chip wrappers.

    Not intended to be instantiated directly — use :func:`create_motor`.
    """

    # Set by subclasses
    SUPPORTED_FEATURES: frozenset[str] = frozenset()

    def __init__(
        self,
        eval_board: Any,
        config: MotorConfig,
        axis: int = 0,
    ) -> None:
        self._eval = eval_board
        self._config = config
        self._axis = axis
        self._motor = eval_board.motors[axis]

        # cached desired values so we can e.g. re-apply speed when rotate()
        # is called without an argument
        self._desired_speed_rps: float = 1.0
        self._step_mode: StepMode = config.default_microsteps
        self._enabled: bool = False
        self._chopper_mode: int = 0
        self._stallguard_enabled: bool = True
        self._stallguard_threshold: int = 0
        self._coolstep_enabled: bool = False
        self._coolstep_threshold_raw: int = 0

    # ------------------------------------------------------------------ #
    # Feature discovery
    # ------------------------------------------------------------------ #

    def has_feature(self, name: str) -> bool:
        return name in self.SUPPORTED_FEATURES

    def _require_feature(self, name: str) -> None:
        if not self.has_feature(name):
            raise UnsupportedFeatureError(
                f"{type(self).__name__} does not support feature {name!r}; "
                f"supported: {sorted(self.SUPPORTED_FEATURES)}"
            )

    # ------------------------------------------------------------------ #
    # Enable / disable
    # ------------------------------------------------------------------ #

    def enable(self) -> None:
        # Restore configured currents. On both chips, setting a run current
        # of 0 is effectively "disabled", so we re-apply the cached value.
        self._set_run_current_raw(self._cached_run_current_raw)
        self._set_standstill_current_raw(self._cached_standstill_raw)
        self._enabled = True

    def disable(self) -> None:
        # Stop first so we don't leave the chip pulsing while de-energised.
        self.stop()
        self._set_run_current_raw(0)
        self._set_standstill_current_raw(0)
        self._enabled = False

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    # ------------------------------------------------------------------ #
    # Current
    # ------------------------------------------------------------------ #

    _cached_run_current_raw: int = 0
    _cached_standstill_raw: int = 0
    _cached_run_current_mA: float = 0.0
    _cached_standstill_current_mA: float = 0.0

    def set_run_current_mA(self, current_mA: float) -> None:
        self._check_current_limit(current_mA)
        raw = self._current_to_raw(current_mA)
        self._cached_run_current_raw = raw
        self._cached_run_current_mA = 0.0 if current_mA == 0 else self._raw_to_current(raw)
        if self._enabled:
            self._set_run_current_raw(raw)

    def set_standstill_current_mA(self, current_mA: float) -> None:
        self._check_current_limit(current_mA)
        raw = self._current_to_raw(current_mA)
        self._cached_standstill_raw = raw
        self._cached_standstill_current_mA = (
            0.0 if current_mA == 0 else self._raw_to_current(raw)
        )
        if self._enabled:
            self._set_standstill_current_raw(raw)

    def get_run_current_mA(self) -> float:
        return self._cached_run_current_mA

    def get_standstill_current_mA(self) -> float:
        return self._cached_standstill_current_mA

    def _check_current_limit(self, current_mA: float) -> None:
        if current_mA < 0:
            raise OutOfRangeError("current must be non-negative")
        limit = self._config.max_current_mA_limit
        if limit is not None and current_mA > limit:
            raise OutOfRangeError(
                f"Requested {current_mA:.0f} mA exceeds configured safety "
                f"limit of {limit:.0f} mA. Raise MotorConfig.max_current_mA_limit "
                f"if intentional."
            )

    # ------------------------------------------------------------------ #
    # Motion parameters
    # ------------------------------------------------------------------ #

    def set_speed_rps(self, speed_rps: float) -> None:
        if speed_rps < 0:
            raise OutOfRangeError("speed must be non-negative; use direction=CCW")
        self._desired_speed_rps = speed_rps
        self._set_speed_raw(self._rps_to_raw_speed(speed_rps))

    def set_acceleration_rps2(self, accel_rps2: float) -> None:
        if accel_rps2 <= 0:
            raise OutOfRangeError("acceleration must be positive")
        self._set_accel_raw(self._rps2_to_raw_accel(accel_rps2))

    def set_step_mode(self, mode: StepMode) -> None:
        self._motor.set_axis_parameter(
            self._motor.AP.MicrostepResolution, int(mode)
        )
        self._step_mode = mode

    def get_step_mode(self) -> StepMode:
        return self._step_mode

    # ------------------------------------------------------------------ #
    # Motion commands
    # ------------------------------------------------------------------ #

    def rotate(
        self,
        speed_rps: float | None = None,
        direction: Direction = Direction.CW,
    ) -> None:
        if speed_rps is not None:
            self.set_speed_rps(speed_rps)
        self._restore_run_current_for_motion()
        raw = self._rps_to_raw_speed(self._desired_speed_rps) * int(direction)
        self._eval.rotate(self._axis, raw)

    def rotate_by(
        self,
        revolutions: float,
        direction: Direction = Direction.CW,
    ) -> None:
        self._restore_run_current_for_motion()
        usteps = revolutions_to_usteps(
            revolutions,
            self._config.full_steps_per_rev,
            self._motion_units_per_fullstep(),
        )
        signed_usteps = usteps * int(direction)
        current_usteps = self._motor.get_axis_parameter(
            self._motor.AP.ActualPosition, signed=True
        )
        target_usteps = current_usteps + signed_usteps
        # Use an absolute target rather than a relative move command.
        # On the TMC5160 eval-board firmware used in this repo, relative
        # move_by commands can behave unstably after reaching the target,
        # while move_to keeps the board locked to a single absolute target.
        self._eval._connection.move_to(
            self._axis, target_usteps, self._eval._module_id
        )

    def stop(self) -> None:
        self._eval.stop(self._axis)
        if self._enabled:
            self._set_run_current_raw(self._cached_standstill_raw)

    def wait_until_reached(self, timeout_s: float | None = None) -> bool:
        deadline = None if timeout_s is None else time.monotonic() + timeout_s
        while True:
            # Axis-parameter 8 = PositionReachedFlag on both chips (via firmware)
            if self._motor.get_axis_parameter(self._motor.AP.PositionReachedFlag):
                return True
            if deadline is not None and time.monotonic() > deadline:
                return False
            time.sleep(0.01)

    # ------------------------------------------------------------------ #
    # Status
    # ------------------------------------------------------------------ #

    def get_actual_position_rot(self) -> float:
        usteps = self._motor.get_axis_parameter(
            self._motor.AP.ActualPosition, signed=True
        )
        return usteps_to_revolutions(
            usteps,
            self._config.full_steps_per_rev,
            self._motion_units_per_fullstep(),
        )

    def get_actual_speed_rps(self) -> float:
        raw = self._motor.get_axis_parameter(
            self._motor.AP.ActualVelocity, signed=True
        )
        return self._raw_speed_to_rps(raw)

    def reset_position(self) -> None:
        self._motor.set_axis_parameter(self._motor.AP.ActualPosition, 0)
        self._motor.set_axis_parameter(self._motor.AP.TargetPosition, 0)

    def _motion_units_per_fullstep(self) -> int:
        """Units-per-fullstep used by the firmware for motion commands/APs."""
        return self._step_mode.microsteps_per_fullstep

    def _restore_run_current_for_motion(self) -> None:
        if self._enabled:
            self._set_run_current_raw(self._cached_run_current_raw)

    # ------------------------------------------------------------------ #
    # Default (no-op) advanced features — override in subclass
    # ------------------------------------------------------------------ #

    def set_interpolation(self, enabled: bool) -> None:
        self._require_feature("interpolation")
        raise NotImplementedError  # pragma: no cover — overridden

    def set_chopper_mode(self, mode: int) -> None:
        """Set chopper mode through PyTrinamic's ConstantTOffMode AP.

        0 selects SpreadCycle. 1 selects classic constant TOff.
        """
        if mode not in (0, 1):
            raise ValueError("chopper mode must be 0 (SpreadCycle) or 1 (Constant TOff)")
        self._chopper_mode = mode
        self._motor.set_axis_parameter(self._motor.AP.ConstantTOffMode, mode)

    def set_stealthchop(
        self,
        enabled: bool,
        threshold_rps: float | None = None,
    ) -> None:
        self._require_feature("stealthchop")
        raise NotImplementedError  # pragma: no cover — overridden

    def set_stallguard_enabled(self, enabled: bool) -> None:
        self._require_feature("stallguard")
        self._stallguard_enabled = enabled
        threshold = self._stallguard_threshold if enabled else 0
        self._motor.set_axis_parameter(self._motor.AP.SG2Threshold, threshold)

    def set_stallguard_filter_enabled(self, enabled: bool) -> None:
        self._require_feature("stallguard")
        self._motor.set_axis_parameter(
            self._motor.AP.SG2FilterEnable, 1 if enabled else 0
        )

    def set_stallguard_threshold(self, threshold: int) -> None:
        self._require_feature("stallguard")
        if not -64 <= threshold <= 63:
            raise ValueError("threshold must be in [-64, 63]")
        self._stallguard_threshold = threshold
        if self._stallguard_enabled:
            self._motor.set_axis_parameter(self._motor.AP.SG2Threshold, threshold)

    def configure_coolstep(
        self,
        *,
        min_current: int = 0,
        current_down_step: int = 0,
        current_up_step: int = 0,
        hysteresis: int = 0,
        threshold_speed: int = 0,
    ) -> None:
        self._require_feature("coolstep")
        self._check_range("min_current", min_current, 0, 1)
        self._check_range("current_down_step", current_down_step, 0, 3)
        self._check_range("current_up_step", current_up_step, 0, 3)
        self._check_range("hysteresis", hysteresis, 0, 15)
        self._check_range("threshold_speed", threshold_speed, 0, (1 << 31) - 1)
        self._coolstep_threshold_raw = threshold_speed
        self._coolstep_enabled = threshold_speed > 0
        self._motor.set_axis_parameter(self._motor.AP.SEIMIN, min_current)
        self._motor.set_axis_parameter(self._motor.AP.SECDS, current_down_step)
        self._motor.set_axis_parameter(self._motor.AP.SECUS, current_up_step)
        self._motor.set_axis_parameter(
            self._motor.AP.smartEnergyHysteresis, hysteresis
        )
        self._motor.set_axis_parameter(
            self._motor.AP.smartEnergyThresholdSpeed, threshold_speed
        )

    def set_coolstep_enabled(self, enabled: bool) -> None:
        self._require_feature("coolstep")
        self._coolstep_enabled = enabled
        threshold = self._coolstep_threshold_raw if enabled else 0
        self._motor.set_axis_parameter(
            self._motor.AP.smartEnergyThresholdSpeed, threshold
        )

    def set_coolstep_threshold_raw(self, threshold: int) -> None:
        self._require_feature("coolstep")
        self._check_range("threshold", threshold, 0, (1 << 31) - 1)
        self._coolstep_threshold_raw = threshold
        if threshold > 0:
            self._coolstep_enabled = True
        self._motor.set_axis_parameter(
            self._motor.AP.smartEnergyThresholdSpeed,
            threshold if self._coolstep_enabled else 0,
        )

    def set_coolstep_threshold_rps(self, rps: float) -> None:
        self._require_feature("coolstep")
        if rps < 0:
            raise ValueError("rps must be non-negative")
        self.set_coolstep_threshold_raw(self._rps_to_raw_speed(rps) if rps > 0 else 0)

    @staticmethod
    def _check_range(name: str, value: int, minimum: int, maximum: int) -> None:
        if not minimum <= value <= maximum:
            raise ValueError(f"{name} must be in [{minimum}, {maximum}]")

    # ------------------------------------------------------------------ #
    # Abstract hooks — subclasses MUST provide
    # ------------------------------------------------------------------ #

    @abstractmethod
    def _current_to_raw(self, current_mA: float) -> int: ...

    @abstractmethod
    def _raw_to_current(self, raw: int) -> float: ...

    @abstractmethod
    def _rps_to_raw_speed(self, rps: float) -> int: ...

    @abstractmethod
    def _raw_speed_to_rps(self, raw: int) -> float: ...

    @abstractmethod
    def _rps2_to_raw_accel(self, rps2: float) -> int: ...

    @abstractmethod
    def _set_run_current_raw(self, raw: int) -> None: ...

    @abstractmethod
    def _set_standstill_current_raw(self, raw: int) -> None: ...

    @abstractmethod
    def _set_speed_raw(self, raw: int) -> None: ...

    @abstractmethod
    def _set_accel_raw(self, raw: int) -> None: ...
