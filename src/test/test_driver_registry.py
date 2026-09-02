import importlib
import logging
import sys
import types
from types import SimpleNamespace

import pytest

from dip_coater.logging.tmc5160_logger import TMC5160LogLevel
from dip_coater.mechanical.mechanical_setup import MechanicalSetup
from dip_coater.config import config_tmc5160
from dip_coater.motor_driver.trinamic_adapter import TrinamicWrapperMotorAdapter
from dip_coater.setup_profiles.machine_profile import (
    AvailableMachineSetups,
    MachineProfile,
)
from dip_coater.setup_profiles.registry import get_machine_profile
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
_prepare_tmc5160_motor_for_startup = (
    _driver_registry._prepare_tmc5160_motor_for_startup
)


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
        self.chopper_mode = None
        self.stealthchop = None
        self.stealthchop_threshold = None
        self.stallguard_threshold = None
        self.stallguard_enabled = None
        self.stallguard_filter_enabled = None
        self.coolstep_threshold = None
        self.coolstep_enabled = None
        self.reference_stops = None
        self.reference_stop_calls = []
        self.disabled = False
        self.rotate_calls = []
        self.stop_calls = 0
        self.position_reads = 0
        self.speed_reads = 0

    def set_run_current_mA(self, current_mA):
        self.run_current = current_mA

    def set_standstill_current_mA(self, current_mA):
        self.standstill_current = current_mA

    def set_step_mode(self, mode):
        self.step_mode = mode

    def get_step_mode(self):
        return self.step_mode

    def set_interpolation(self, enabled):
        self.interpolation = enabled

    def set_chopper_mode(self, mode):
        self.chopper_mode = mode

    def set_stealthchop(self, enabled, threshold_rps=None):
        self.stealthchop = enabled
        self.stealthchop_threshold = threshold_rps

    def set_stallguard_threshold(self, threshold):
        self.stallguard_threshold = threshold

    def set_stallguard_enabled(self, enabled):
        self.stallguard_enabled = enabled

    def set_stallguard_filter_enabled(self, enabled):
        self.stallguard_filter_enabled = enabled

    def set_coolstep_threshold_raw(self, threshold):
        self.coolstep_threshold = threshold

    def set_coolstep_enabled(self, enabled):
        self.coolstep_enabled = enabled

    def enable_reference_stops(self, *, left=True, right=True):
        self.reference_stops = (left, right)
        self.reference_stop_calls.append((left, right))

    def set_speed_rps(self, speed_rps):
        self.speed_rps = speed_rps

    def disable(self):
        self.disabled = True

    def stop(self):
        self.stop_calls += 1

    def set_acceleration_rps2(self, accel_rps2):
        self.accel = accel_rps2

    def rotate_by(self, revolutions, direction):
        self.rotate_calls.append((revolutions, direction))

    def wait_until_reached(self, timeout_s=None):
        return True

    def get_actual_position_rot(self):
        self.position_reads += 1
        return 0.0

    def get_actual_speed_rps(self):
        self.speed_reads += 1
        return 0.0


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
        USE_SPREAD_CYCLE=False,
        DEFAULT_RSENSE=75,
        MAX_CURRENT=4000,
        DEFAULT_CHOPPER_MODE="SpreadCycle",
        VSENSE_FULL_SCALE=object(),
        DEFAULT_STEP_DIR_SOURCE=object(),
    )
    return SimpleNamespace(
        config=config,
        setup_profile=profile,
        mechanical_setup=profile.mechanical_setup,
    )


