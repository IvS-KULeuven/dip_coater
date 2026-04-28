import pytest

from trinamic_wrapper import (
    Direction,
    DummyStepperMotor,
    MotorConfig,
    OutOfRangeError,
    StepMode,
    StepperMotor,
)


def test_dummy_motor_satisfies_stepper_motor_protocol():
    motor = DummyStepperMotor()

    assert isinstance(motor, StepperMotor)


def test_dummy_motor_tracks_position_speed_and_step_mode():
    motor = DummyStepperMotor(
        MotorConfig(default_microsteps=StepMode.USTEP_16, max_current_mA_limit=500)
    )

    motor.set_run_current_mA(250)
    motor.set_standstill_current_mA(50)
    motor.set_step_mode(StepMode.USTEP_256)
    motor.set_speed_rps(2.5)
    motor.set_acceleration_rps2(5.0)
    motor.enable()

    motor.rotate_by(1.25, direction=Direction.CW)
    motor.rotate_by(0.25, direction=Direction.CCW)

    assert motor.is_enabled is True
    assert motor.get_run_current_mA() == pytest.approx(250)
    assert motor.get_standstill_current_mA() == pytest.approx(50)
    assert motor.get_step_mode() == StepMode.USTEP_256
    assert motor.get_actual_position_rot() == pytest.approx(1.0)
    assert motor.wait_until_reached(timeout_s=0.0) is True

    motor.rotate(direction=Direction.CCW)
    assert motor.get_actual_speed_rps() == pytest.approx(-2.5)
    assert motor.wait_until_reached(timeout_s=0.0) is False

    motor.stop()
    assert motor.get_actual_speed_rps() == pytest.approx(0.0)
    assert motor.wait_until_reached(timeout_s=0.0) is True


def test_dummy_motor_validates_current_and_motion_parameters():
    motor = DummyStepperMotor(MotorConfig(max_current_mA_limit=500))

    with pytest.raises(OutOfRangeError):
        motor.set_run_current_mA(501)
    with pytest.raises(OutOfRangeError):
        motor.set_standstill_current_mA(-1)
    with pytest.raises(OutOfRangeError):
        motor.set_speed_rps(-1)
    with pytest.raises(OutOfRangeError):
        motor.set_acceleration_rps2(0)
