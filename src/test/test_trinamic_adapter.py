import logging

import pytest

from dip_coater.mechanical.mechanical_setup import MechanicalSetup
from dip_coater.motor_driver.trinamic_adapter import TrinamicWrapperMotorAdapter
from trinamic_wrapper import Direction, StepMode


class FakeStepperMotor:
    class _AP:
        ActualPosition = "ActualPosition"
        TargetPosition = "TargetPosition"

    class _RawMotor:
        def __init__(self, outer):
            self._outer = outer
            self.AP = outer._AP
            self.axis_parameters = {
                self.AP.ActualPosition: 0,
                self.AP.TargetPosition: 0,
            }

        def get_axis_parameter(self, ap_type, signed: bool = False):
            return self.axis_parameters[ap_type]

        def set_axis_parameter(self, ap_type, value):
            self.axis_parameters[ap_type] = value

    def __init__(self):
        self.enabled = False
        self.step_mode = StepMode.USTEP_256
        self.position_rot = 0.0
        self.run_current_mA = 0.0
        self.standstill_current_mA = 0.0
        self.configured_speed_rps = None
        self.configured_accel_rps2 = None
        self.wait_results = [True]
        self.speed_rps = 0.0
        self.position_sequence = []
        self.speed_sequence = []
        self.rotate_calls = []
        self.stop_calls = 0
        self.interpolation = None
        self.stealthchop = None
        self.stealthchop_threshold_rps = None
        self.chopper_mode = None
        self.stallguard_enabled = None
        self.stallguard_filter_enabled = None
        self.stallguard_threshold = None
        self.coolstep_enabled = None
        self.coolstep_threshold_raw = None
        self.reference_stops = None
        self.left_endstop = False
        self.right_endstop = False
        self.motion_units_per_fullstep = self.step_mode.microsteps_per_fullstep
        self._motor = self._RawMotor(self)

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
        self.motion_units_per_fullstep = mode.microsteps_per_fullstep

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
        if self.position_sequence:
            self.position_rot = self.position_sequence.pop(0)
        full_steps_per_rev = 200
        actual = round(self.position_rot * full_steps_per_rev * self.motion_units_per_fullstep)
        self._motor.axis_parameters[self._motor.AP.ActualPosition] = actual
        return self.position_rot

    def get_actual_speed_rps(self) -> float:
        if self.speed_sequence:
            self.speed_rps = self.speed_sequence.pop(0)
        return self.speed_rps

    def reset_position(self) -> None:
        self.position_rot = 0.0

    def set_interpolation(self, enabled: bool) -> None:
        self.interpolation = enabled

    def set_stealthchop(
        self,
        enabled: bool,
        threshold_rps: float | None = None,
    ) -> None:
        self.stealthchop = enabled
        self.stealthchop_threshold_rps = threshold_rps

    def set_chopper_mode(self, mode: int) -> None:
        self.chopper_mode = mode

    def set_stallguard_enabled(self, enabled: bool) -> None:
        self.stallguard_enabled = enabled

    def set_stallguard_filter_enabled(self, enabled: bool) -> None:
        self.stallguard_filter_enabled = enabled

    def set_stallguard_threshold(self, threshold: int) -> None:
        self.stallguard_threshold = threshold

    def set_coolstep_enabled(self, enabled: bool) -> None:
        self.coolstep_enabled = enabled

    def set_coolstep_threshold_raw(self, threshold: int) -> None:
        self.coolstep_threshold_raw = threshold

    def enable_reference_stops(
        self,
        *,
        left: bool = True,
        right: bool = True,
    ) -> None:
        self.reference_stops = (left, right)

    def get_left_endstop(self) -> bool:
        return self.left_endstop

    def get_right_endstop(self) -> bool:
        return self.right_endstop

    def has_feature(self, name: str) -> bool:
        return True

    def _motion_units_per_fullstep(self) -> int:
        return self.motion_units_per_fullstep


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
    motor.position_sequence = [0.0, 0.5, 0.98, 1.0]
    motor.speed_sequence = [0.2, 0.1, 0.03, 0.0]
    adapter = make_adapter(motor)
    adapter.move_up(4.0, 1.0)

    await adapter.wait_for_motor_done_async()

    assert motor.position_sequence == []
    assert motor.speed_sequence == []


