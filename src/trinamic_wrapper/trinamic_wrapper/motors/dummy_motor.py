"""In-memory StepperMotor implementation for development and tests."""

from __future__ import annotations

from ..config import Direction, MotorConfig, StepMode
from ..exceptions import OutOfRangeError


class DummyStepperMotor:
    """Small deterministic ``StepperMotor`` implementation."""

    SUPPORTED_FEATURES = frozenset({
        "stealthchop",
        "interpolation",
        "coolstep",
        "stallguard",
        "ramp_generator",
        "reference_switches",
    })

    def __init__(self, config: MotorConfig | None = None) -> None:
        self._config = config or MotorConfig()
        self._enabled = False
        self._run_current_mA = 0.0
        self._standstill_current_mA = 0.0
        self._speed_rps = 0.0
        self._acceleration_rps2 = 1.0
        self._step_mode = self._config.default_microsteps
        self._position_rot = 0.0
        self._actual_speed_rps = 0.0
        self._position_reached = True
        self._interpolation = False
        self._stealthchop = False
        self._stealthchop_threshold_rps: float | None = None
        self._stallguard_threshold = 0
        self._stallguard_enabled = True
        self._stallguard_filter_enabled = False
        self._chopper_mode = 0
        self._coolstep_enabled = False
        self._coolstep_threshold_rps = 0.0
        self._coolstep_threshold_raw = 0
        self._automatic_left_stop = False
        self._automatic_right_stop = False
        self._left_endstop = True
        self._right_endstop = True

    def set_chopper_mode(self, mode: int) -> None:
        if mode not in (0, 1):
            raise ValueError("chopper mode must be 0 (SpreadCycle) or 1 (Constant TOff)")
        self._chopper_mode = mode

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self.stop()
        self._enabled = False

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def set_run_current_mA(self, current_mA: float) -> None:
        self._check_current(current_mA)
        self._run_current_mA = current_mA

    def set_standstill_current_mA(self, current_mA: float) -> None:
        self._check_current(current_mA)
        self._standstill_current_mA = current_mA

    def get_run_current_mA(self) -> float:
        return self._run_current_mA

    def get_standstill_current_mA(self) -> float:
        return self._standstill_current_mA

    def set_speed_rps(self, speed_rps: float) -> None:
        if speed_rps < 0:
            raise OutOfRangeError("speed must be non-negative; use direction=CCW")
        self._speed_rps = speed_rps

    def set_acceleration_rps2(self, accel_rps2: float) -> None:
        if accel_rps2 <= 0:
            raise OutOfRangeError("acceleration must be positive")
        self._acceleration_rps2 = accel_rps2

    def set_step_mode(self, mode: StepMode) -> None:
        self._step_mode = StepMode(mode)

    def get_step_mode(self) -> StepMode:
        return self._step_mode

    def rotate(
        self,
        speed_rps: float | None = None,
        direction: Direction = Direction.CW,
    ) -> None:
        if speed_rps is not None:
            self.set_speed_rps(speed_rps)
        self._actual_speed_rps = self._speed_rps * int(direction)
        self._position_reached = False

    def rotate_by(
        self,
        revolutions: float,
        direction: Direction = Direction.CW,
    ) -> None:
        self._position_rot += abs(revolutions) * int(direction)
        self._actual_speed_rps = 0.0
        self._position_reached = True

    def wait_until_reached(self, timeout_s: float | None = None) -> bool:
        return self._position_reached

    def stop(self) -> None:
        self._actual_speed_rps = 0.0
        self._position_reached = True

    def get_actual_position_rot(self) -> float:
        return self._position_rot

    def get_actual_speed_rps(self) -> float:
        return self._actual_speed_rps

    def reset_position(self) -> None:
        self._position_rot = 0.0

    def set_interpolation(self, enabled: bool) -> None:
        self._interpolation = enabled

    def set_stealthchop(
        self,
        enabled: bool,
        threshold_rps: float | None = None,
    ) -> None:
        if threshold_rps is not None and threshold_rps <= 0:
            raise ValueError("threshold_rps must be positive")
        self._stealthchop = enabled
        self._stealthchop_threshold_rps = threshold_rps

    def set_stallguard_threshold(self, threshold: int) -> None:
        if not -64 <= threshold <= 63:
            raise ValueError("threshold must be in [-64, 63]")
        self._stallguard_threshold = threshold

    def set_stallguard_enabled(self, enabled: bool) -> None:
        self._stallguard_enabled = enabled

    def set_stallguard_filter_enabled(self, enabled: bool) -> None:
        self._stallguard_filter_enabled = enabled

    def configure_coolstep(
        self,
        *,
        min_current: int = 0,
        current_down_step: int = 0,
        current_up_step: int = 0,
        hysteresis: int = 0,
        threshold_speed: int = 0,
    ) -> None:
        self._check_int_range("min_current", min_current, 0, 1)
        self._check_int_range("current_down_step", current_down_step, 0, 3)
        self._check_int_range("current_up_step", current_up_step, 0, 3)
        self._check_int_range("hysteresis", hysteresis, 0, 15)
        self._check_int_range("threshold_speed", threshold_speed, 0, (1 << 31) - 1)
        self._coolstep_threshold_raw = threshold_speed
        self._coolstep_enabled = threshold_speed > 0

    def set_coolstep_enabled(self, enabled: bool) -> None:
        self._coolstep_enabled = enabled

    def set_coolstep_threshold_raw(self, threshold: int) -> None:
        self._check_int_range("threshold", threshold, 0, (1 << 31) - 1)
        self._coolstep_threshold_raw = threshold
        if threshold > 0:
            self._coolstep_enabled = True

    def set_coolstep_threshold_rps(self, rps: float) -> None:
        if rps < 0:
            raise ValueError("rps must be non-negative")
        self._coolstep_threshold_rps = rps
        self._coolstep_enabled = rps > 0

    def enable_reference_stops(
        self,
        *,
        left: bool = True,
        right: bool = True,
    ) -> None:
        self._automatic_left_stop = left
        self._automatic_right_stop = right

    def get_left_endstop(self) -> bool:
        return self._left_endstop

    def get_right_endstop(self) -> bool:
        return self._right_endstop

    def has_feature(self, name: str) -> bool:
        return name in self.SUPPORTED_FEATURES

    def _motion_units_per_fullstep(self) -> int:
        return self._step_mode.microsteps_per_fullstep

    def _check_current(self, current_mA: float) -> None:
        if current_mA < 0:
            raise OutOfRangeError("current must be non-negative")
        limit = self._config.max_current_mA_limit
        if limit is not None and current_mA > limit:
            raise OutOfRangeError(
                f"Requested {current_mA:.0f} mA exceeds configured safety "
                f"limit of {limit:.0f} mA."
            )

    @staticmethod
    def _check_int_range(name: str, value: int, minimum: int, maximum: int) -> None:
        if not minimum <= value <= maximum:
            raise ValueError(f"{name} must be in [{minimum}, {maximum}]")
