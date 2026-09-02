"""Tests for pure unit conversion helpers.

No hardware, no pytrinamic imports — just math.
"""

from __future__ import annotations

import math

import pytest

from trinamic_wrapper.conversions import (
    amax_to_rps2_tmc5160,
    cs_to_mA_rms,
    mA_rms_to_cs,
    revolutions_to_usteps,
    rps2_to_amax_tmc5160,
    rps_to_usteps_per_s,
    rps_to_vmax_tmc5160,
    usteps_per_s_to_rps,
    usteps_to_revolutions,
    vmax_to_rps_tmc5160,
)


# --------------------------------------------------------------------- #
# Current
# --------------------------------------------------------------------- #

class TestCurrentConversion:
    """Values cross-checked against the TMC5160 and TMC2660 datasheets."""

    # TMC5160-EVAL: R_sense=0.075, R_offset=0.02, V_fs=0.325 (VS=0)
    TMC5160_PARAMS = dict(
        sense_resistor_ohms=0.075, vfs=0.325,
        sense_resistor_offset_ohms=0.02,
    )
    # TMC2660-EVAL: R_sense=0.1, R_offset=0.03, V_fs=0.305 (VS=0)
    TMC2660_PARAMS = dict(
        sense_resistor_ohms=0.1, vfs=0.305,
        sense_resistor_offset_ohms=0.03,
    )

    def test_roundtrip_tmc5160_all_cs_values(self):
        """Every CS -> mA -> CS must be a fixed point."""
        for cs in range(32):
            mA = cs_to_mA_rms(cs, **self.TMC5160_PARAMS)
            cs_back = mA_rms_to_cs(mA, **self.TMC5160_PARAMS)
            assert cs_back == cs, f"CS={cs} -> {mA:.1f} mA -> CS={cs_back}"

    def test_roundtrip_tmc2660_all_cs_values(self):
        for cs in range(32):
            mA = cs_to_mA_rms(cs, **self.TMC2660_PARAMS)
            cs_back = mA_rms_to_cs(mA, **self.TMC2660_PARAMS)
            assert cs_back == cs

    def test_tmc5160_max_current_matches_datasheet(self):
        """At CS=31 the configured sense circuit gives ~2.42 A RMS."""
        mA = cs_to_mA_rms(31, **self.TMC5160_PARAMS)
        # (31+1)/32 * 0.325 / (0.075+0.02) / sqrt(2) * 1000
        expected = 32 / 32 * 0.325 / 0.095 / math.sqrt(2) * 1000
        assert mA == pytest.approx(expected, rel=1e-6)
        assert 2300 < mA < 2500  # ~2418 mA RMS. Sanity: datasheet ballpark.

    def test_tmc2660_max_current_matches_datasheet(self):
        mA = cs_to_mA_rms(31, **self.TMC2660_PARAMS)
        expected = 1 * 0.305 / 0.13 / math.sqrt(2) * 1000
        assert mA == pytest.approx(expected, rel=1e-6)

    def test_negative_current_raises(self):
        with pytest.raises(ValueError):
            mA_rms_to_cs(-1, **self.TMC5160_PARAMS)

    def test_zero_current_is_valid(self):
        """0 mA is allowed (motor off); may clamp upward if CS=0 already gives >0 mA."""
        cs = mA_rms_to_cs(0, **self.TMC5160_PARAMS, clamp=True)
        assert cs == 0

    def test_above_maximum_clamps_with_warning(self):
        with pytest.warns(UserWarning, match="clamped"):
            cs = mA_rms_to_cs(5000, **self.TMC5160_PARAMS)
        assert cs == 31

    def test_above_maximum_raises_without_clamp(self):
        with pytest.raises(ValueError, match="out of range"):
            mA_rms_to_cs(5000, **self.TMC5160_PARAMS, clamp=False)

    def test_reasonable_value_gives_reasonable_cs(self):
        """1000 mA on TMC5160-EVAL should give a mid-range CS."""
        cs = mA_rms_to_cs(1000, **self.TMC5160_PARAMS)
        assert 10 < cs < 20  # should land somewhere around CS=13

    def test_monotonic(self):
        """Higher mA never gives lower CS."""
        prev = -1
        for mA in range(0, 2000, 50):
            cs = mA_rms_to_cs(mA, **self.TMC5160_PARAMS)
            assert cs >= prev
            prev = cs


# --------------------------------------------------------------------- #
# TMC5160 velocity (VMAX)
# --------------------------------------------------------------------- #

