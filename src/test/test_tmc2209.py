import threading
from types import SimpleNamespace

import pytest

from dip_coater.gpio import GpioEdge, GpioState
from dip_coater.motor_driver.tmc2209.tmc2209 import MotorDriverTMC2209


class FakeTMC2209:
    def __init__(self, distances):
        self.distances = iter(distances)
        self.distance_checks = 0

    def distance_to_go(self):
        self.distance_checks += 1
        return next(self.distances)

    def wait_for_movement_finished_threaded(self):
        return threading.get_ident()


@pytest.mark.asyncio
async def test_async_wait_polls_negative_distance_until_target(monkeypatch):
    async def no_delay(_seconds):
        pass

    monkeypatch.setattr(
        "dip_coater.motor_driver.tmc2209.tmc2209.asyncio.sleep", no_delay
    )
    driver = MotorDriverTMC2209.__new__(MotorDriverTMC2209)
    driver.tmc = FakeTMC2209([-2, -1, 0])

    await driver.wait_for_motor_done_async()

    assert driver.tmc.distance_checks == 3


@pytest.mark.asyncio
async def test_async_wait_joins_worker_off_the_event_loop():
    event_loop_thread = threading.get_ident()
    driver = MotorDriverTMC2209.__new__(MotorDriverTMC2209)
    driver.tmc = FakeTMC2209([0])

    join_thread = await driver.wait_for_motor_done_async()

    assert join_thread != event_loop_thread


class FakeHomingGPIO:
    def __init__(self):
        self.states = {1: GpioState.LOW, 2: GpioState.LOW}
        self.callbacks = {}

    def input(self, pin):
        return self.states[pin]

    def add_event_detect(self, pin, event, callback, bouncetime=None):
        self.callbacks[pin] = callback

    def remove_event_detect(self, pin):
        self.callbacks.pop(pin, None)


def test_first_limit_switch_homing_registers_callback_polarity():
    driver = MotorDriverTMC2209.__new__(MotorDriverTMC2209)
    driver.GPIO = FakeHomingGPIO()
    driver.tmc = SimpleNamespace(set_current_position=lambda position: None)
    driver.limit_switch_bindings = {}
    stops = []
    moves = []
    driver.stop_motor = stops.append

    def move(distance_mm, speed_mm_s):
        moves.append((distance_mm, speed_mm_s))
        if len(moves) == 1:
            driver.GPIO.states[1] = GpioState.HIGH
            driver.GPIO.callbacks[1](1)

    driver.move = move
    driver.move_down = lambda distance_mm, speed_mm_s: None
    driver.wait_for_motor_done = lambda: None

    assert driver.do_limit_switch_homing(1, 2, 10.0, 2.0) is True
    assert stops
    assert driver.limit_switch_bindings == {}


def test_limit_switch_bindings_are_isolated_per_driver_instance():
    app_state = SimpleNamespace(
        mechanical_setup=object(),
        gpio=FakeHomingGPIO(),
        config=SimpleNamespace(USE_DUMMY_DRIVER=True),
    )
    first = MotorDriverTMC2209(app_state)
    second = MotorDriverTMC2209(app_state)

    first.bind_limit_switch(1, NC=True)

    assert first.limit_switch_bindings == {1: GpioEdge.RISING}
    assert second.limit_switch_bindings == {}


def test_cleanup_stops_worker_before_disabling_and_releasing_gpio():
    calls = []

    class CleanupTMC:
        def stop(self, mode):
            calls.append(("stop", mode))

        def wait_for_movement_finished_threaded(self):
            calls.append(("join",))

        def set_motor_enabled(self, enabled):
            calls.append(("enabled", enabled))

    class CleanupGPIO:
        def cleanup(self):
            calls.append(("gpio_cleanup",))

    driver = MotorDriverTMC2209.__new__(MotorDriverTMC2209)
    driver.tmc = CleanupTMC()
    driver.GPIO = CleanupGPIO()

    driver.cleanup()

    assert [call[0] for call in calls] == [
        "stop",
        "join",
        "enabled",
        "gpio_cleanup",
    ]
    assert calls[2] == ("enabled", False)
