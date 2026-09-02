"""Configuration dataclass and enums shared across chips."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum


class Direction(IntEnum):
    """Rotation direction.

    The sign is applied to the commanded velocity. Which physical direction
    a positive velocity produces depends on motor wiring and the SHAFT
    register bit.
    """
    CW = 1
    CCW = -1


class StepMode(IntEnum):
    """Microstepping resolution.

    The enum value is the microsteps-per-fullstep count accepted by the
    EvalSystem firmware's ``MicrostepResolution`` axis parameter.
    """
    FULLSTEP    = 1
    USTEP_2     = 2
    USTEP_4     = 4
    USTEP_8     = 8
    USTEP_16    = 16
    USTEP_32    = 32
    USTEP_64    = 64
    USTEP_128   = 128
    USTEP_256   = 256

    @property
    def microsteps_per_fullstep(self) -> int:
        """Actual microstep multiplier (1, 2, 4, …, 256)."""
        return int(self.value)


class RampMode(IntEnum):
    """Ramp generator mode (TMC5160 only).

    The TMC2660 has no internal ramp generator; the Landungsbrücke firmware
    emulates positioning and velocity ramps on its MCU side.
    """
    POSITION = 0    # go to XTARGET following A1/V1/AMAX/DMAX/D1
    VELOCITY_POS = 1  # reach VMAX in positive direction
    VELOCITY_NEG = 2  # reach VMAX in negative direction
    HOLD = 3        # no ramp, velocity stays


class Chip(str, Enum):
    """Supported Trinamic eval-board chip families."""

    TMC5160 = "TMC5160"
    TMC2660 = "TMC2660"


@dataclass(frozen=True)
class MotorConfig:
    """Mechanical and electrical configuration of the motor + driver combo.

    These values are required to convert between physical units (mA, rot/s,
    rot/s²) and the raw register / axis-parameter values the hardware wants.

    :param full_steps_per_rev: Full steps per mechanical revolution.
        Typical 1.8° motor = 200.
    :param sense_resistor_ohms: Value of the sense resistor on the eval
        board. TMC5160-EVAL = 0.075Ω; TMC2660-EVAL = 0.1Ω.
    :param vsense_high_sensitivity: If True, the chip's high-sensitivity
        sense voltage is used (smaller V_fs, so same CS value yields less
        current but finer resolution). Defaults to False = standard range.
        Only affects mA <-> CS conversion.
    :param clock_hz: TMC chip clock frequency. The TMC5160-EVAL /
        Landungsbruecke setup used by this wrapper runs at 16 MHz by
        default. Only used by TMC5160 to convert VMAX/AMAX.
    :param default_microsteps: Step mode used if none is explicitly set.
    :param max_current_mA_limit: Soft cap on run/hold current to prevent
        accidental overcurrent. Set to ``None`` to disable.
    """
    full_steps_per_rev: int = 200
    sense_resistor_ohms: float = 0.075          # TMC5160-EVAL default
    vsense_high_sensitivity: bool = False
    clock_hz: float = 16_000_000.0
    default_microsteps: StepMode = StepMode.USTEP_256
    max_current_mA_limit: float | None = 2000.0

    # Advanced: full-scale sense voltage for each vsense setting. The
    # datasheet values differ slightly per chip; the per-chip motor class
    # overrides these if needed.
    vfs_standard: float = 0.325   # TMC5160 default (VS=0)
    vfs_high_sens: float = 0.180  # TMC5160 high-sens (VS=1)

    def __post_init__(self) -> None:
        if self.full_steps_per_rev <= 0:
            raise ValueError("full_steps_per_rev must be positive")
        if self.sense_resistor_ohms <= 0:
            raise ValueError("sense_resistor_ohms must be positive")
        if self.clock_hz <= 0:
            raise ValueError("clock_hz must be positive")
