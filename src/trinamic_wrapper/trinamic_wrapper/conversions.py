"""Pure unit-conversion helpers (mA ↔ CS, rot/s ↔ VMAX, …).

Kept free of any pytrinamic imports so they can be unit-tested without
touching hardware.

References
----------
- TMC5160 datasheet, section 9, "Motor Current Control" and section 6
  "Velocity Ramp Generator"
- TMC2660 datasheet, section 5.1 "Motor Current Control"
"""

from __future__ import annotations

import math
import warnings


# --------------------------------------------------------------------------- #
# Current: mA <-> 5-bit current scaler (CS / IRUN)
# --------------------------------------------------------------------------- #

def mA_rms_to_cs(
    current_mA: float,
    sense_resistor_ohms: float,
    vfs: float,
    sense_resistor_offset_ohms: float,
    *,
    clamp: bool = True,
) -> int:
    """Convert an RMS current in mA to the 5-bit CS / IRUN register value.

    The datasheet formula (rearranged) is::

        CS = round( (I_rms * sqrt(2) * (R_sense + R_offset)) / V_fs * 32 - 1 )

    :param current_mA: Target RMS current in milliamps.
    :param sense_resistor_ohms: Physical sense-resistor value. 0.075 Ω on
        TMC5160-EVAL, 0.1 Ω on TMC2660-EVAL.
    :param vfs: Full-scale sense voltage. 0.325 V typical for standard
        range, 0.180 V (5160) / 0.165 V (2660) for high-sensitivity range.
    :param sense_resistor_offset_ohms: Parasitic resistance added to
        R_sense in the datasheet formula — 0.02 Ω for TMC5160, 0.03 Ω for
        TMC2660 (from the respective datasheets).
    :param clamp: If True, clamp result to [0, 31] and emit a warning on
        clamp. If False, raise :class:`ValueError` on out-of-range.
    :returns: Integer CS value in [0, 31].
    """
    if current_mA < 0:
        raise ValueError("current_mA must be non-negative")

    # 0 mA is a legitimate "off" request — return CS=0 without warning.
    # (Strictly, CS=0 gives a small non-zero current ≈ V_fs/(32·R_total·√2),
    # but callers treat 0 as "off" and rely on driver enable/disable to
    # actually kill current.)
    if current_mA == 0:
        return 0

    i_amps = current_mA / 1000.0
    r_total = sense_resistor_ohms + sense_resistor_offset_ohms
    # Solve I_rms = (CS+1)/32 * V_fs / R_total / sqrt(2)  for CS
    cs_float = (i_amps * math.sqrt(2) * r_total) / vfs * 32 - 1
    cs_int = int(round(cs_float))

    if 0 <= cs_int <= 31:
        return cs_int

    if not clamp:
        raise ValueError(
            f"{current_mA:.1f} mA maps to CS={cs_int}, which is out of "
            f"range [0,31] for R_sense={sense_resistor_ohms}Ω, V_fs={vfs}V"
        )

    clamped = max(0, min(31, cs_int))
    warnings.warn(
        f"current {current_mA:.1f} mA clamped: CS {cs_int} -> {clamped} "
        f"(~{cs_to_mA_rms(clamped, sense_resistor_ohms, vfs, sense_resistor_offset_ohms):.0f} mA)",
        stacklevel=2,
    )
    return clamped


def cs_to_mA_rms(
    cs: int,
    sense_resistor_ohms: float,
    vfs: float,
    sense_resistor_offset_ohms: float,
) -> float:
    """Inverse of :func:`mA_rms_to_cs`.

    :returns: RMS current in mA that corresponds to the given CS value.
    """
    if not 0 <= cs <= 31:
        raise ValueError(f"cs must be in [0, 31], got {cs}")
    r_total = sense_resistor_ohms + sense_resistor_offset_ohms
    i_amps = (cs + 1) / 32.0 * vfs / r_total / math.sqrt(2)
    return i_amps * 1000.0


