from types import SimpleNamespace

import pytest

from dip_coater.mechanical.mechanical_setup import MechanicalSetup
from dip_coater.motor_driver.tmc2660 import tmc2660_dummy
from dip_coater.motor_driver.tmc2660.tmc2660 import MotorDriverTMC2660
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
