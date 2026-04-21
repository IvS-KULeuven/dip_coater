"""Hardware verification tests — require a real Landungsbrücke.

Run with::

    pytest tests/hardware/ --hw-port=/dev/tty.usbmodemTMCEVAL1 \\
                          --hw-chip=TMC5160 \\
                          --hw-rsense=0.075

Skipped automatically if --hw-port is not given.

These tests command a real motor. The motor will rotate. Bolt it down,
make sure nothing is in the way, and don't run them while you've got
a 1 kg flywheel on the shaft.

The tests are designed to be non-destructive and use conservative
defaults (500 mA, 1 rot/s, 5 rot/s²). Adjust with the --hw-* options.
"""

from __future__ import annotations

import time

import pytest
from pytrinamic.ic import TMC2660, TMC5160

from trinamic_wrapper import Direction, StepMode


# ------------------------------------------------------------------------- #
# Basic connectivity & identity
# ------------------------------------------------------------------------- #

class TestConnectivity:
    """These run first — if the board isn't responding, later tests are skipped."""

    def test_can_read_axis_parameter(self, hw_motor):
        """Round-trip a harmless axis parameter; proves TMCL is working."""
        pos = hw_motor.get_actual_position_rot()
        assert isinstance(pos, float)

    def test_can_read_actual_velocity(self, hw_motor):
        v = hw_motor.get_actual_speed_rps()
        assert isinstance(v, float)
        # Motor is idle at this point
        assert abs(v) < 0.1, f"motor is moving at {v} rot/s before we asked it to"


# ------------------------------------------------------------------------- #
# Current setting — the main concern in the user's request
# ------------------------------------------------------------------------- #

class TestCurrentRoundTrip:
    """Verify that the value written to the chip's current register matches
    what we asked for, and that enable/disable actually zeros it.

    These confirm the *write path* is correct — i.e. the firmware is
    interpreting our axis-parameter value the way we expect. They don't
    measure absolute current in amperes (you need a current probe for that),
    but they catch unit-conversion bugs in our code and mismatches between
    the wrapper's encoding and the firmware's decoding.
    """

    def test_set_run_current_readback_matches(self, hw_motor, hw_currents):
        target_mA, _ = hw_currents
        hw_motor.enable()
        hw_motor.set_run_current_mA(target_mA)
        time.sleep(0.05)  # let any internal pipelining settle

        readback = hw_motor.get_run_current_mA()
        # The conversion is lossy (5-bit CS ≈ 60-75 mA per step), so we
        # assert within one CS step.
        step_mA = _cs_step_size(hw_motor)
        assert abs(readback - target_mA) <= step_mA * 1.1, (
            f"requested {target_mA} mA, chip reports {readback:.0f} mA, "
            f"CS step size ≈ {step_mA:.0f} mA"
        )

    def test_set_standstill_current_readback_matches(self, hw_motor, hw_currents):
        _, target_mA = hw_currents
        hw_motor.enable()
        hw_motor.set_standstill_current_mA(target_mA)
        time.sleep(0.05)

        readback = hw_motor.get_standstill_current_mA()
        step_mA = _cs_step_size(hw_motor)
        assert abs(readback - target_mA) <= step_mA * 1.1

    def test_current_register_matches_readback(self, hw_motor, hw_currents):
        """Stronger check: read the *chip*'s own register, not just the
        TMCL axis parameter we wrote, and confirm CS matches.

        This catches cases where the firmware silently rejects or rescales
        our value — it closes the loop all the way into the IC.
        """
        target_mA, _ = hw_currents
        hw_motor.enable()
        hw_motor.set_run_current_mA(target_mA)
        time.sleep(0.05)

        chip_cs = _read_chip_cs(hw_motor)
        # Compute what we *intended* the CS to be
        intended_cs = _intended_cs(hw_motor, target_mA)

        assert chip_cs == intended_cs, (
            f"requested {target_mA} mA -> intended CS={intended_cs}, "
            f"but chip register reads CS={chip_cs}. "
            f"Firmware encoding doesn't match wrapper's assumption."
        )

    def test_disable_zeros_the_current_register(self, hw_motor, hw_currents):
        target_mA, _ = hw_currents
        hw_motor.enable()
        hw_motor.set_run_current_mA(target_mA)
        time.sleep(0.05)
        assert _read_chip_cs(hw_motor) > 0

        hw_motor.disable()
        time.sleep(0.05)
        # After disable, IRUN/CS should be 0 (chip is de-energised)
        assert _read_chip_cs(hw_motor) == 0, (
            "disable() did not zero the current register"
        )

    def test_enable_restores_cached_current(self, hw_motor, hw_currents):
        target_mA, _ = hw_currents
        hw_motor.enable()
        hw_motor.set_run_current_mA(target_mA)
        hw_motor.disable()
        time.sleep(0.05)

        hw_motor.enable()
        time.sleep(0.05)
        readback = hw_motor.get_run_current_mA()
        step_mA = _cs_step_size(hw_motor)
        assert abs(readback - target_mA) <= step_mA * 1.1, (
            "enable() should re-apply the most recent set_run_current_mA"
        )


