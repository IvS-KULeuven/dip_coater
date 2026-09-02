from types import SimpleNamespace

import pytest

from dip_coater.mechanical.mechanical_setup import MechanicalSetup
from dip_coater.motor_driver.tmc2660 import tmc2660
from dip_coater.motor_driver.tmc2660 import tmc2660_dummy
from dip_coater.motor_driver.tmc2660.tmc2660 import (
    MotorDriverTMC2660,
    VSenseFullScale,
)
from dip_coater.motor_driver.tmc2660.tmc2660_dummy import (
    DummyAxisParameters,
    DummyEvalBoard,
    DummyInterface,
)


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.advance(seconds)

    def advance(self, seconds):
        self.now += seconds


def make_driver(**kwargs):
    app_state = SimpleNamespace(
        mechanical_setup=MechanicalSetup(mm_per_revolution=4.0),
        config=SimpleNamespace(USE_DUMMY_DRIVER=True),
    )
    return MotorDriverTMC2660(
        app_state,
        interface_type="dummy_tmcl",
        log_handlers=[],
        **kwargs,
    )


def test_tmc2660_dummy_move_by_duration_depends_on_steps_and_velocity(monkeypatch):
    clock = FakeClock()
    monkeypatch.setattr(tmc2660_dummy, "time", clock, raising=False)
    values = {
        DummyAxisParameters.ActualPosition: 0,
        DummyAxisParameters.PositionReachedFlag: True,
        DummyAxisParameters.MaxVelocity: 100,
    }
    interface = DummyInterface(values)
    board = DummyEvalBoard(values)

    interface.move_by(0, 200)

    assert board.get_axis_parameter(DummyAxisParameters.PositionReachedFlag, 0) is False
    assert board.get_axis_parameter(DummyAxisParameters.ActualPosition, 0) == 0

    clock.advance(1.0)
    assert board.get_axis_parameter(DummyAxisParameters.PositionReachedFlag, 0) is False
    assert board.get_axis_parameter(DummyAxisParameters.ActualPosition, 0) == 100

    clock.advance(1.0)
    assert board.get_axis_parameter(DummyAxisParameters.PositionReachedFlag, 0) is True
    assert board.get_axis_parameter(DummyAxisParameters.ActualPosition, 0) == 200


@pytest.mark.parametrize(
    ("microsteps", "register_value"),
    [(1, 0), (2, 1), (16, 4), (256, 8)],
)
def test_tmc2660_microsteps_use_tmcl_index_encoding(microsteps, register_value):
    driver = make_driver(step_mode=8)

    driver.set_microsteps(microsteps)

    assert driver.dummy_values[driver.motor.AP.MicrostepResolution] == register_value
    assert driver.get_microsteps() == microsteps


def test_tmc2660_vsense_enum_exposes_scalar_register_values():
    assert VSenseFullScale.VSENSE_FULL_SCALE_305mV.value == 0
    assert VSenseFullScale.VSENSE_FULL_SCALE_165mV.value == 1


def test_tmc2660_applies_selected_vsense_during_initialization():
    driver = make_driver(
        step_mode=8,
        current_mA=1000,
        vsense_full_scale=VSenseFullScale.VSENSE_FULL_SCALE_165mV,
    )

    assert driver.get_vsense_full_scale() == 1
    assert driver.vsense_fs is VSenseFullScale.VSENSE_FULL_SCALE_165mV


@pytest.mark.parametrize(
    ("invert_direction", "homed_up", "expected_position_mm"),
    [
        (False, False, 4.0),
        (False, True, -4.0),
        (True, False, -4.0),
        (True, True, 4.0),
    ],
)
def test_tmc2660_position_uses_inversion_and_home_direction(
    invert_direction, homed_up, expected_position_mm
):
    driver = make_driver(step_mode=8, invert_direction=invert_direction)
    driver.homing_found = True
    driver.dummy_values[driver.motor.AP.ActualPosition] = 1600

    assert driver.get_current_position_mm(homed_up) == pytest.approx(
        expected_position_mm
    )


@pytest.mark.parametrize(
    ("invert_direction", "homed_up", "expected_target_steps"),
    [
        (False, False, 1600),
        (False, True, -1600),
        (True, False, -1600),
        (True, True, 1600),
    ],
)
def test_tmc2660_absolute_target_uses_inversion_and_home_direction(
    invert_direction, homed_up, expected_target_steps
):
    driver = make_driver(step_mode=8, invert_direction=invert_direction)
    driver.homing_found = True
    targets = []
    driver.motor.move_to = targets.append

    driver.run_to_position(4.0, homed_up=homed_up)

    assert targets == [expected_target_steps]


def test_tmc2660_reads_actual_position_as_signed():
    calls = []

    class FakeEvalBoard:
        def get_axis_parameter(self, parameter, axis, signed=False):
            calls.append((parameter, axis, signed))
            return -1

    driver = MotorDriverTMC2660.__new__(MotorDriverTMC2660)
    driver.eval_board = FakeEvalBoard()
    driver.motor = SimpleNamespace(
        AP=SimpleNamespace(ActualPosition="actual-position")
    )
    driver.axis = 0

    assert driver.get_actual_position() == -1
    assert calls == [("actual-position", 0, True)]


def test_tmc2660_absolute_position_requires_manual_home_reference():
    driver = make_driver(step_mode=8)

    assert driver.get_current_position_mm() is None
    with pytest.raises(ValueError, match="not homed"):
        driver.run_to_position(4.0)


def test_tmc2660_sync_wait_sleeps_between_status_polls(monkeypatch):
    driver = MotorDriverTMC2660.__new__(MotorDriverTMC2660)
    reached = iter((False, False, True))
    sleep_calls = []
    driver.is_target_reached = lambda: next(reached)
    driver.logger = SimpleNamespace(log=lambda *args: None)
    monkeypatch.setattr(
        tmc2660,
        "time",
        SimpleNamespace(sleep=sleep_calls.append),
        raising=False,
    )

    driver.wait_for_motor_done()

    assert sleep_calls == [0.1, 0.1]


def test_tmc2660_cleanup_stops_before_disabling_and_closing():
    driver = MotorDriverTMC2660.__new__(MotorDriverTMC2660)
    calls = []
    driver.stop_motor = lambda: calls.append("stop")
    driver.disable_motor = lambda: calls.append("disable")
    driver.interface = SimpleNamespace(close=lambda: calls.append("close"))
    driver.logger = SimpleNamespace(log=lambda *args: calls.append("log"))

    driver.cleanup()

    assert calls == ["stop", "disable", "close", "log"]


def test_tmc2660_cleanup_attempts_every_step_after_stop_failure():
    driver = MotorDriverTMC2660.__new__(MotorDriverTMC2660)
    calls = []

    def fail_stop():
        calls.append("stop")
        raise RuntimeError("stop failed")

    driver.stop_motor = fail_stop
    driver.disable_motor = lambda: calls.append("disable")
    driver.interface = SimpleNamespace(close=lambda: calls.append("close"))
    driver.logger = SimpleNamespace(log=lambda *args: calls.append("log"))

    with pytest.raises(RuntimeError, match="stop failed"):
        driver.cleanup()

    assert calls == ["stop", "disable", "close"]
