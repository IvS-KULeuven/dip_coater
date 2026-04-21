import logging

import pytest

from dip_coater.mechanical.mechanical_setup import MechanicalSetup
from dip_coater.motor_driver.trinamic_adapter import TrinamicWrapperMotorAdapter
from trinamic_wrapper import Direction, StepMode


class FakeStepperMotor:
    def __init__(self):
        self.enabled = False
        self.step_mode = StepMode.USTEP_256
        self.position_rot = 0.0
        self.run_current_mA = 0.0
        self.standstill_current_mA = 0.0
        self.configured_speed_rps = None
        self.configured_accel_rps2 = None
        self.wait_results = [True]
        self.rotate_calls = []
        self.stop_calls = 0
        self.interpolation = None
        self.stallguard_threshold = None

    def enable(self) -> None:
        self.enabled = True

    def disable(self) -> None:
        self.enabled = False

    @property
    def is_enabled(self) -> bool:
        return self.enabled

    def set_run_current_mA(self, current_mA: float) -> None:
        self.run_current_mA = current_mA

    def set_standstill_current_mA(self, current_mA: float) -> None:
        self.standstill_current_mA = current_mA

    def get_run_current_mA(self) -> float:
        return self.run_current_mA

    def get_standstill_current_mA(self) -> float:
        return self.standstill_current_mA

    def set_speed_rps(self, speed_rps: float) -> None:
        self.configured_speed_rps = speed_rps

    def set_acceleration_rps2(self, accel_rps2: float) -> None:
        self.configured_accel_rps2 = accel_rps2

    def set_step_mode(self, mode: StepMode) -> None:
        self.step_mode = mode

    def get_step_mode(self) -> StepMode:
        return self.step_mode

    def rotate(self, speed_rps: float | None = None, direction: Direction = Direction.CW) -> None:
        self.rotate_calls.append(("rotate", speed_rps, direction))

    def rotate_by(self, revolutions: float, direction: Direction = Direction.CW) -> None:
        signed = revolutions * int(direction)
        self.position_rot += signed
        self.rotate_calls.append(("rotate_by", revolutions, direction))

    def wait_until_reached(self, timeout_s: float | None = None) -> bool:
        if self.wait_results:
            return self.wait_results.pop(0)
        return True

    def stop(self) -> None:
        self.stop_calls += 1

    def get_actual_position_rot(self) -> float:
        return self.position_rot

    def get_actual_speed_rps(self) -> float:
        return 0.0

    def reset_position(self) -> None:
        self.position_rot = 0.0

    def set_interpolation(self, enabled: bool) -> None:
        self.interpolation = enabled

    def set_stallguard_threshold(self, threshold: int) -> None:
        self.stallguard_threshold = threshold

    def has_feature(self, name: str) -> bool:
        return True


def make_adapter(
    motor: FakeStepperMotor | None = None,
    *,
    invert_direction: bool = False,
    close=None,
):
    motor = motor or FakeStepperMotor()
    setup = MechanicalSetup(mm_per_revolution=4.0)
    return TrinamicWrapperMotorAdapter(
        motor,
        setup,
        invert_direction=invert_direction,
        close=close,
    )


def test_adapter_move_and_position_round_trip():
    motor = FakeStepperMotor()
    adapter = make_adapter(motor)

    adapter.move_up(8.0, 2.0, 4.0)

    assert motor.rotate_calls[-1] == ("rotate_by", 2.0, Direction.CW)
    assert motor.configured_speed_rps == pytest.approx(0.5)
    assert motor.configured_accel_rps2 == pytest.approx(1.0)
    assert adapter.get_current_position_mm() == pytest.approx(8.0)


def test_adapter_run_to_position_uses_relative_delta():
    motor = FakeStepperMotor()
    adapter = make_adapter(motor)
    adapter.move_up(8.0, 2.0)

    adapter.run_to_position(4.0, 1.0)

    assert motor.rotate_calls[-1] == ("rotate_by", 1.0, Direction.CCW)
    assert adapter.get_current_position_mm() == pytest.approx(4.0)


def test_adapter_invert_direction_flips_motion():
    motor = FakeStepperMotor()
    adapter = make_adapter(motor, invert_direction=True)

    adapter.move_up(4.0, 1.0)

    assert motor.rotate_calls[-1] == ("rotate_by", 1.0, Direction.CCW)
    assert adapter.get_current_position_mm() == pytest.approx(-4.0)


@pytest.mark.asyncio
async def test_adapter_wait_for_motor_done_async_polls_until_reached():
    motor = FakeStepperMotor()
    motor.wait_results = [False, False, True]
    adapter = make_adapter(motor)

    await adapter.wait_for_motor_done_async()

    assert motor.wait_results == []


def test_adapter_cleanup_disables_motor_and_closes_connection():
    motor = FakeStepperMotor()
    closed = {"value": False}

    def close():
        closed["value"] = True

    adapter = make_adapter(motor, close=close)
    adapter.enable_motor()

    adapter.cleanup()

    assert motor.is_enabled is False
    assert closed["value"] is True


def test_adapter_step_mode_maps_to_wrapper_enum():
    motor = FakeStepperMotor()
    adapter = make_adapter(motor)

    adapter.set_microsteps(16)

    assert motor.step_mode == StepMode.USTEP_16
    assert adapter.get_microsteps() == 16


def test_adapter_supports_current_and_basic_advanced_passthrough():
    motor = FakeStepperMotor()
    adapter = make_adapter(motor)

    adapter.set_current(800.0)
    adapter.set_current_standstill(120.0)
    adapter.set_interpolation(True)
    adapter.set_stallguard_threshold(7)

    assert adapter.get_current() == pytest.approx(800.0)
    assert adapter.get_current_standstill() == pytest.approx(120.0)
    assert motor.interpolation is True
    assert motor.stallguard_threshold == 7


def test_adapter_log_handler_methods_do_not_crash():
    adapter = make_adapter()
    handler = logging.StreamHandler()

    adapter.add_log_handler(handler)
    adapter.set_loglevel(logging.INFO)
    adapter.remove_log_handler(handler)


def test_unmapped_advanced_features_fail_loudly():
    adapter = make_adapter()

    with pytest.raises(NotImplementedError):
        adapter.set_chopper_mode("SpreadCycle")
    with pytest.raises(NotImplementedError):
        adapter.set_stallguard_enabled(True)
    with pytest.raises(NotImplementedError):
        adapter.set_stallguard_filter_enabled(True)
    with pytest.raises(NotImplementedError):
        adapter.set_coolstep_enabled(True)
    with pytest.raises(NotImplementedError):
        adapter.set_coolstep_threshold(3)
