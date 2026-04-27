"""Tests for TMC5160Motor — runs against a FakeConnection, no hardware."""

from __future__ import annotations

import pytest
from pytrinamic.evalboards import TMC5160_eval
from pytrinamic.ic import TMC5160

from tests.fake_connection import FakeConnection
from trinamic_wrapper import (
    Direction,
    MotorConfig,
    StepMode,
    TMC5160Motor,
)
from trinamic_wrapper.exceptions import OutOfRangeError


@pytest.fixture
def setup():
    """Create a TMC5160Motor with a FakeConnection; return (motor, conn, board)."""
    conn = FakeConnection()
    board = TMC5160_eval(conn, module_id=1)
    config = MotorConfig(
        full_steps_per_rev=200,
        sense_resistor_ohms=0.075,
        clock_hz=16_000_000.0,
        default_microsteps=StepMode.USTEP_256,
    )
    motor = TMC5160Motor(board, config)
    # clear the ctor-time calls so tests don't see them
    conn.calls.clear()
    return motor, conn, board


class TestFeatureDiscovery:
    def test_has_stealthchop(self, setup):
        motor, *_ = setup
        assert motor.has_feature("stealthchop")

    def test_has_interpolation(self, setup):
        motor, *_ = setup
        assert motor.has_feature("interpolation")

    def test_has_ramp_generator(self, setup):
        motor, *_ = setup
        assert motor.has_feature("ramp_generator")

    def test_has_reference_switches(self, setup):
        motor, *_ = setup
        assert motor.has_feature("reference_switches")

    def test_does_not_have_nonsense_feature(self, setup):
        motor, *_ = setup
        assert not motor.has_feature("banana_mode")


class TestCurrent:
    def test_set_run_current_writes_max_current_ap(self, setup):
        motor, conn, board = setup
        motor.enable()
        motor.set_run_current_mA(1000)
        # Should have set AP 6 (MaxCurrent) with the direct CS value.
        (ap_type, axis, value, _mod) = conn.last("set_ap")
        assert ap_type == board.motors[0].AP.MaxCurrent
        assert axis == 0
        # CS for 1 A on the 5160-EVAL is around 12-13.
        assert 10 <= value <= 20

    def test_set_standstill_current_writes_standby_current_ap(self, setup):
        motor, conn, board = setup
        motor.enable()
        motor.set_standstill_current_mA(300)
        # find set_ap for StandbyCurrent
        hits = [c for c in conn.calls if c[0] == "set_ap"
                and c[1][0] == board.motors[0].AP.StandbyCurrent]
        assert len(hits) >= 1

    def test_roundtrip_readback(self, setup):
        motor, *_ = setup
        motor.enable()
        motor.set_run_current_mA(1000)
        got = motor.get_run_current_mA()
        # resolution of CS is ~75 mA/step at default R_sense; allow some slack
        assert abs(got - 1000) < 100

    def test_soft_limit_rejects_excessive_current(self, setup):
        motor, *_ = setup
        with pytest.raises(OutOfRangeError, match="safety limit"):
            motor.set_run_current_mA(3000)   # default limit is 2000 mA

    def test_negative_current_rejected(self, setup):
        motor, *_ = setup
        with pytest.raises(OutOfRangeError):
            motor.set_run_current_mA(-100)

    def test_disable_zeros_current_axis_parameters(self, setup):
        motor, conn, board = setup
        motor.enable()
        motor.set_run_current_mA(1000)
        motor.set_standstill_current_mA(200)
        conn.calls.clear()

        motor.disable()
        # After disable, MaxCurrent and StandbyCurrent should both be 0
        assert conn.get_ap(board.motors[0].AP.MaxCurrent) == 0
        assert conn.get_ap(board.motors[0].AP.StandbyCurrent) == 0
        assert not motor.is_enabled

    def test_current_set_while_disabled_is_cached_not_written(self, setup):
        motor, conn, board = setup
        # motor is disabled by default
        assert not motor.is_enabled
        motor.set_run_current_mA(500)
        # No AP write to MaxCurrent while disabled
        max_current_writes = [
            c for c in conn.calls
            if c[0] == "set_ap" and c[1][0] == board.motors[0].AP.MaxCurrent
        ]
        assert max_current_writes == []
        # but when we enable, the cached value is applied
        motor.enable()
        assert conn.get_ap(board.motors[0].AP.MaxCurrent) > 0


