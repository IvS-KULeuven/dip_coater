import os
from types import SimpleNamespace

import pytest

from dip_coater.mechanical.mechanical_setup import MechanicalSetup
from dip_coater.motor_driver.tmc5160 import MotorDriverTMC5160


class HardwareAppState:
    def __init__(self):
        self.mechanical_setup = MechanicalSetup(mm_per_revolution=4.0)
        self.config = SimpleNamespace(
            USE_DUMMY_DRIVER=False,
            DEFAULT_GLOBAL_SCALER=0,
            DEFAULT_RSENSE=50,
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
    global_scaler = int(os.getenv("DIP_COATER_TMC5160_GLOBAL_SCALER", "0"))
    rsense_mOhm = int(os.getenv("DIP_COATER_TMC5160_RSENSE_MOHM", "50"))

    driver = MotorDriverTMC5160(
        HardwareAppState(),
        interface_type=interface_type,
        port=port,
        step_mode=step_mode,
        current_mA=current_mA,
        current_standstill_mA=current_standstill_mA,
        global_scaler=global_scaler,
        rsense_mOhm=rsense_mOhm,
    )
    try:
        yield driver
    finally:
        driver.cleanup()


@pytest.mark.hardware
def test_tmc5160_hardware_basic_register_access(hardware_driver):
    assert isinstance(hardware_driver.read_drv_status(), int)
    assert isinstance(hardware_driver.read_ramp_status(), int)
    assert hardware_driver.get_microsteps() > 0


@pytest.mark.hardware
def test_tmc5160_hardware_current_register_roundtrip(hardware_driver):
    run_current_mA = int(os.getenv("DIP_COATER_TMC5160_CURRENT_MA", "500"))
    hold_current_mA = int(os.getenv("DIP_COATER_TMC5160_STANDSTILL_NONZERO_MA", "140"))

    hardware_driver.set_current(run_current_mA)
    assert hardware_driver.get_current() == hardware_driver._convert_current_to_cs(run_current_mA)

    hardware_driver.set_current_standstill(hold_current_mA)
    assert (
        hardware_driver.get_current_standstill()
        == hardware_driver._convert_current_to_cs(hold_current_mA)
    )


@pytest.mark.hardware
def test_tmc5160_hardware_microsteps_roundtrip(hardware_driver):
    original = hardware_driver.get_microsteps()

    hardware_driver.set_microsteps(16)
    assert hardware_driver.get_microsteps() == 16

    hardware_driver.set_microsteps(32)
    assert hardware_driver.get_microsteps() == 32

    hardware_driver.set_microsteps(original)


@pytest.mark.hardware
def test_tmc5160_hardware_optional_motion(hardware_driver):
    if not _env_flag("DIP_COATER_TMC5160_RUN_MOTION"):
        pytest.skip("Set DIP_COATER_TMC5160_RUN_MOTION=1 to run the motion smoke test.")

    hardware_driver.enable_motor()
    start = hardware_driver.get_actual_position()
    hardware_driver.rotate(0.01, 0.1, 0.1)
    hardware_driver.wait_for_motor_done()
    end = hardware_driver.get_actual_position()
    assert end != start
