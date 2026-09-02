"""Supervised Raspberry Pi hardware checks for the TMC2209 driver."""

from __future__ import annotations

import os
import platform

import pytest
from TMC_2209._TMC_2209_logger import Loglevel

from dip_coater.app_state import AppState
from dip_coater.motor_driver.motor_driver_interface import AvailableMotorDrivers
from dip_coater.motor_driver.tmc2209 import MotorDriverTMC2209
from dip_coater.setup_profiles.machine_profile import AvailableMachineSetups
from dip_coater.setup_profiles.registry import get_machine_profile


pytestmark = pytest.mark.hardware


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


@pytest.fixture(scope="module")
def hardware_driver():
    if not _env_flag("DIP_COATER_TMC2209_HARDWARE"):
        pytest.skip(
            "Set DIP_COATER_TMC2209_HARDWARE=1 after checking the supervised bench."
        )
    if platform.system() != "Linux":
        pytest.skip("TMC2209 hardware tests require a Raspberry Pi Linux runner.")

    run_current_mA = int(os.environ.get("DIP_COATER_TMC2209_CURRENT_MA", "500"))
    hold_current_mA = int(
        os.environ.get("DIP_COATER_TMC2209_STANDSTILL_MA", "100")
    )
    if run_current_mA > 1000 or hold_current_mA > run_current_mA:
        pytest.fail(
            "Unsafe TMC2209 test currents: require hold <= run <= 1000 mA."
        )

    profile = get_machine_profile(AvailableMachineSetups.SMALL_COATER)
    app_state = AppState(
        AvailableMotorDrivers.TMC2209,
        profile,
        gpio_required=True,
    )
    driver = MotorDriverTMC2209(
        app_state,
        step_mode=8,
        current_mA=run_current_mA,
        current_standstill_mA=hold_current_mA,
        invert_direction=profile.invert_motor_direction,
        interpolation=True,
        spread_cycle=False,
        loglevel=Loglevel.INFO,
        log_handlers=[],
    )
    driver.disable_motor()
    try:
        yield driver
    finally:
        driver.cleanup()


def test_tmc2209_hardware_uart_and_microsteps_roundtrip(hardware_driver):
    assert hardware_driver.is_dummy is False

    hardware_driver.read_back_config()
    original = hardware_driver.get_microsteps()
    hardware_driver.set_microsteps(16)
    assert hardware_driver.get_microsteps() == 16
    hardware_driver.set_microsteps(original)


@pytest.mark.hardware_motion
def test_tmc2209_hardware_optional_motion(hardware_driver):
    if not _env_flag("DIP_COATER_TMC2209_RUN_MOTION"):
        pytest.skip("Set DIP_COATER_TMC2209_RUN_MOTION=1 to arm physical motion.")

    hardware_driver.enable_motor()
    try:
        start_steps = hardware_driver.tmc.get_current_position()
        hardware_driver.move_up(0.04, 0.4, 0.4)
        hardware_driver.wait_for_motor_done()
        end_steps = hardware_driver.tmc.get_current_position()
        assert end_steps != start_steps
    finally:
        hardware_driver.disable_motor()
