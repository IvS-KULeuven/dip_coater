import threading
import math
from types import SimpleNamespace

import pytest

from dip_coater.gpio import GpioEdge, GpioState
from dip_coater.mechanical.mechanical_setup import MechanicalSetup
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


def test_cleanup_attempts_every_step_and_preserves_first_error():
    calls = []

    class FaultingCleanupTMC:
        def stop(self, mode):
            calls.append(("stop", mode))
            raise RuntimeError("stop failed")

        def wait_for_movement_finished_threaded(self):
            calls.append(("join",))
            raise RuntimeError("join failed")

        def set_motor_enabled(self, enabled):
            calls.append(("enabled", enabled))
            raise RuntimeError("disable failed")

    class FaultingCleanupGPIO:
        def cleanup(self):
            calls.append(("gpio_cleanup",))
            raise RuntimeError("gpio cleanup failed")

    driver = MotorDriverTMC2209.__new__(MotorDriverTMC2209)
    driver.tmc = FaultingCleanupTMC()
    driver.GPIO = FaultingCleanupGPIO()

    with pytest.raises(RuntimeError, match="stop failed"):
        driver.cleanup()

    assert [call[0] for call in calls] == [
        "stop",
        "join",
        "enabled",
        "gpio_cleanup",
    ]


def test_configured_speed_can_be_read_for_timeout_estimates():
    driver = MotorDriverTMC2209.__new__(MotorDriverTMC2209)
    driver.mechanical_setup = MechanicalSetup(mm_per_revolution=4.0)
    driver.microsteps = 8
    driver.tmc = SimpleNamespace(set_max_speed=lambda steps_per_second: None)

    driver.set_speed_rps(0.5)

    assert driver.get_speed_rps() == pytest.approx(0.5)


def test_stallguard_homing_restores_chopper_mode_after_failure():
    restored_modes = []

    class FaultingHomingTMC:
        def get_spreadcycle(self):
            return True

        def do_homing(self, **_kwargs):
            raise RuntimeError("homing failed")

        def set_spreadcycle(self, enabled):
            restored_modes.append(enabled)

    driver = MotorDriverTMC2209.__new__(MotorDriverTMC2209)
    driver.tmc = FaultingHomingTMC()
    driver.mechanical_setup = MechanicalSetup(mm_per_revolution=4.0)
    driver.diag_pin = 5

    with pytest.raises(RuntimeError, match="homing failed"):
        driver.do_stallguard_homing(speed_mm_s=2.0)

    assert restored_modes == [True]


def make_current_test_driver():
    driver = MotorDriverTMC2209.__new__(MotorDriverTMC2209)
    driver.current = 600.0
    driver.current_standstill = 100.0
    driver._min_current_mA = 31.0
    driver._max_current_mA = 2475.0
    driver.tmc = SimpleNamespace(set_current=lambda *_args, **_kwargs: None)
    return driver


@pytest.mark.parametrize(
    "current_mA",
    [0, -1, 2476, float("nan"), float("inf"), True, "600"],
)
def test_tmc2209_rejects_invalid_run_current(current_mA):
    driver = make_current_test_driver()

    with pytest.raises(ValueError, match="run current"):
        driver.set_current(current_mA)

    assert driver.current == 600.0


@pytest.mark.parametrize(
    "current_mA",
    [0, -1, 2476, float("nan"), float("inf"), True, "100"],
)
def test_tmc2209_rejects_invalid_standstill_current(current_mA):
    driver = make_current_test_driver()

    with pytest.raises(ValueError, match="standstill current"):
        driver.set_current_standstill(current_mA)

    assert driver.current_standstill == 100.0


def test_tmc2209_rejects_standstill_current_above_run_current():
    driver = make_current_test_driver()

    with pytest.raises(ValueError, match="must not exceed run current"):
        driver.set_current_standstill(700.0)

    with pytest.raises(ValueError, match="must not be below standstill current"):
        driver.set_current(50.0)


@pytest.mark.parametrize("method_name", ["set_current", "set_current_standstill"])
def test_tmc2209_current_cache_changes_only_after_uart_success(method_name):
    driver = make_current_test_driver()

    def fail_current(*_args, **_kwargs):
        raise RuntimeError("UART write failed")

    driver.tmc.set_current = fail_current
    original_run = driver.current
    original_standstill = driver.current_standstill

    with pytest.raises(RuntimeError, match="UART write failed"):
        getattr(driver, method_name)(500.0 if method_name == "set_current" else 50.0)

    assert driver.current == original_run
    assert driver.current_standstill == original_standstill


def test_tmc2209_current_setters_write_finite_hold_multiplier():
    calls = []
    driver = make_current_test_driver()
    driver.tmc.set_current = lambda *args, **kwargs: calls.append((args, kwargs))

    driver.set_current(500.0)
    driver.set_current_standstill(50.0)

    multipliers = [kwargs["hold_current_multiplier"] for _args, kwargs in calls]
    assert all(math.isfinite(value) and 0 <= value <= 1 for value in multipliers)
    assert multipliers == pytest.approx([0.2, 0.1])
