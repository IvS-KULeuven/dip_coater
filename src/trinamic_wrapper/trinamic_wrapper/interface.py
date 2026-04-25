"""Generic stepper-motor interface.

The :class:`StepperMotor` Protocol defines the contract every concrete
chip driver must satisfy. User code should type-hint against this rather
than against a specific chip so that swapping between TMC5160 and TMC2660
(or a mock) is a one-line change at construction time.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .config import Direction, StepMode


@runtime_checkable
class StepperMotor(Protocol):
    """Chip-agnostic stepper-motor interface."""

    # ---- enable / disable -------------------------------------------------

    def enable(self) -> None:
        """Energise the coils. Motor holds position (at standstill current)."""

    def disable(self) -> None:
        """De-energise the coils. Motor can be turned by hand."""

    @property
    def is_enabled(self) -> bool: ...

    # ---- current ----------------------------------------------------------

    def set_run_current_mA(self, current_mA: float) -> None:
        """Set the RMS current used while the motor is moving."""

    def set_standstill_current_mA(self, current_mA: float) -> None:
        """Set the RMS current used at standstill (hold current)."""

    def get_run_current_mA(self) -> float: ...
    def get_standstill_current_mA(self) -> float: ...

    # ---- motion parameters ------------------------------------------------

    def set_speed_rps(self, speed_rps: float) -> None:
        """Set the maximum rotational speed, in revolutions per second."""

    def set_acceleration_rps2(self, accel_rps2: float) -> None:
        """Set the rotational acceleration, in rev/s²."""

    def set_step_mode(self, mode: StepMode) -> None:
        """Set the microstepping resolution."""

    def get_step_mode(self) -> StepMode: ...

    # ---- motion commands --------------------------------------------------

    def rotate(
        self,
        speed_rps: float | None = None,
        direction: Direction = Direction.CW,
    ) -> None:
        """Start continuous rotation.

        :param speed_rps: Optional per-call speed override. If ``None``,
            the previously configured speed is used.
        :param direction: CW or CCW.
        """

    def rotate_by(
        self,
        revolutions: float,
        direction: Direction = Direction.CW,
    ) -> None:
        """Rotate a fixed (signed if desired) amount and then stop.

        This is a non-blocking *command* — it returns as soon as the target
        has been loaded. Use :meth:`wait_until_reached` to block until the
        move finishes.
        """

    def wait_until_reached(self, timeout_s: float | None = None) -> bool:
        """Block until the motor reports position-reached (or timeout).

        :returns: ``True`` if the target was reached, ``False`` on timeout.
        """

    def stop(self) -> None:
        """Stop the motor immediately (using the configured deceleration)."""

    # ---- status -----------------------------------------------------------

    def get_actual_position_rot(self) -> float:
        """Current position in revolutions (since last position reset)."""

    def get_actual_speed_rps(self) -> float:
        """Current measured speed in revolutions per second."""

    def reset_position(self) -> None:
        """Define the current position as zero."""

    # ---- advanced / chip-specific knobs -----------------------------------
    #
    # These are on the Protocol so generic code can *ask* for them, but the
    # concrete TMC2660Motor raises UnsupportedFeatureError from the ones it
    # doesn't have (StealthChop). Use hasattr-style feature discovery via
    # the has_feature() method if you want to probe.

    def set_interpolation(self, enabled: bool) -> None:
        """Enable 256-microstep interpolation from the current step mode."""

    def set_chopper_mode(self, mode: int) -> None:
        """Set chopper mode: 0 = SpreadCycle, 1 = classic constant TOff."""

    def set_stealthchop(
        self,
        enabled: bool,
        threshold_rps: float | None = None,
    ) -> None:
        """Enable/disable StealthChop silent mode (TMC5160 only).

        :param threshold_rps: If given, speed above which the chip falls
            back to SpreadCycle. Below this speed it stays in StealthChop.
        """

    def set_stallguard_enabled(self, enabled: bool) -> None:
        """Enable or disable StallGuard2 using the cached threshold."""

    def set_stallguard_filter_enabled(self, enabled: bool) -> None:
        """Enable or disable the hardware StallGuard2 filter."""

    def set_stallguard_threshold(self, threshold: int) -> None:
        """Set the StallGuard2 threshold."""

    def configure_coolstep(
        self,
        *,
        min_current: int = 0,
        current_down_step: int = 0,
        current_up_step: int = 0,
        hysteresis: int = 0,
        threshold_speed: int = 0,
    ) -> None:
        """Configure CoolStep axis parameters in PyTrinamic raw units."""

    def set_coolstep_enabled(self, enabled: bool) -> None:
        """Enable or disable CoolStep using the cached raw threshold."""

    def set_coolstep_threshold_raw(self, threshold: int) -> None:
        """Set the raw PyTrinamic smartEnergyThresholdSpeed axis parameter."""

    def set_coolstep_threshold_rps(self, rps: float) -> None:
        """Set the CoolStep threshold in revolutions per second."""

    def has_feature(self, name: str) -> bool:
        """Check whether the chip supports a named optional feature.

        Valid names include: ``"stealthchop"``, ``"interpolation"``,
        ``"coolstep"``, ``"stallguard"``, ``"ramp_generator"``.
        """