@pytest.mark.asyncio
async def test_adapter_wait_uses_motion_units_for_tmc5160_style_tolerance():
    motor = FakeStepperMotor()
    motor.motion_units_per_fullstep = 8
    motor.position_sequence = [0.0, 0.999792]
    motor.speed_sequence = [0.2, 0.0]
    adapter = make_adapter(motor)
    adapter.move_up(4.0, 1.0)

    await adapter.wait_for_motor_done_async()

    assert motor.position_sequence == []
    assert motor._motor.axis_parameters[motor._motor.AP.TargetPosition] == 1600


def test_adapter_sync_wait_polls_until_reached():
    motor = FakeStepperMotor()
    motor.position_sequence = [0.0, 0.5, 0.98, 1.0]
    motor.speed_sequence = [0.2, 0.1, 0.03, 0.0]
    adapter = make_adapter(motor)
    adapter.move_up(4.0, 1.0)

    adapter.wait_for_motor_done()

    assert motor.position_sequence == []
    assert motor.speed_sequence == []


@pytest.mark.asyncio
async def test_adapter_wait_exits_after_stop_when_target_cleared():
    motor = FakeStepperMotor()
    motor.wait_results = [False, False, False]
    motor.speed_sequence = [0.2, 0.0]
    adapter = make_adapter(motor)

    adapter.stop_motor()
    await adapter.wait_for_motor_done_async()

    assert motor.stop_calls == 1


@pytest.mark.asyncio
async def test_adapter_wait_retries_if_motion_reappears_after_reaching_target():
    motor = FakeStepperMotor()
    motor.position_sequence = [
        0.0,
        1.0,
        1.0,
        0.95,
        1.0,
        1.0,
        1.0,
        1.0,
        1.0,
        1.0,
    ]
    motor.speed_sequence = [
        0.0,
        0.0,
        0.2,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
    ]
    adapter = make_adapter(motor)
    adapter.move_up(4.0, 1.0)

    await adapter.wait_for_motor_done_async()

    assert motor.stop_calls == 2
    assert motor._motor.axis_parameters[motor._motor.AP.TargetPosition] == 51200


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


def test_adapter_supports_advanced_feature_passthroughs():
    motor = FakeStepperMotor()
    adapter = make_adapter(motor)

    adapter.set_chopper_mode("SpreadCycle")
    adapter.set_stealthchop_threshold(2.5)
    adapter.set_stealthchop_enabled(True)
    adapter.set_stallguard_enabled(True)
    adapter.set_stallguard_filter_enabled(True)
    adapter.set_coolstep_enabled(True)
    adapter.set_coolstep_threshold(3)

    assert motor.chopper_mode == 0
    assert motor.stealthchop is True
    assert motor.stealthchop_threshold_rps == pytest.approx(2.5)
    assert motor.stallguard_enabled is True
    assert motor.stallguard_filter_enabled is True
    assert motor.coolstep_enabled is True
    assert motor.coolstep_threshold_raw == 3


def test_adapter_disables_stealthchop_without_threshold():
    motor = FakeStepperMotor()
    adapter = make_adapter(motor)

    adapter.set_stealthchop_threshold(2.5)
    adapter.set_stealthchop_enabled(False)

    assert motor.stealthchop is False
    assert motor.stealthchop_threshold_rps is None


def test_adapter_chopper_mode_accepts_constant_toff_label():
    motor = FakeStepperMotor()
    adapter = make_adapter(motor)

    adapter.set_chopper_mode("Constant TOff")

    assert motor.chopper_mode == 1


def test_adapter_supports_reference_stop_passthroughs():
    motor = FakeStepperMotor()
    motor.left_endstop = True
    motor.right_endstop = False
    adapter = make_adapter(motor)

    adapter.enable_reference_stops(left=True, right=False)

    assert motor.reference_stops == (True, False)
    assert adapter.get_left_endstop() is True
    assert adapter.get_right_endstop() is False