def test_create_tmc5160_driver_uses_trinamic_wrapper_adapter(monkeypatch):
    app_state = _make_app_state()
    app_state.setup_profile = _driver_registry.get_driver_spec(
        "TMC5160"
    ).adjust_setup_profile(app_state.setup_profile)
    setup_profile_before_factory = app_state.setup_profile
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
    assert driver.is_dummy is False
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
    assert app_state.setup_profile is setup_profile_before_factory
    assert app_state.setup_profile.invert_motor_direction is False
    assert fake_motor.run_current == 2500
    assert fake_motor.standstill_current == 70
    assert fake_motor.step_mode == StepMode.USTEP_16
    assert fake_motor.accel == 10 / 4.0 * 1.5
    assert fake_motor.interpolation is True
    assert fake_motor.chopper_mode == 0
    assert fake_motor.stealthchop is False
    assert fake_motor.stealthchop_threshold is None
    assert fake_motor.stallguard_threshold == 0
    assert fake_motor.stallguard_enabled is True
    assert fake_motor.stallguard_filter_enabled is True
    assert fake_motor.coolstep_threshold == 0
    assert fake_motor.coolstep_enabled is False
    assert fake_motor.reference_stops == (True, True)
    assert fake_motor.stop_calls == 1
    assert fake_motor.disabled is True
    assert fake_motor.position_reads == 1
    assert fake_motor.speed_reads == 1
    assert fake_motor.reference_stop_calls == [(False, False), (True, True)]

    driver.move_up(4.0, 1.0)
    assert fake_motor.rotate_calls[-1][1].name == "CW"

    driver.cleanup()
    assert fake_motor.disabled is True
    assert fake_conn.closed is True


def test_tmc5160_startup_attempts_all_safety_actions_after_stop_failure():
    calls = []

    class FaultingStartupMotor:
        def stop(self):
            calls.append("stop")
            raise RuntimeError("stop failed")

        def disable(self):
            calls.append("disable")

        def enable_reference_stops(self, *, left, right):
            calls.append(("reference_stops", left, right))

        def get_actual_position_rot(self):
            calls.append("position")
            return 0.0

        def get_actual_speed_rps(self):
            calls.append("speed")
            return 0.0

    logger = SimpleNamespace(error=lambda _message: None)

    with pytest.raises(RuntimeError, match="startup initialization failed"):
        _prepare_tmc5160_motor_for_startup(FaultingStartupMotor(), logger)

    assert calls == [
        "stop",
        "disable",
        ("reference_stops", False, False),
        "position",
        "speed",
    ]


def test_create_tmc5160_driver_closes_connection_after_configuration_failure(
    monkeypatch,
):
    app_state = _make_app_state()
    app_state.setup_profile = _driver_registry.get_driver_spec(
        "TMC5160"
    ).adjust_setup_profile(app_state.setup_profile)
    fake_conn = FakeConn()

    class FaultingMotor(FakeMotor):
        def set_run_current_mA(self, current_mA):
            raise RuntimeError("current configuration failed")

    monkeypatch.setattr(
        "dip_coater.motor_driver.driver_registry.open_connection",
        lambda **_kwargs: SimpleNamespace(connect=lambda: fake_conn),
    )
    monkeypatch.setattr(
        "dip_coater.motor_driver.driver_registry.create_motor",
        lambda *_args, **_kwargs: FaultingMotor(),
    )

    with pytest.raises(RuntimeError, match="current configuration failed"):
        _create_tmc5160_driver(
            app_state,
            log_level=TMC5160LogLevel.INFO,
            log_handlers=[],
            log_formatter=None,
            interface_type="usb_tmcl",
            port="/dev/tty.test",
        )

    assert fake_conn.closed is True


def test_tmc5160_startup_failure_detaches_owned_log_handlers(monkeypatch):
    app_state = _make_app_state()
    app_state.setup_profile = _driver_registry.get_driver_spec(
        "TMC5160"
    ).adjust_setup_profile(app_state.setup_profile)
    handler = logging.NullHandler()
    logger = logging.getLogger("TMC5160")

    class FaultingMotor(FakeMotor):
        def set_run_current_mA(self, current_mA):
            raise RuntimeError("current configuration failed")

    monkeypatch.setattr(
        "dip_coater.motor_driver.driver_registry.open_connection",
        lambda **_kwargs: SimpleNamespace(connect=FakeConn),
    )
    monkeypatch.setattr(
        "dip_coater.motor_driver.driver_registry.create_motor",
        lambda *_args, **_kwargs: FaultingMotor(),
    )

    try:
        with pytest.raises(RuntimeError, match="current configuration failed"):
            _create_tmc5160_driver(
                app_state,
                log_level=TMC5160LogLevel.INFO,
                log_handlers=[handler],
                log_formatter=None,
                interface_type="usb_tmcl",
                port="/dev/tty.test",
            )

        assert handler not in logger.handlers
    finally:
        logger.removeHandler(handler)


