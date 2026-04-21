import importlib
import sys
import types
from types import SimpleNamespace

from dip_coater.logging.tmc5160_logger import TMC5160LogLevel
from dip_coater.mechanical.mechanical_setup import MechanicalSetup
from dip_coater.motor_driver.trinamic_adapter import TrinamicWrapperMotorAdapter
from dip_coater.setup_profiles.machine_profile import (
    AvailableMachineSetups,
    MachineProfile,
)
from trinamic_wrapper import StepMode


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


_driver_registry = importlib.import_module("dip_coater.motor_driver.driver_registry")
_create_tmc5160_driver = _driver_registry._create_tmc5160_driver


class FakeConn:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class FakeMotor:
    def __init__(self):
        self.run_current = None
        self.standstill_current = None
        self.step_mode = None
        self.accel = None
        self.interpolation = None
        self.disabled = False

    def set_run_current_mA(self, current_mA):
        self.run_current = current_mA

    def set_standstill_current_mA(self, current_mA):
        self.standstill_current = current_mA

    def set_step_mode(self, mode):
        self.step_mode = mode

    def set_acceleration_rps2(self, accel):
        self.accel = accel

    def set_interpolation(self, enabled):
        self.interpolation = enabled

    def disable(self):
        self.disabled = True


def _make_app_state():
    profile = MachineProfile(
        key=AvailableMachineSetups.CUSTOM,
        label="Custom",
        mechanical_setup=MechanicalSetup(
            mm_per_revolution=4.0,
            gearbox_ratio=1.5,
            steps_per_revolution=400,
        ),
        invert_motor_direction=True,
    )
    config = SimpleNamespace(
        USE_DUMMY_DRIVER=False,
        DEFAULT_STEP_MODE="I16",
        STEP_MODES={"I2": 2, "I4": 4, "I16": 16, "I256": 256},
        DEFAULT_CURRENT=2500,
        DEFAULT_CURRENT_STANDSTILL=70,
        DEFAULT_ACCELERATION=10,
        USE_INTERPOLATION=True,
        DEFAULT_RSENSE=75,
        MAX_CURRENT=4000,
    )
    return SimpleNamespace(
        config=config,
        setup_profile=profile,
        mechanical_setup=profile.mechanical_setup,
    )


def test_create_tmc5160_driver_uses_trinamic_wrapper_adapter(monkeypatch):
    app_state = _make_app_state()
    fake_conn = FakeConn()
    fake_motor = FakeMotor()

    captured = {}

    def fake_open_connection(*, port=None, interface="usb_tmcl", datarate=None):
        captured["open_connection"] = {
            "port": port,
            "interface": interface,
            "datarate": datarate,
        }
        return SimpleNamespace(connect=lambda: fake_conn)

    def fake_create_motor(chip, connection, *, config, module_id=1, axis=0):
        captured["create_motor"] = {
            "chip": chip,
            "connection": connection,
            "config": config,
            "module_id": module_id,
            "axis": axis,
        }
        return fake_motor

    monkeypatch.setattr(
        "dip_coater.motor_driver.driver_registry.open_connection",
        fake_open_connection,
    )
    monkeypatch.setattr(
        "dip_coater.motor_driver.driver_registry.create_motor",
        fake_create_motor,
    )

    driver = _create_tmc5160_driver(
        app_state,
        log_level=TMC5160LogLevel.INFO,
        log_handlers=[],
        log_formatter=None,
        interface_type="usb_tmcl",
        port="/dev/tty.test",
    )

    assert isinstance(driver, TrinamicWrapperMotorAdapter)
    assert captured["open_connection"] == {
        "port": "/dev/tty.test",
        "interface": "usb_tmcl",
        "datarate": None,
    }
    assert captured["create_motor"]["connection"] is fake_conn
    assert captured["create_motor"]["config"].full_steps_per_rev == 400
    assert captured["create_motor"]["config"].sense_resistor_ohms == 0.075
    assert captured["create_motor"]["config"].default_microsteps == StepMode.USTEP_16
    assert captured["create_motor"]["config"].max_current_mA_limit == 4000
    assert fake_motor.run_current == 2500
    assert fake_motor.standstill_current == 70
    assert fake_motor.step_mode == StepMode.USTEP_16
    assert fake_motor.accel == 10 / 4.0 / 1.5
    assert fake_motor.interpolation is True

    driver.cleanup()
    assert fake_motor.disabled is True
    assert fake_conn.closed is True
