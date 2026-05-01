import pytest
from TMC_2209._TMC_2209_move import MovementAbsRel, StopMode

from dip_coater.motor_driver.tmc2209 import tmc2209_dummy
from dip_coater.motor_driver.tmc2209.tmc2209_dummy import DummyTMC2209


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.advance(seconds)

    def advance(self, seconds):
        self.now += seconds


def test_tmc2209_dummy_motion_duration_depends_on_steps_and_speed(monkeypatch):
    clock = FakeClock()
    monkeypatch.setattr(tmc2209_dummy, "time", clock, raising=False)
    tmc = DummyTMC2209()

    tmc.set_max_speed(200)
    tmc.run_to_position_steps_threaded(400, movement_abs_rel=MovementAbsRel.RELATIVE)

    assert tmc.distance_to_go() == 400
    assert tmc.get_current_position() == 0

    clock.advance(1.0)
    assert tmc.distance_to_go() == 200
    assert tmc.get_current_position() == 200

    clock.advance(1.0)
    assert tmc.wait_for_movement_finished_threaded() == StopMode.NO
    assert tmc.distance_to_go() == 0
    assert tmc.get_current_position() == 400


def test_tmc2209_dummy_stop_holds_current_interpolated_position(monkeypatch):
    clock = FakeClock()
    monkeypatch.setattr(tmc2209_dummy, "time", clock, raising=False)
    tmc = DummyTMC2209()

    tmc.set_max_speed(100)
    tmc.run_to_position_steps_threaded(300, movement_abs_rel=MovementAbsRel.RELATIVE)
    clock.advance(1.0)
    tmc.stop()

    assert tmc.distance_to_go() == 0
    assert tmc.get_current_position() == pytest.approx(100)