# --------------------------------------------------------------------------- #
# TMC5160 velocity: rot/s <-> VMAX (internal units)
# --------------------------------------------------------------------------- #
#
# Datasheet formula:
#     v [Hz, microsteps/s] = VMAX * f_clk / 2^24
# With 256 usteps/fullstep and N full-steps/rev:
#     v [rot/s] = VMAX * f_clk / (2^24 * 256 * N)
# -> VMAX = v_rot_s * 256 * N * 2^24 / f_clk
# Note: microsteps/s is always measured at the native 256-microstep
# resolution, independent of MRES. This is why we use 256 and not the
# current step_mode multiplier.

_TMC5160_USTEPS_NATIVE = 256

def rps_to_vmax_tmc5160(
    rps: float,
    full_steps_per_rev: int,
    clock_hz: float,
) -> int:
    """Convert rev/s to TMC5160 VMAX register value."""
    ustep_per_s = rps * _TMC5160_USTEPS_NATIVE * full_steps_per_rev
    vmax = ustep_per_s * (1 << 24) / clock_hz
    return int(round(vmax))


def vmax_to_rps_tmc5160(
    vmax: int,
    full_steps_per_rev: int,
    clock_hz: float,
) -> float:
    """Inverse of :func:`rps_to_vmax_tmc5160`."""
    ustep_per_s = vmax * clock_hz / (1 << 24)
    return ustep_per_s / (_TMC5160_USTEPS_NATIVE * full_steps_per_rev)


# --------------------------------------------------------------------------- #
# TMC5160 acceleration: rot/s^2 <-> AMAX
# --------------------------------------------------------------------------- #
#
# Datasheet: a [usteps/s^2] = AMAX * f_clk^2 / (2^41)
# -> AMAX = a_rot_s2 * 256 * N * 2^41 / f_clk^2

def rps2_to_amax_tmc5160(
    rps2: float,
    full_steps_per_rev: int,
    clock_hz: float,
) -> int:
    """Convert rev/s² to TMC5160 AMAX register value."""
    ustep_per_s2 = rps2 * _TMC5160_USTEPS_NATIVE * full_steps_per_rev
    amax = ustep_per_s2 * (1 << 41) / (clock_hz ** 2)
    return int(round(amax))


def amax_to_rps2_tmc5160(
    amax: int,
    full_steps_per_rev: int,
    clock_hz: float,
) -> float:
    """Inverse of :func:`rps2_to_amax_tmc5160`."""
    ustep_per_s2 = amax * (clock_hz ** 2) / (1 << 41)
    return ustep_per_s2 / (_TMC5160_USTEPS_NATIVE * full_steps_per_rev)


# --------------------------------------------------------------------------- #
# TMC2660 velocity: rot/s <-> μsteps/s
# --------------------------------------------------------------------------- #
#
# The TMC2660 has no internal ramp generator. The Landungsbrücke firmware
# emulates one and accepts MaxVelocity / MaxAcceleration in μsteps/s and
# μsteps/s² respectively (at the configured microstep resolution).

def rps_to_usteps_per_s(
    rps: float,
    full_steps_per_rev: int,
    microsteps_per_fullstep: int,
) -> int:
    """Convert rev/s to μsteps/s at the given microstep resolution."""
    return int(round(rps * full_steps_per_rev * microsteps_per_fullstep))


def usteps_per_s_to_rps(
    usteps_per_s: int,
    full_steps_per_rev: int,
    microsteps_per_fullstep: int,
) -> float:
    """Inverse of :func:`rps_to_usteps_per_s`."""
    return usteps_per_s / (full_steps_per_rev * microsteps_per_fullstep)


# --------------------------------------------------------------------------- #
# Position helpers
# --------------------------------------------------------------------------- #

def revolutions_to_usteps(
    revolutions: float,
    full_steps_per_rev: int,
    microsteps_per_fullstep: int,
) -> int:
    """Convert (possibly fractional) revolutions to an integer μstep count."""
    return int(round(revolutions * full_steps_per_rev * microsteps_per_fullstep))


def usteps_to_revolutions(
    usteps: int,
    full_steps_per_rev: int,
    microsteps_per_fullstep: int,
) -> float:
    """Inverse of :func:`revolutions_to_usteps`."""
    return usteps / (full_steps_per_rev * microsteps_per_fullstep)
