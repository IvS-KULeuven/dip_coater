import sys
import types
from types import SimpleNamespace

import pytest

if "TMC_2209._TMC_2209_logger" not in sys.modules:
    fake_logger_module = types.ModuleType("TMC_2209._TMC_2209_logger")

    class Loglevel:
        INFO = SimpleNamespace(name="INFO", value=20)

    fake_logger_module.Loglevel = Loglevel
    sys.modules["TMC_2209"] = types.ModuleType("TMC_2209")
    sys.modules["TMC_2209._TMC_2209_logger"] = fake_logger_module

if "dip_coater.motor_driver.tmc2209" not in sys.modules:
    fake_tmc2209_module = types.ModuleType("dip_coater.motor_driver.tmc2209")

    class MotorDriverTMC2209:
        pass

    fake_tmc2209_module.MotorDriverTMC2209 = MotorDriverTMC2209
    sys.modules["dip_coater.motor_driver.tmc2209"] = fake_tmc2209_module

from dip_coater.logging.tmc5160_logger import TMC5160LogLevel
from dip_coater.mechanical.mechanical_setup import MechanicalSetup
from dip_coater.motor_driver.driver_registry import get_driver_spec
from dip_coater.motor_driver.motor_driver_interface import AvailableMotorDrivers
from dip_coater.motor_driver.trinamic_adapter import TrinamicWrapperMotorAdapter
from dip_coater.setup_profiles.machine_profile import (
    AvailableMachineSetups,
    MachineProfile,
)
from trinamic_wrapper import OutOfRangeError


class DummyAppState:
    def __init__(self, *, invert_motor_direction: bool = True):
        mechanical_setup = MechanicalSetup(mm_per_revolution=4.0)
        self.setup_profile = MachineProfile(
            key=AvailableMachineSetups.CUSTOM,
            label="Wrapper TMC5160 dummy",
            mechanical_setup=mechanical_setup,
            invert_motor_direction=invert_motor_direction,
        )
        self.mechanical_setup = mechanical_setup
        self.config = SimpleNamespace(
            USE_DUMMY_DRIVER=True,
            DEFAULT_STEP_MODE="I16",
            STEP_MODES={"I2": 2, "I4": 4, "I16": 16, "I256": 256},
            DEFAULT_CURRENT=1500,
            DEFAULT_CURRENT_STANDSTILL=100,
            DEFAULT_ACCELERATION=10.0,
            USE_INTERPOLATION=True,
            DEFAULT_RSENSE=75,
            MAX_CURRENT=4000,
        )


def _make_driver(app_state: DummyAppState | None = None) -> TrinamicWrapperMotorAdapter:
    spec = get_driver_spec(AvailableMotorDrivers.TMC5160)
    return spec.driver_factory(
        app_state=app_state or DummyAppState(),
        log_level=TMC5160LogLevel.INFO,
        log_handlers=[],
        log_formatter=None,
        interface_type="usb_tmcl",
        port="/dev/tty.should-not-open",
    )


def test_tmc5160_dummy_driver_uses_wrapper_adapter():
    driver = _make_driver()

    assert isinstance(driver, TrinamicWrapperMotorAdapter)
    assert driver.get_microsteps() == 16
    assert driver.get_current() == pytest.approx(1500)
    assert driver.get_current_standstill() == pytest.approx(100)


def test_tmc5160_dummy_driver_supports_basic_motion():
    driver = _make_driver()

    driver.enable_motor()
    driver.move_up(8.0, 2.0)
    driver.wait_for_motor_done()
    assert driver.get_current_position_mm() == pytest.approx(8.0)

    driver.run_to_position(3.0, 1.0)
    driver.wait_for_motor_done()
    assert driver.get_current_position_mm() == pytest.approx(3.0)


def test_tmc5160_dummy_driver_defaults_reference_switches_to_open():
    driver = _make_driver()

    assert driver.get_left_endstop() is True
    assert driver.get_right_endstop() is True


def test_tmc5160_dummy_driver_supports_direction_inversion():
    driver = _make_driver()

    driver.invert_direction(True)
    driver.move_up(4.0, 1.0)

    assert driver.get_current_position_mm() == pytest.approx(-4.0)


def test_tmc5160_dummy_driver_validates_limits():
    driver = _make_driver()

    with pytest.raises(OutOfRangeError):
        driver.set_current(4001)


def test_tmc5160_dummy_driver_cleanup_disables_motor():
    driver = _make_driver()
    driver.enable_motor()

    driver.cleanup()

    assert driver._motor.is_enabled is False
