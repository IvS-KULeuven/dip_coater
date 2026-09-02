import threading

import pytest

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