class TestMotion:
    def test_set_speed_writes_vmax(self, setup):
        motor, conn, board = setup
        motor.set_speed_rps(1.0)
        # Landungsbruecke motion scaling uses the MRES code (8 at USTEP_256),
        # so 1 rot/s maps to ~1678 at the default step mode.
        value = conn.get_ap(board.motors[0].AP.MaxVelocity)
        assert 1600 < value < 1800

    def test_set_acceleration_writes_amax_dmax_d1(self, setup):
        motor, conn, board = setup
        motor.set_acceleration_rps2(5.0)
        ap = board.motors[0].AP
        a = conn.get_ap(ap.MaxAcceleration)
        d = conn.get_ap(ap.MaxDeceleration)
        d1 = conn.get_ap(ap.D1)
        assert a > 0
        assert a == d == d1  # base class mirrors accel to decel

    def test_negative_speed_rejected(self, setup):
        motor, *_ = setup
        with pytest.raises(OutOfRangeError):
            motor.set_speed_rps(-1.0)

    def test_zero_or_negative_accel_rejected(self, setup):
        motor, *_ = setup
        with pytest.raises(OutOfRangeError):
            motor.set_acceleration_rps2(0)
        with pytest.raises(OutOfRangeError):
            motor.set_acceleration_rps2(-1)

    def test_rotate_cw_sends_positive_velocity(self, setup):
        motor, conn, _ = setup
        motor.rotate(speed_rps=1.0, direction=Direction.CW)
        kind, (axis, velocity, _mid) = [
            (k, a) for k, a in conn.calls if k == "rotate"
        ][-1]
        assert axis == 0
        assert velocity > 0

    def test_rotate_ccw_sends_negative_velocity(self, setup):
        motor, conn, _ = setup
        motor.rotate(speed_rps=1.0, direction=Direction.CCW)
        _kind, (axis, velocity, _mid) = [
            (k, a) for k, a in conn.calls if k == "rotate"
        ][-1]
        assert axis == 0
        assert velocity < 0

    def test_rotate_without_speed_uses_cached(self, setup):
        motor, conn, _ = setup
        motor.set_speed_rps(2.0)
        motor.rotate()  # no explicit speed
        (_a, v, _m) = [a for k, a in conn.calls if k == "rotate"][-1]
        # 2 rot/s ~ 3355 with the firmware's MRES-code scaling.
        assert 3300 < v < 3400

    def test_rotate_by_sends_move_to_with_correct_absolute_target(self, setup):
        motor, conn, _ = setup
        motor.set_step_mode(StepMode.USTEP_256)
        motor.rotate_by(2.0, direction=Direction.CW)
        # 2 rotations × 200 fullsteps × MRES-code 8 = 3200
        (axis, target, _mid) = conn.last("move_to")
        assert axis == 0
        assert target == 3200

    def test_rotate_by_negative_direction(self, setup):
        motor, conn, _ = setup
        motor.rotate_by(1.0, direction=Direction.CCW)
        (_axis, target, _mid) = conn.last("move_to")
        assert target == -1600

    def test_stop_sends_stop_command(self, setup):
        motor, conn, _ = setup
        motor.stop()
        assert conn.last("stop") is not None

    def test_stop_immediately_drops_to_standstill_current(self, setup):
        motor, conn, board = setup
        motor.set_run_current_mA(1000)
        motor.set_standstill_current_mA(200)
        motor.enable()

        motor.stop()

        assert conn.last("stop") is not None
        assert conn.get_ap(board.motors[0].AP.MaxCurrent) == motor._cached_standstill_raw

    def test_motion_restores_run_current_after_stop(self, setup):
        motor, conn, board = setup
        motor.set_run_current_mA(1000)
        motor.set_standstill_current_mA(200)
        motor.enable()
        motor.stop()
        conn.calls.clear()

        motor.rotate(speed_rps=1.0, direction=Direction.CW)

        max_current_writes = [
            args for kind, args in conn.calls
            if kind == "set_ap" and args[0] == board.motors[0].AP.MaxCurrent
        ]
        assert max_current_writes
        assert max_current_writes[0][2] == motor._cached_run_current_raw


