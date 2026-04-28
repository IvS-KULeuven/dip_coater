import os
from types import SimpleNamespace

import pytest

from dip_coater.logging.tmc5160_logger import TMC5160LogLevel
from dip_coater.mechanical.mechanical_setup import MechanicalSetup
from dip_coater.motor_driver.driver_registry import get_driver_spec
from dip_coater.motor_driver.motor_driver_interface import AvailableMotorDrivers
from dip_coater.motor_driver.trinamic_adapter import TrinamicWrapperMotorAdapter
from dip_coater.setup_profiles.machine_profile import (
    AvailableMachineSetups,
    MachineProfile,
)


class HardwareAppState:
    def __init__(
        self,
        *,
        step_mode: int,
        current_mA: int,
        hold_current_mA: int,
        rsense_mOhm: int,
    ):
        mechanical_setup = MechanicalSetup(mm_per_revolution=4.0)
        self.setup_profile = MachineProfile(
            key=AvailableMachineSetups.CUSTOM,
            label="TMC5160 hardware test",
            mechanical_setup=mechanical_setup,
        )
        self.mechanical_setup = mechanical_setup
        self.config = SimpleNamespace(
            USE_DUMMY_DRIVER=False,
            DEFAULT_STEP_MODE=f"I{step_mode}",
            STEP_MODES={"I2": 2, "I4": 4, "I16": 16, "I256": 256},
            DEFAULT_CURRENT=current_mA,
            DEFAULT_CURRENT_STANDSTILL=hold_current_mA,
            DEFAULT_ACCELERATION=10.0,
            USE_INTERPOLATION=True,
            DEFAULT_RSENSE=rsense_mOhm,
            MAX_CURRENT=4000,
        )


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


@pytest.fixture(scope="module")
def hardware_driver():
    port = os.getenv("DIP_COATER_TMC5160_PORT")
    if not port:
        pytest.skip("Set DIP_COATER_TMC5160_PORT to run TMC5160 hardware tests.")

    interface_type = os.getenv("DIP_COATER_TMC5160_INTERFACE", "usb_tmcl")
    step_mode = int(os.getenv("DIP_COATER_TMC5160_STEP_MODE", "16"))
    current_mA = int(os.getenv("DIP_COATER_TMC5160_CURRENT_MA", "500"))
    current_standstill_mA = int(os.getenv("DIP_COATER_TMC5160_STANDSTILL_MA", "0"))
    rsense_mOhm = int(os.getenv("DIP_COATER_TMC5160_RSENSE_MOHM", "75"))

    app_state = HardwareAppState(
        step_mode=step_mode,
        current_mA=current_mA,
        hold_current_mA=current_standstill_mA,
        rsense_mOhm=rsense_mOhm,
    )
    driver_spec = get_driver_spec(AvailableMotorDrivers.TMC5160)
    driver = driver_spec.driver_factory(
        app_state=app_state,
        log_level=TMC5160LogLevel.INFO,
        log_handlers=[],
        log_formatter=None,
        interface_type=interface_type,
        port=port,
    )
    try:
        yield driver
    finally:
        driver.cleanup()


@pytest.mark.hardware
def test_tmc5160_hardware_uses_trinamic_wrapper_adapter(hardware_driver):
    assert isinstance(hardware_driver, TrinamicWrapperMotorAdapter)
    assert hardware_driver.get_microsteps() > 0


@pytest.mark.hardware
def test_tmc5160_hardware_current_roundtrip(hardware_driver):
    run_current_mA = int(os.getenv("DIP_COATER_TMC5160_CURRENT_MA", "500"))
    hold_current_mA = int(os.getenv("DIP_COATER_TMC5160_STANDSTILL_NONZERO_MA", "140"))

    hardware_driver.set_current(run_current_mA)
    assert hardware_driver.get_current() == pytest.approx(run_current_mA, abs=120)

    hardware_driver.set_current_standstill(hold_current_mA)
    assert hardware_driver.get_current_standstill() == pytest.approx(
        hold_current_mA, abs=120
    )


@pytest.mark.hardware
def test_tmc5160_hardware_microsteps_roundtrip(hardware_driver):
    original = hardware_driver.get_microsteps()

    hardware_driver.set_microsteps(16)
    assert hardware_driver.get_microsteps() == 16

    hardware_driver.set_microsteps(256)
    assert hardware_driver.get_microsteps() == 256

    hardware_driver.set_microsteps(original)


@pytest.mark.hardware
def test_tmc5160_hardware_optional_motion(hardware_driver):
    if not _env_flag("DIP_COATER_TMC5160_RUN_MOTION"):
        pytest.skip("Set DIP_COATER_TMC5160_RUN_MOTION=1 to run the motion smoke test.")

    hardware_driver.enable_motor()
    start = hardware_driver.get_current_position_mm()
    hardware_driver.move_up(0.04, 0.4, 0.4)
    hardware_driver.wait_for_motor_done()
    end = hardware_driver.get_current_position_mm()
    assert end != start
