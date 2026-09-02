import asyncio
import json

import pytest
from textual.widgets import Button

from dip_coater.app import DipCoaterApp, initialize_runtime
from dip_coater.logging.session_log import SessionLog
from dip_coater.motor_driver.motor_driver_interface import AvailableMotorDrivers
from dip_coater.setup_profiles import (
    get_default_setup_for_driver,
    get_machine_profile,
)


async def _wait_for_state(app_state, expected: str, timeout_s: float = 3.0) -> None:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_s
    while app_state.motor_state != expected:
        if loop.time() >= deadline:
            raise AssertionError(
                f"motor state did not become {expected!r}; "
                f"last state was {app_state.motor_state!r}"
            )
        await asyncio.sleep(0.01)


def _session_events(path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def _dummy_runtime(driver_type, log_path):
    profile = get_machine_profile(get_default_setup_for_driver(driver_type))
    return initialize_runtime(
        driver_type,
        profile,
        use_dummy_driver=True,
        interface_type="dummy_tmcl",
        port=None,
        log_level_name="ERROR",
        session_log=SessionLog(log_path),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("driver_type", list(AvailableMotorDrivers))
async def test_full_app_dummy_driver_mounts_moves_and_shuts_down(
    driver_type,
    tmp_path,
):
    log_path = tmp_path / f"{driver_type.value}.jsonl"
    app_state = _dummy_runtime(driver_type, log_path)
    app = DipCoaterApp(app_state)

    try:
        async with app.run_test(size=(180, 60)) as pilot:
            for tab_id in (
                "main-tab",
                "logs-tab",
                "advanced-tab",
                "diagnostics-tab",
                "coder-tab",
            ):
                assert app.query_one(f"#{tab_id}")

            assert app_state.motor_driver.is_dummy is True
            assert app.query_one("#enable-motor", Button).disabled is False
            assert app.query_one("#move-up", Button).disabled is True

            await pilot.click("#enable-motor")
            await _wait_for_state(app_state, "enabled")

            app_state.distance_controls.set_distance(2.0)
            app_state.speed_controls.update_speed(5.0)
            await pilot.pause()

            await pilot.click("#move-up")
            await _wait_for_state(app_state, "moving")
            await _wait_for_state(app_state, "enabled")

            await pilot.click("#disable-motor")
            await _wait_for_state(app_state, "disabled")

            await pilot.press("q")
            await pilot.pause()
    finally:
        app_state.motion_controller.cleanup()

    events = [entry["event"] for entry in _session_events(log_path)]
    assert "session_started" in events
    assert "motion_requested" in events
    assert "motion_completed" in events
    assert "session_cleanup" in events


@pytest.mark.asyncio
async def test_full_tmc5160_app_completes_dummy_reference_homing(tmp_path):
    log_path = tmp_path / "tmc5160-homing.jsonl"
    app_state = _dummy_runtime(AvailableMotorDrivers.TMC5160, log_path)
    app = DipCoaterApp(app_state)

    try:
        async with app.run_test(size=(180, 60)) as pilot:
            await pilot.click("#enable-motor")
            await _wait_for_state(app_state, "enabled")

            assert app.query_one("#do-homing", Button).disabled is False
            await pilot.click("#do-homing")
            await _wait_for_state(app_state, "homing")
            await _wait_for_state(app_state, "enabled", timeout_s=6.0)

            assert app_state.homing_found is True
            assert app_state.motion_controller.is_homing_found() is True
            assert app.query_one("#move-to-position-btn", Button).disabled is False

            await pilot.press("q")
            await pilot.pause()
    finally:
        app_state.motion_controller.cleanup()

    events = _session_events(log_path)
    assert any(entry["event"] == "homing_requested" for entry in events)
    assert any(
        entry["event"] == "homing_completed" and entry["homing_found"] is True
        for entry in events
    )