class TestTmc5160Velocity:
    PARAMS = dict(full_steps_per_rev=200, clock_hz=16_000_000.0)

    def test_roundtrip(self):
        for rps in [0.1, 1.0, 5.0, 25.0, 100.0]:
            vmax = rps_to_vmax_tmc5160(rps, **self.PARAMS)
            rps_back = vmax_to_rps_tmc5160(vmax, **self.PARAMS)
            assert rps_back == pytest.approx(rps, rel=1e-4)

    def test_known_value(self):
        """
        1 rot/s with 200 full-steps and 256 μsteps at 16 MHz:
            ustep/s = 200 * 256 * 1 = 51200
            VMAX = 51200 * 2^24 / 16e6 = 53687.09...
        """
        vmax = rps_to_vmax_tmc5160(1.0, **self.PARAMS)
        expected = round(51200 * (2**24) / 16_000_000)
        assert vmax == expected

    def test_zero_velocity(self):
        assert rps_to_vmax_tmc5160(0.0, **self.PARAMS) == 0
        assert vmax_to_rps_tmc5160(0, **self.PARAMS) == 0.0

    def test_conversion_uses_configured_microstep_resolution(self):
        vmax = rps_to_vmax_tmc5160(
            1.0,
            **self.PARAMS,
            microsteps_per_fullstep=16,
        )
        expected = round(200 * 16 * (2**24) / 16_000_000)

        assert vmax == expected
        assert vmax_to_rps_tmc5160(
            vmax,
            **self.PARAMS,
            microsteps_per_fullstep=16,
        ) == pytest.approx(1.0, rel=1e-3)


class TestTmc5160Acceleration:
    PARAMS = dict(full_steps_per_rev=200, clock_hz=16_000_000.0)

    def test_roundtrip(self):
        for rps2 in [0.5, 5.0, 50.0, 500.0]:
            amax = rps2_to_amax_tmc5160(rps2, **self.PARAMS)
            rps2_back = amax_to_rps2_tmc5160(amax, **self.PARAMS)
            assert rps2_back == pytest.approx(rps2, rel=1e-3)

    def test_known_value(self):
        """
        1 rot/s^2: ustep/s^2 = 51200. AMAX = 51200 * 2^41 / (16e6)^2
        """
        amax = rps2_to_amax_tmc5160(1.0, **self.PARAMS)
        expected = round(51200 * (2**41) / (16_000_000 ** 2))
        assert amax == expected

    def test_conversion_uses_configured_microstep_resolution(self):
        amax = rps2_to_amax_tmc5160(
            1.0,
            **self.PARAMS,
            microsteps_per_fullstep=16,
        )
        expected = round(200 * 16 * (2**41) / (16_000_000 ** 2))

        assert amax == expected
        assert amax_to_rps2_tmc5160(
            amax,
            **self.PARAMS,
            microsteps_per_fullstep=16,
        ) == pytest.approx(1.0, rel=2e-2)


# --------------------------------------------------------------------- #
# TMC2660 (μsteps/s directly)
# --------------------------------------------------------------------- #

class TestTmc2660Velocity:
    def test_simple_multiply(self):
        # 1 rot/s at 200 fullsteps × 256 μsteps = 51200 μsteps/s
        v = rps_to_usteps_per_s(1.0, 200, 256)
        assert v == 51200

    def test_roundtrip_at_various_step_modes(self):
        for msteps in [1, 2, 4, 16, 256]:
            for rps in [0.5, 1.0, 10.0]:
                raw = rps_to_usteps_per_s(rps, 200, msteps)
                back = usteps_per_s_to_rps(raw, 200, msteps)
                assert back == pytest.approx(rps, rel=1e-3)

    def test_step_mode_matters(self):
        """Different microstep settings give different raw values."""
        assert (
            rps_to_usteps_per_s(1.0, 200, 256)
            > rps_to_usteps_per_s(1.0, 200, 16)
        )


# --------------------------------------------------------------------- #
# Position
# --------------------------------------------------------------------- #

class TestPosition:
    def test_integer_revolutions(self):
        assert revolutions_to_usteps(1.0, 200, 256) == 51200
        assert revolutions_to_usteps(5.0, 200, 256) == 51200 * 5

    def test_fractional_revolutions(self):
        assert revolutions_to_usteps(0.5, 200, 256) == 25600
        assert revolutions_to_usteps(0.25, 200, 256) == 12800

    def test_negative(self):
        assert revolutions_to_usteps(-1.0, 200, 256) == -51200

    def test_roundtrip(self):
        for rev in [0.0, 0.5, 1.0, -2.5, 10.125]:
            u = revolutions_to_usteps(rev, 200, 256)
            back = usteps_to_revolutions(u, 200, 256)
            assert back == pytest.approx(rev, abs=1 / 51200)  # one μstep
