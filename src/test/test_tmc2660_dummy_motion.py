from dip_coater.motor_driver.tmc2660 import tmc2660_dummy
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