class TestStepMode:
    def test_set_step_mode_writes_mres(self, setup):
        motor, conn, board = setup
        motor.set_step_mode(StepMode.USTEP_16)
        value = conn.get_ap(board.motors[0].AP.MicrostepResolution)
        assert value == int(StepMode.USTEP_16)

    def test_get_step_mode_returns_cached(self, setup):
        motor, *_ = setup
        motor.set_step_mode(StepMode.USTEP_16)
        assert motor.get_step_mode() == StepMode.USTEP_16

    def test_unsupported_step_mode_rejected(self, setup):
        motor, *_ = setup
        with pytest.raises(ValueError, match="supports only these step modes"):
            motor.set_step_mode(StepMode.USTEP_64)

    def test_step_mode_affects_rotate_by_usteps(self, setup):
        motor, conn, _ = setup
        motor.set_step_mode(StepMode.USTEP_16)
        motor.rotate_by(1.0)
        (_axis, target, _mid) = conn.last("move_to")
        # 1 rev * 200 fullsteps * MRES-code 4 = 800
        assert target == 800


class TestStealthChop:
    def test_enable_stealthchop_sets_en_pwm_mode(self, setup):
        motor, conn, _ = setup
        motor.set_stealthchop(True)
        # After set_stealthchop(True), GCONF register (0x00) should have
        # EN_PWM_MODE bit set (bit 2)
        gconf = conn.registers.get(TMC5160.REG.GCONF, 0)
        assert gconf & 0b100  # EN_PWM_MODE

    def test_disable_stealthchop_clears_en_pwm_mode(self, setup):
        motor, conn, _ = setup
        motor.set_stealthchop(True)
        motor.set_stealthchop(False)
        gconf = conn.registers.get(TMC5160.REG.GCONF, 0)
        assert gconf & 0b100 == 0

    def test_stealthchop_with_threshold_writes_tpwmthrs(self, setup):
        motor, conn, _ = setup
        motor.set_stealthchop(True, threshold_rps=2.0)
        assert TMC5160.REG.TPWMTHRS in conn.registers
        tpwmthrs = conn.registers[TMC5160.REG.TPWMTHRS]
        assert tpwmthrs > 0
        # TPWMTHRS is an f_clk / ustep_per_s quantity; sanity-check magnitude
        assert tpwmthrs < (1 << 20)

    def test_stealthchop_threshold_rejects_zero_or_negative(self, setup):
        motor, *_ = setup
        with pytest.raises(ValueError):
            motor.set_stealthchop(True, threshold_rps=0)
        with pytest.raises(ValueError):
            motor.set_stealthchop(True, threshold_rps=-1)


class TestInterpolation:
    def test_enable_interpolation_sets_intpol_bit(self, setup):
        motor, conn, _ = setup
        motor.set_interpolation(True)
        # INTPOL is in CHOPCONF (reg 0x6C), bit 28
        chopconf = conn.registers.get(TMC5160.REG.CHOPCONF, 0)
        assert chopconf & (1 << 28)


