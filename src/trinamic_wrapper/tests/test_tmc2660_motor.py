"""Tests for TMC2660Motor — runs against a FakeConnection, no hardware."""

from __future__ import annotations

import pytest
from pytrinamic.evalboards import TMC2660_eval

from tests.fake_connection import FakeConnection
from trinamic_wrapper import (
    Direction,
    MotorConfig,
    StepMode,
    TMC2660Motor,
)
from trinamic_wrapper.exceptions import (
    OutOfRangeError,
    UnsupportedFeatureError,
)


@pytest.fixture
def setup():
    conn = FakeConnection()
    board = TMC2660_eval(conn, module_id=1)
    config = MotorConfig(
        full_steps_per_rev=200,
        sense_resistor_ohms=0.1,          # TMC2660-EVAL
        clock_hz=16_000_000.0,
        default_microsteps=StepMode.USTEP_256,
    )
    motor = TMC2660Motor(board, config)
    conn.calls.clear()
    return motor, conn, board


class TestFeatureDiscovery:
    def test_does_not_have_stealthchop(self, setup):
        motor, *_ = setup
        assert not motor.has_feature("stealthchop")

    def test_does_not_have_ramp_generator(self, setup):
        """TMC2660 is driver-only — ramp is firmware-emulated, not on-chip."""
        motor, *_ = setup
        assert not motor.has_feature("ramp_generator")

    def test_has_interpolation(self, setup):
        motor, *_ = setup
        assert motor.has_feature("interpolation")

    def test_has_stallguard(self, setup):
        motor, *_ = setup
        assert motor.has_feature("stallguard")


class TestCurrent:
    def test_set_run_current_writes_cs_directly(self, setup):
        motor, conn, board = setup
        motor.enable()
        motor.set_run_current_mA(1000)
        cs = conn.get_ap(board.motors[0].AP.MaxCurrent)
        # unlike 5160, value *is* the CS field, 0..31
        assert 0 < cs < 32

    def test_roundtrip_readback(self, setup):
        motor, *_ = setup
        motor.enable()
        motor.set_run_current_mA(1000)
        got = motor.get_run_current_mA()
        # Step size on TMC2660 is ~60 mA/CS; allow 80 mA slack
        assert abs(got - 1000) < 80

    def test_cs_value_stays_in_5_bit_range(self, setup):
        motor, conn, board = setup
        motor.enable()
        for mA in [100, 500, 1000, 1500, 1900]:
            motor.set_run_current_mA(mA)
            cs = conn.get_ap(board.motors[0].AP.MaxCurrent)
            assert 0 <= cs <= 31

    def test_soft_limit_rejects_excessive_current(self, setup):
        motor, *_ = setup
        with pytest.raises(OutOfRangeError):
            motor.set_run_current_mA(3000)

    def test_vsense_set_on_construction(self, setup):
        motor, conn, board = setup
        # When vsense_high_sensitivity=False (default), VSense AP should be 0
        assert conn.get_ap(board.motors[0].AP.VSense) == 0

    def test_high_sensitivity_config_sets_vsense(self):
        conn = FakeConnection()
        board = TMC2660_eval(conn, module_id=1)
        config = MotorConfig(
            sense_resistor_ohms=0.1,
            vsense_high_sensitivity=True,
        )
        TMC2660Motor(board, config)
        assert conn.get_ap(board.motors[0].AP.VSense) == 1


class TestMotion:
    def test_set_speed_uses_usteps_per_second(self, setup):
        motor, conn, board = setup
        motor.set_speed_rps(1.0)
        raw = conn.get_ap(board.motors[0].AP.MaxVelocity)
        # At USTEP_256: 1 rot/s = 200 * 256 = 51200 μsteps/s
        assert raw == 51200

    def test_set_speed_scales_with_step_mode(self, setup):
        motor, conn, board = setup
        motor.set_step_mode(StepMode.USTEP_16)
        motor.set_speed_rps(1.0)
        raw = conn.get_ap(board.motors[0].AP.MaxVelocity)
        # 1 rot/s at USTEP_16 = 200 * 16 = 3200 μsteps/s
        assert raw == 3200

    def test_rotate_by_correct_usteps(self, setup):
        motor, conn, _ = setup
        motor.set_step_mode(StepMode.USTEP_256)
        motor.rotate_by(3.0, direction=Direction.CW)
        (axis, delta, _mid) = conn.last("move_by")
        assert axis == 0
        assert delta == 3 * 200 * 256  # 153600

    def test_rotate_negative_direction(self, setup):
        motor, conn, _ = setup
        motor.rotate(speed_rps=2.0, direction=Direction.CCW)
        (_a, v, _m) = conn.last("rotate")
        assert v < 0
        assert abs(v) == 2 * 200 * 256  # 102400

    def test_stop_sends_stop(self, setup):
        motor, conn, _ = setup
        motor.stop()
        assert conn.last("stop") is not None


class TestStepMode:
    def test_set_step_mode_writes_mres_ap(self, setup):
        motor, conn, board = setup
        motor.set_step_mode(StepMode.USTEP_8)
        assert conn.get_ap(board.motors[0].AP.MicrostepResolution) == int(
            StepMode.USTEP_8
        )


class TestUnsupportedFeatures:
    def test_stealthchop_raises_unsupported(self, setup):
        motor, *_ = setup
        with pytest.raises(UnsupportedFeatureError, match="StealthChop"):
            motor.set_stealthchop(True)

    def test_has_feature_stealthchop_returns_false(self, setup):
        motor, *_ = setup
        assert not motor.has_feature("stealthchop")

    def test_portable_code_can_fall_back(self, setup):
        """Demonstrate the feature-discovery pattern."""
        motor, *_ = setup
        if motor.has_feature("stealthchop"):
            motor.set_stealthchop(True)  # not executed for 2660
            executed = True
        else:
            executed = False
        assert not executed


class TestInterpolation:
    def test_set_interpolation_writes_intpol_ap(self, setup):
        motor, conn, board = setup
        motor.set_interpolation(True)
        assert conn.get_ap(board.motors[0].AP.Intpol) == 1
        motor.set_interpolation(False)
        assert conn.get_ap(board.motors[0].AP.Intpol) == 0


class TestStallGuard:
    def test_set_sgt_valid_range(self, setup):
        motor, conn, board = setup
        motor.set_stallguard_threshold(5)
        assert conn.get_ap(board.motors[0].AP.SG2Threshold) == 5

    def test_set_sgt_rejects_out_of_range(self, setup):
        motor, *_ = setup
        with pytest.raises(ValueError):
            motor.set_stallguard_threshold(200)
