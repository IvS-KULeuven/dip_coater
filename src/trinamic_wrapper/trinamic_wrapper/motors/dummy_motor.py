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
        self._coolstep_threshold_rps = 0.0

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

    def set_coolstep_threshold_rps(self, rps: float) -> None:
        if rps < 0:
            raise ValueError("rps must be non-negative")
        self._coolstep_threshold_rps = rps

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