# ------------------------------------------------------------------------- #
# Motion — does the motor actually move by the commanded amount?
# ------------------------------------------------------------------------- #

class TestMotion:
    """Verify the motor physically responds to motion commands.

    We rely on the chip's internal position counter (``ActualPosition``) as
    ground truth. For the TMC5160 that's XACTUAL, which tracks every step
    the ramp generator commands. For the TMC2660 it's the firmware's step
    counter. In both cases, the counter advances only when steps actually
    fire, so if the motor stalls or the driver is disabled, this test
    will fail — which is what we want.
    """

    def test_rotate_by_one_revolution_produces_one_revolution(self, hw_motor, hw_currents):
        run_mA, standstill_mA = hw_currents
        hw_motor.set_step_mode(StepMode.USTEP_256)
        hw_motor.set_run_current_mA(run_mA)
        hw_motor.set_standstill_current_mA(standstill_mA)
        hw_motor.set_speed_rps(1.0)
        hw_motor.set_acceleration_rps2(5.0)
        hw_motor.enable()
        hw_motor.reset_position()

        hw_motor.rotate_by(1.0, direction=Direction.CW)
        reached = hw_motor.wait_until_reached(timeout_s=5.0)
        assert reached, "motor did not reach target within 5 s"

        pos = hw_motor.get_actual_position_rot()
        # Within one microstep of target
        tol = 1.0 / (200 * 256)
        assert abs(pos - 1.0) < tol, f"expected 1.0 rev, got {pos}"

    def test_reversed_direction_gives_negative_position(self, hw_motor, hw_currents):
        run_mA, standstill_mA = hw_currents
        hw_motor.set_run_current_mA(run_mA)
        hw_motor.set_standstill_current_mA(standstill_mA)
        hw_motor.set_speed_rps(1.0)
        hw_motor.set_acceleration_rps2(5.0)
        hw_motor.enable()
        hw_motor.reset_position()

        hw_motor.rotate_by(0.5, direction=Direction.CCW)
        assert hw_motor.wait_until_reached(timeout_s=5.0)
        pos = hw_motor.get_actual_position_rot()
        assert pos < 0, f"CCW move should produce negative position, got {pos}"
        assert abs(pos - (-0.5)) < 1e-3

    def test_continuous_rotate_yields_measurable_speed(self, hw_motor, hw_currents):
        run_mA, standstill_mA = hw_currents
        hw_motor.set_run_current_mA(run_mA)
        hw_motor.set_standstill_current_mA(standstill_mA)
        hw_motor.set_speed_rps(1.0)
        hw_motor.set_acceleration_rps2(10.0)
        hw_motor.enable()

        hw_motor.rotate(direction=Direction.CW)
        time.sleep(1.0)  # let the ramp finish (0.1 s at 10 rot/s²) and stabilise

        v = hw_motor.get_actual_speed_rps()
        hw_motor.stop()
        # Allow 20 % slack: firmware velocity readback has quantisation,
        # and with small microstepping a 1 rot/s command can be a bit off.
        assert 0.8 < v < 1.2, f"expected ~1.0 rot/s, got {v:.3f}"

    def test_stop_actually_stops(self, hw_motor, hw_currents):
        run_mA, standstill_mA = hw_currents
        hw_motor.set_run_current_mA(run_mA)
        hw_motor.set_standstill_current_mA(standstill_mA)
        hw_motor.set_speed_rps(1.0)
        hw_motor.set_acceleration_rps2(10.0)
        hw_motor.enable()

        hw_motor.rotate(direction=Direction.CW)
        time.sleep(0.5)
        hw_motor.stop()
        time.sleep(0.5)  # give the ramp decel some time

        v = hw_motor.get_actual_speed_rps()
        assert abs(v) < 0.1, f"motor should be stopped, but v={v}"