class TestStallGuard:
    def test_stallguard_threshold_accepts_valid_range(self, setup):
        motor, conn, board = setup
        motor.set_stallguard_threshold(10)
        assert conn.get_ap(board.motors[0].AP.SG2Threshold) == 10

    def test_stallguard_threshold_rejects_out_of_range(self, setup):
        motor, *_ = setup
        with pytest.raises(ValueError):
            motor.set_stallguard_threshold(100)
        with pytest.raises(ValueError):
            motor.set_stallguard_threshold(-100)

    def test_stallguard_enable_disable_uses_cached_threshold(self, setup):
        motor, conn, board = setup
        motor.set_stallguard_threshold(10)
        motor.set_stallguard_enabled(False)
        assert conn.get_ap(board.motors[0].AP.SG2Threshold) == 0

        motor.set_stallguard_enabled(True)
        assert conn.get_ap(board.motors[0].AP.SG2Threshold) == 10

    def test_stallguard_filter_writes_sg2_filter_ap(self, setup):
        motor, conn, board = setup
        motor.set_stallguard_filter_enabled(True)
        assert conn.get_ap(board.motors[0].AP.SG2FilterEnable) == 1
        motor.set_stallguard_filter_enabled(False)
        assert conn.get_ap(board.motors[0].AP.SG2FilterEnable) == 0


class TestChopperAndCoolStep:
    def test_chopper_mode_writes_constant_toff_ap(self, setup):
        motor, conn, board = setup
        motor.set_chopper_mode(1)
        assert conn.get_ap(board.motors[0].AP.ConstantTOffMode) == 1
        motor.set_chopper_mode(0)
        assert conn.get_ap(board.motors[0].AP.ConstantTOffMode) == 0

    def test_chopper_mode_rejects_invalid_value(self, setup):
        motor, *_ = setup
        with pytest.raises(ValueError):
            motor.set_chopper_mode(2)

    def test_configure_coolstep_writes_pytrinamic_axis_parameters(self, setup):
        motor, conn, board = setup
        ap = board.motors[0].AP
        motor.configure_coolstep(
            min_current=1,
            current_down_step=2,
            current_up_step=3,
            hysteresis=4,
            threshold_speed=123,
        )

        assert conn.get_ap(ap.SEIMIN) == 1
        assert conn.get_ap(ap.SECDS) == 2
        assert conn.get_ap(ap.SECUS) == 3
        assert conn.get_ap(ap.smartEnergyHysteresis) == 4
        assert conn.get_ap(ap.smartEnergyThresholdSpeed) == 123

    def test_coolstep_enable_disable_uses_cached_threshold(self, setup):
        motor, conn, board = setup
        ap = board.motors[0].AP
        motor.set_coolstep_threshold_raw(456)
        assert conn.get_ap(ap.smartEnergyThresholdSpeed) == 456
        motor.set_coolstep_enabled(False)
        assert conn.get_ap(ap.smartEnergyThresholdSpeed) == 0
        motor.set_coolstep_enabled(True)
        assert conn.get_ap(ap.smartEnergyThresholdSpeed) == 456


class TestReferenceSwitches:
    def test_enable_reference_stops_writes_left_and_right_aps(self, setup):
        motor, conn, board = setup
        ap = board.motors[0].AP

        motor.enable_reference_stops(left=True, right=False)

        assert conn.get_ap(ap.AutomaticLeftStop) == 1
        assert conn.get_ap(ap.AutomaticRightStop) == 0

    def test_get_endstops_reads_left_and_right_aps(self, setup):
        motor, conn, board = setup
        ap = board.motors[0].AP
        conn.axis_parameters[(ap.LeftEndstop, 0)] = 1
        conn.axis_parameters[(ap.RightEndstop, 0)] = 0

        assert motor.get_left_endstop() is True
        assert motor.get_right_endstop() is False


class TestPosition:
    def test_reset_position_zeros_both_position_aps(self, setup):
        motor, conn, board = setup
        motor.reset_position()
        ap = board.motors[0].AP
        assert conn.get_ap(ap.ActualPosition) == 0
        assert conn.get_ap(ap.TargetPosition) == 0

    def test_get_actual_position_converts_to_revolutions(self, setup):
        motor, conn, board = setup
        # inject a raw position value
        conn.axis_parameters[(board.motors[0].AP.ActualPosition, 0)] = 1600
        pos = motor.get_actual_position_rot()
        assert pos == pytest.approx(1.0)
