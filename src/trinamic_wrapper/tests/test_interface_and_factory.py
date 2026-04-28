"""Tests for the generic StepperMotor interface.

These verify that both concrete motor classes satisfy the Protocol, that
user code written against the Protocol works with either chip without
modification, and that the factory returns the correct concrete class.
"""

from __future__ import annotations

import pytest
from pytrinamic.evalboards import TMC2660_eval, TMC5160_eval

from tests.fake_connection import FakeConnection
from trinamic_wrapper import (
    Chip,
    Direction,
    MotorConfig,
    StepMode,
    StepperMotor,
    TMC2660Motor,
    TMC5160Motor,
    create_motor,
)


def _make_5160() -> tuple[TMC5160Motor, FakeConnection]:
    conn = FakeConnection()
    board = TMC5160_eval(conn, module_id=1)
    motor = TMC5160Motor(board, MotorConfig(sense_resistor_ohms=0.075))
    conn.calls.clear()
    return motor, conn


def _make_2660() -> tuple[TMC2660Motor, FakeConnection]:
    conn = FakeConnection()
    board = TMC2660_eval(conn, module_id=1)
    motor = TMC2660Motor(board, MotorConfig(sense_resistor_ohms=0.1))
    conn.calls.clear()
    return motor, conn


class TestProtocolConformance:
    """Both motor classes must satisfy the StepperMotor Protocol."""

    def test_5160_satisfies_protocol(self):
        motor, _ = _make_5160()
        assert isinstance(motor, StepperMotor)

    def test_2660_satisfies_protocol(self):
        motor, _ = _make_2660()
        assert isinstance(motor, StepperMotor)


class TestChipAgnosticUsage:
    """
    The same piece of user code should work with either chip.
    If this test ever breaks, the abstraction has leaked.
    """

    @pytest.mark.parametrize("maker", [_make_5160, _make_2660])
    def test_basic_drive_sequence(self, maker):
        motor, conn = maker()
        # Generic code — no chip-specific branches
        motor.set_step_mode(StepMode.USTEP_256)
        motor.set_run_current_mA(800)
        motor.set_standstill_current_mA(200)
        motor.set_speed_rps(1.5)
        motor.set_acceleration_rps2(10.0)
        motor.enable()
        motor.rotate(direction=Direction.CW)
        motor.stop()
        motor.rotate_by(0.5, direction=Direction.CCW)
        motor.disable()
        # If we got here without exceptions, the contract held.

    @pytest.mark.parametrize("maker", [_make_5160, _make_2660])
    def test_feature_discovery_pattern(self, maker):
        """Idiomatic chip-agnostic advanced feature use."""
        motor, _ = maker()
        # This pattern should be safe for any chip
        if motor.has_feature("stealthchop"):
            motor.set_stealthchop(True)
        if motor.has_feature("interpolation"):
            motor.set_interpolation(True)
        # No exceptions — user code is portable.


class TestFactory:
    def test_factory_returns_tmc5160_for_tmc5160(self):
        conn = FakeConnection()
        motor = create_motor("TMC5160", conn)
        assert isinstance(motor, TMC5160Motor)

    def test_factory_accepts_chip_enum(self):
        conn = FakeConnection()
        motor = create_motor(Chip.TMC5160, conn)
        assert isinstance(motor, TMC5160Motor)

    def test_factory_returns_tmc2660_for_tmc2660(self):
        conn = FakeConnection()
        motor = create_motor("TMC2660", conn)
        assert isinstance(motor, TMC2660Motor)

    def test_factory_uses_correct_default_rsense(self):
        conn5 = FakeConnection()
        m5 = create_motor("TMC5160", conn5)
        assert m5._config.sense_resistor_ohms == 0.075

        conn2 = FakeConnection()
        m2 = create_motor("TMC2660", conn2)
        assert m2._config.sense_resistor_ohms == 0.1

    def test_factory_accepts_custom_config(self):
        conn = FakeConnection()
        custom = MotorConfig(full_steps_per_rev=400, sense_resistor_ohms=0.05)
        motor = create_motor("TMC5160", conn, config=custom)
        assert motor._config.full_steps_per_rev == 400
        assert motor._config.sense_resistor_ohms == 0.05

    def test_factory_rejects_unknown_chip(self):
        conn = FakeConnection()
        with pytest.raises(ValueError, match="unknown chip"):
            create_motor("TMC9999", conn)  # type: ignore[arg-type]

    def test_factory_module_id_passed_through(self):
        conn = FakeConnection()
        motor = create_motor("TMC5160", conn, module_id=3)
        assert motor._eval._module_id == 3


class TestConfigValidation:
    def test_zero_fullsteps_rejected(self):
        with pytest.raises(ValueError):
            MotorConfig(full_steps_per_rev=0)

    def test_zero_rsense_rejected(self):
        with pytest.raises(ValueError):
            MotorConfig(sense_resistor_ohms=0)

    def test_negative_rsense_rejected(self):
        with pytest.raises(ValueError):
            MotorConfig(sense_resistor_ohms=-1)

    def test_zero_clock_rejected(self):
        with pytest.raises(ValueError):
            MotorConfig(clock_hz=0)

    def test_microsteps_per_fullstep_from_stepmode(self):
        assert StepMode.FULLSTEP.microsteps_per_fullstep == 1
        assert StepMode.USTEP_2.microsteps_per_fullstep == 2
        assert StepMode.USTEP_16.microsteps_per_fullstep == 16
        assert StepMode.USTEP_256.microsteps_per_fullstep == 256