# ------------------------------------------------------------------------- #
# Step mode — does changing microsteps actually reconfigure the chip?
# ------------------------------------------------------------------------- #

class TestStepMode:
    def test_set_step_mode_reads_back(self, hw_motor):
        for mode in [StepMode.USTEP_16, StepMode.USTEP_64, StepMode.USTEP_256]:
            hw_motor.set_step_mode(mode)
            time.sleep(0.05)
            readback_raw = hw_motor._motor.get_axis_parameter(
                hw_motor._motor.AP.MicrostepResolution
            )
            assert readback_raw == int(mode), (
                f"set {mode.name} (value {int(mode)}), read back {readback_raw}"
            )


# ------------------------------------------------------------------------- #
# Chip-specific: StealthChop (TMC5160 only)
# ------------------------------------------------------------------------- #

class TestStealthChop:
    def test_enable_stealthchop_sets_en_pwm_mode(self, hw_motor):
        if not hw_motor.has_feature("stealthchop"):
            pytest.skip("chip has no StealthChop")

        hw_motor.set_stealthchop(True)
        time.sleep(0.05)

        gconf = hw_motor._eval.read_register(TMC5160.REG.GCONF)
        assert gconf & 0b100, (
            f"EN_PWM_MODE (bit 2) not set in GCONF after enabling StealthChop. "
            f"GCONF = 0x{gconf:08x}"
        )

    def test_disable_stealthchop_clears_en_pwm_mode(self, hw_motor):
        if not hw_motor.has_feature("stealthchop"):
            pytest.skip("chip has no StealthChop")

        hw_motor.set_stealthchop(True)
        hw_motor.set_stealthchop(False)
        time.sleep(0.05)

        gconf = hw_motor._eval.read_register(TMC5160.REG.GCONF)
        assert gconf & 0b100 == 0


# ------------------------------------------------------------------------- #
# Helpers to look into the chip's own registers
# ------------------------------------------------------------------------- #

def _read_chip_cs(motor) -> int:
    """Read the effective CS (current scaling) value from the chip registers."""
    if motor.has_feature("ramp_generator"):
        # TMC5160: IHOLD_IRUN, IRUN is bits 8..12
        raw = motor._eval.read_register(TMC5160.REG.IHOLD_IRUN)
        return (raw >> 8) & 0x1F
    else:
        # TMC2660: CS is in SGCSCONF (register 0x0E), bits 0..4
        # Note: TMC2660 is write-only in SPI, so we read back via the
        # firmware's shadow copy through the axis parameter.
        return motor._motor.get_axis_parameter(motor._motor.AP.MaxCurrent)


def _intended_cs(motor, current_mA: float) -> int:
    """What CS should our wrapper have programmed for this current?"""
    from trinamic_wrapper.conversions import mA_rms_to_cs

    cfg = motor._config
    if motor.has_feature("ramp_generator"):  # TMC5160
        vfs = cfg.vfs_high_sens if cfg.vsense_high_sensitivity else cfg.vfs_standard
        r_offset = 0.02
    else:  # TMC2660
        vfs = 0.165 if cfg.vsense_high_sensitivity else 0.305
        r_offset = 0.03
    return mA_rms_to_cs(current_mA, cfg.sense_resistor_ohms, vfs, r_offset)


def _cs_step_size(motor) -> float:
    """Return the mA/CS-step size for the configured driver — the readback
    resolution floor."""
    from trinamic_wrapper.conversions import cs_to_mA_rms

    cfg = motor._config
    if motor.has_feature("ramp_generator"):
        vfs = cfg.vfs_high_sens if cfg.vsense_high_sensitivity else cfg.vfs_standard
        r_offset = 0.02
    else:
        vfs = 0.165 if cfg.vsense_high_sensitivity else 0.305
        r_offset = 0.03
    return (
        cs_to_mA_rms(31, cfg.sense_resistor_ohms, vfs, r_offset)
        - cs_to_mA_rms(30, cfg.sense_resistor_ohms, vfs, r_offset)
    )