@pytest.mark.parametrize(
    ("factory_name", "driver_type_name", "logger_name"),
    [
        ("_create_tmc2209_driver", "MotorDriverTMC2209", "TMC2209"),
        ("_create_tmc2660_driver", "MotorDriverTMC2660", "TMC2660"),
    ],
)
def test_legacy_startup_failure_detaches_owned_log_handlers(
    monkeypatch,
    factory_name,
    driver_type_name,
    logger_name,
):
    app_state = _make_app_state()
    handler = logging.NullHandler()
    logger = logging.getLogger(logger_name)

    def fail_constructor(*_args, **_kwargs):
        logger.addHandler(handler)
        raise RuntimeError("driver construction failed")

    monkeypatch.setattr(_driver_registry, driver_type_name, fail_constructor)

    try:
        with pytest.raises(RuntimeError, match="driver construction failed"):
            getattr(_driver_registry, factory_name)(
                app_state,
                log_level=TMC5160LogLevel.INFO,
                log_handlers=[handler],
                log_formatter=None,
            )

        assert handler not in logger.handlers
    finally:
        logger.removeHandler(handler)


def test_create_tmc5160_dummy_driver_uses_wrapper_adapter(monkeypatch):
    app_state = _make_app_state()
    app_state.setup_profile = _driver_registry.get_driver_spec(
        "TMC5160"
    ).adjust_setup_profile(app_state.setup_profile)
    setup_profile_before_factory = app_state.setup_profile
    app_state.config.USE_DUMMY_DRIVER = True

    def fail_open_connection(*args, **kwargs):
        raise AssertionError("dummy TMC5160 driver should not open hardware")

    monkeypatch.setattr(
        "dip_coater.motor_driver.driver_registry.open_connection",
        fail_open_connection,
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
    assert driver.is_dummy is True
    assert app_state.setup_profile is setup_profile_before_factory
    assert app_state.setup_profile.invert_motor_direction is False

    driver.enable_motor()
    driver.move_up(0.04, 80.0, 2.0)
    driver.wait_for_motor_done()

    assert driver.get_current_position_mm() == pytest.approx(0.04)
    assert driver.get_current() == pytest.approx(2500)
    assert driver.get_current_standstill() == pytest.approx(70)


def test_tmc5160_reference_stops_default_to_both_limits_enabled():
    assert config_tmc5160.DEFAULT_REFERENCE_LEFT_STOP_ENABLED is True
    assert config_tmc5160.DEFAULT_REFERENCE_RIGHT_STOP_ENABLED is True


def test_tmc5160_setup_adjustment_normalizes_direction_without_mutating_input():
    spec = _driver_registry.get_driver_spec("TMC5160")
    profile = _make_app_state().setup_profile

    adjusted = spec.adjust_setup_profile(profile)

    assert profile.invert_motor_direction is True
    assert adjusted.invert_motor_direction is False
    assert adjusted is not profile


def test_real_tmc2660_rejects_driver_reference_limit_switches():
    profile = get_machine_profile(AvailableMachineSetups.LARGE_COATER)

    with pytest.raises(ValueError, match="cannot read driver-reference"):
        _driver_registry.validate_driver_setup_compatibility(
            _driver_registry.AvailableMotorDrivers.TMC2660,
            profile,
            use_dummy_driver=False,
        )


def test_tmc2660_compatibility_allows_dummy_and_gpio_profiles():
    large_profile = get_machine_profile(AvailableMachineSetups.LARGE_COATER)
    small_profile = get_machine_profile(AvailableMachineSetups.SMALL_COATER)

    _driver_registry.validate_driver_setup_compatibility(
        _driver_registry.AvailableMotorDrivers.TMC2660,
        large_profile,
        use_dummy_driver=True,
    )
    _driver_registry.validate_driver_setup_compatibility(
        _driver_registry.AvailableMotorDrivers.TMC2660,
        small_profile,
        use_dummy_driver=False,
    )
