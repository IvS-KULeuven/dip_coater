from contextlib import ExitStack
from dataclasses import dataclass
from typing import Any, Callable

from TMC_2209._TMC_2209_logger import Loglevel
from trinamic_wrapper import (
    Chip,
    DummyStepperMotor,
    MotorConfig,
    StepMode,
    create_motor,
    open_connection,
)

from dip_coater.logging.tmc2660_logger import TMC2660LogLevel
from dip_coater.logging.tmc5160_logger import TMC5160Logger
from dip_coater.logging.tmc5160_logger import TMC5160LogLevel
from dip_coater.motor_driver import TrinamicWrapperMotorAdapter
from dip_coater.motor_driver.motor_driver_interface import AvailableMotorDrivers, MotorDriver
from dip_coater.motor_driver.tmc2209 import MotorDriverTMC2209
from dip_coater.motor_driver.tmc2660 import (
    MotorDriverTMC2660,
    TMC2660LogLevel as TMC2660DriverLogLevel,
)
from dip_coater.setup_profiles.machine_profile import (
    AvailableMachineSetups,
    MachineProfile,
)
from dip_coater.widgets.advanced.advanced_settings_tmc2209 import (
    AdvancedSettingsTMC2209,
)
from dip_coater.widgets.advanced.advanced_settings_tmc2660 import (
    AdvancedSettingsTMC2660,
)
from dip_coater.widgets.advanced.advanced_settings_trinamic_tmc5160 import (
    AdvancedSettingsTrinamicTMC5160,
)
from dip_coater.widgets.advanced.status_advanced_tmc2209 import StatusAdvancedTMC2209
from dip_coater.widgets.advanced.status_advanced_tmc2660 import StatusAdvancedTMC2660
from dip_coater.widgets.advanced.status_advanced_trinamic_tmc5160 import (
    StatusAdvancedTrinamicTMC5160,
)


_MICROSTEPS_TO_STEP_MODE = {
    1: StepMode.FULLSTEP,
    2: StepMode.USTEP_2,
    4: StepMode.USTEP_4,
    8: StepMode.USTEP_8,
    16: StepMode.USTEP_16,
    32: StepMode.USTEP_32,
    64: StepMode.USTEP_64,
    128: StepMode.USTEP_128,
    256: StepMode.USTEP_256,
}


@dataclass(frozen=True)
class MotorDriverSpec:
    """Factory metadata for one supported motor driver.

    :param driver_type: Driver enum value represented by this spec.
    :param requires_gpio: Whether the driver itself needs GPIO access.
    :param default_setup: Default machine setup used with this driver.
    :param driver_factory: Callable that builds the concrete driver instance.
    :param log_level_from_name: Callable that resolves a log-level name.
    :param log_level_options: Callable that returns selectable log-level options.
    :param create_advanced_settings: Callable that creates the advanced-settings widget.
    :param create_advanced_status: Callable that creates the advanced-status widget.
    :param adjust_setup_profile: Callable that normalizes a selected machine profile.
    :param supports_driver_reference_switches: Whether the backend can read
        reference inputs wired directly to the motor driver.
    """

    driver_type: AvailableMotorDrivers
    requires_gpio: bool
    default_setup: AvailableMachineSetups
    driver_factory: Callable[..., MotorDriver]
    log_level_from_name: Callable[[str], Any]
    log_level_options: Callable[[], list[tuple[str, str]]]
    create_advanced_settings: Callable[[Any], Any]
    create_advanced_status: Callable[[Any], Any]
    adjust_setup_profile: Callable[[MachineProfile], MachineProfile] = (
        lambda profile: profile
    )
    supports_driver_reference_switches: bool = False


def _normalize_tmc5160_setup_profile(profile: MachineProfile) -> MachineProfile:
    # The legacy dip_coater TMC5160 path and the wrapper-backed path use
    # opposite effective motion signs for the same machine profile. Keep the
    # physical UP/DOWN behavior consistent by normalizing the selected profile
    # before app state, UI defaults, and motion services are created.
    return profile.with_overrides(
        invert_motor_direction=not profile.invert_motor_direction
    )


def _create_tmc2209_driver(
    app_state,
    *,
    log_level,
    log_handlers,
    log_formatter,
    interface_type="usb_tmcl",
    port="interactive",
) -> MotorDriver:
    return MotorDriverTMC2209(
        app_state,
        step_mode=app_state.config.STEP_MODES[app_state.config.DEFAULT_STEP_MODE],
        current_mA=app_state.config.DEFAULT_CURRENT,
        current_standstill_mA=app_state.config.DEFAULT_CURRENT_STANDSTILL,
        invert_direction=app_state.setup_profile.invert_motor_direction,
        interpolation=app_state.config.USE_INTERPOLATION,
        spread_cycle=app_state.config.USE_SPREAD_CYCLE,
        loglevel=log_level,
        log_handlers=log_handlers,
        log_formatter=log_formatter,
    )


def _create_tmc2660_driver(
    app_state,
    *,
    log_level,
    log_handlers,
    log_formatter,
    interface_type="usb_tmcl",
    port="interactive",
) -> MotorDriver:
    if app_state.config.USE_DUMMY_DRIVER:
        interface_type = "dummy_tmcl"
        port = None
    return MotorDriverTMC2660(
        app_state,
        interface_type=interface_type,
        port=port,
        step_mode=app_state.config.STEP_MODES[app_state.config.DEFAULT_STEP_MODE],
        current_mA=app_state.config.DEFAULT_CURRENT,
        current_standstill_mA=app_state.config.DEFAULT_CURRENT_STANDSTILL,
        invert_direction=app_state.setup_profile.invert_motor_direction,
        chopper_mode=app_state.config.DEFAULT_CHOPPER_MODE,
        vsense_full_scale=app_state.config.VSENSE_FULL_SCALE,
        step_dir_source=app_state.config.DEFAULT_STEP_DIR_SOURCE,
        loglevel=log_level,
        log_handlers=log_handlers,
        log_formatter=log_formatter,
    )


def _create_tmc5160_driver(
    app_state,
    *,
    log_level,
    log_handlers,
    log_formatter,
    interface_type="usb_tmcl",
    port="interactive",
) -> MotorDriver:
    microsteps = app_state.config.STEP_MODES[app_state.config.DEFAULT_STEP_MODE]
    step_mode = _MICROSTEPS_TO_STEP_MODE[microsteps]
    setup = app_state.setup_profile.mechanical_setup
    config = MotorConfig(
        full_steps_per_rev=setup.steps_per_revolution,
        sense_resistor_ohms=app_state.config.DEFAULT_RSENSE / 1000.0,
        default_microsteps=step_mode,
        max_current_mA_limit=app_state.config.MAX_CURRENT,
    )
    logger = TMC5160Logger(
        loglevel=log_level,
        handlers=log_handlers,
        formatter=log_formatter,
    ).logger

    connection = None
    with ExitStack() as failed_startup_cleanup:
        if app_state.config.USE_DUMMY_DRIVER:
            motor = DummyStepperMotor(config)
        else:
            connection = open_connection(
                port=port, interface=interface_type
            ).connect()
            failed_startup_cleanup.callback(
                _close_after_failed_startup, connection.close
            )
            motor = create_motor(Chip.TMC5160, connection, config=config)
        _prepare_tmc5160_motor_for_startup(motor, logger)
        motor.set_run_current_mA(app_state.config.DEFAULT_CURRENT)
        motor.set_standstill_current_mA(app_state.config.DEFAULT_CURRENT_STANDSTILL)
        motor.set_step_mode(step_mode)
        motor.set_acceleration_rps2(
            setup.mm_s2_to_rpss(app_state.config.DEFAULT_ACCELERATION)
        )
        motor.set_interpolation(app_state.config.USE_INTERPOLATION)
        adapter = TrinamicWrapperMotorAdapter(
            motor,
            setup,
            invert_direction=app_state.setup_profile.invert_motor_direction,
            is_dummy=app_state.config.USE_DUMMY_DRIVER,
            close=connection.close if connection is not None else None,
            logger=logger,
        )
        adapter.set_chopper_mode(
            getattr(app_state.config, "DEFAULT_CHOPPER_MODE", "SpreadCycle")
        )
        adapter.set_stealthchop_threshold(
            getattr(app_state.config, "DEFAULT_STEALTHCHOP_THRESHOLD_RPS", 0.0)
        )
        adapter.set_stealthchop_enabled(
            getattr(app_state.config, "DEFAULT_STEALTHCHOP_ENABLED", False)
        )
        adapter.set_stallguard_threshold(
            getattr(app_state.config, "DEFAULT_STALLGUARD_THRESHOLD", 0)
        )
        adapter.set_stallguard_enabled(
            getattr(app_state.config, "DEFAULT_STALLGUARD_ENABLED", True)
        )
        adapter.set_stallguard_filter_enabled(
            getattr(app_state.config, "DEFAULT_STALLGUARD_FILTER_ENABLED", True)
        )
        adapter.set_coolstep_threshold(
            getattr(app_state.config, "DEFAULT_COOLSTEP_THRESHOLD", 0)
        )
        adapter.set_coolstep_enabled(
            getattr(app_state.config, "DEFAULT_COOLSTEP_ENABLED", False)
        )
        adapter.enable_reference_stops(
            left=getattr(
                app_state.config, "DEFAULT_REFERENCE_LEFT_STOP_ENABLED", True
            ),
            right=getattr(
                app_state.config, "DEFAULT_REFERENCE_RIGHT_STOP_ENABLED", True
            ),
        )
        failed_startup_cleanup.pop_all()
        return adapter


def _close_after_failed_startup(close: Callable[[], None]) -> None:
    try:
        close()
    except Exception:
        pass


def _prepare_tmc5160_motor_for_startup(motor, logger) -> None:
    startup_actions = [motor.stop, motor.disable]
    if hasattr(motor, "enable_reference_stops"):
        startup_actions.append(
            lambda: motor.enable_reference_stops(left=False, right=False)
        )
    startup_actions.append(motor.get_actual_position_rot)
    get_actual_speed_rps = getattr(motor, "get_actual_speed_rps", None)
    if callable(get_actual_speed_rps):
        startup_actions.append(get_actual_speed_rps)

    first_error: Exception | None = None
    for action in startup_actions:
        try:
            action()
        except Exception as error:
            if first_error is None:
                first_error = error

    if first_error is not None:
        msg = (
            "TMC5160 startup initialization failed. Check that motor power is on "
            "before connecting USB, then reconnect the Landungsbruecke USB cable."
        )
        logger.error(msg)
        raise RuntimeError(msg) from first_error


_SPECS = {
    AvailableMotorDrivers.TMC2209: MotorDriverSpec(
        driver_type=AvailableMotorDrivers.TMC2209,
        requires_gpio=True,
        default_setup=AvailableMachineSetups.SMALL_COATER,
        driver_factory=_create_tmc2209_driver,
        log_level_from_name=lambda name: getattr(Loglevel, name),
        log_level_options=lambda: [(level.name, level.name) for level in Loglevel],
        create_advanced_settings=lambda app_state: AdvancedSettingsTMC2209(app_state),
        create_advanced_status=lambda app_state, *args, **kwargs: StatusAdvancedTMC2209(
            app_state, *args, **kwargs
        ),
    ),
    AvailableMotorDrivers.TMC2660: MotorDriverSpec(
        driver_type=AvailableMotorDrivers.TMC2660,
        requires_gpio=False,
        default_setup=AvailableMachineSetups.LARGE_COATER,
        driver_factory=_create_tmc2660_driver,
        log_level_from_name=lambda name: getattr(TMC2660DriverLogLevel, name),
        log_level_options=lambda: [
            (level.name, level.name) for level in TMC2660LogLevel
        ],
        create_advanced_settings=lambda app_state: AdvancedSettingsTMC2660(app_state),
        create_advanced_status=lambda app_state, *args, **kwargs: StatusAdvancedTMC2660(
            app_state, *args, **kwargs
        ),
    ),
    AvailableMotorDrivers.TMC5160: MotorDriverSpec(
        driver_type=AvailableMotorDrivers.TMC5160,
        requires_gpio=False,
        default_setup=AvailableMachineSetups.LARGE_COATER,
        driver_factory=_create_tmc5160_driver,
        log_level_from_name=lambda name: getattr(TMC5160LogLevel, name),
        log_level_options=lambda: [
            (level.name, level.name) for level in TMC5160LogLevel
        ],
        create_advanced_settings=lambda app_state: AdvancedSettingsTrinamicTMC5160(
            app_state
        ),
        create_advanced_status=lambda app_state, *args, **kwargs: StatusAdvancedTrinamicTMC5160(
            app_state, *args, **kwargs
        ),
        adjust_setup_profile=_normalize_tmc5160_setup_profile,
        supports_driver_reference_switches=True,
    ),
}


def get_driver_spec(driver_type: AvailableMotorDrivers | str) -> MotorDriverSpec:
    """Return driver factory metadata by driver type.

    :param driver_type: Driver enum value or string name.
    :return: Matching motor-driver spec.
    """
    if not isinstance(driver_type, AvailableMotorDrivers):
        driver_type = AvailableMotorDrivers(driver_type)
    try:
        return _SPECS[driver_type]
    except KeyError as exc:
        raise ValueError(f"Unsupported driver type: '{driver_type}'") from exc


def validate_driver_setup_compatibility(
    driver_type: AvailableMotorDrivers | str,
    setup_profile: MachineProfile,
    *,
    use_dummy_driver: bool,
) -> None:
    """Reject hardware configurations whose safety inputs cannot be read.

    Dummy drivers are allowed for UI and motion simulation because they do not
    energize physical hardware.

    :param driver_type: Selected motor driver.
    :param setup_profile: Selected machine and limit-switch profile.
    :param use_dummy_driver: Whether this run uses simulated hardware.
    :raises ValueError: If real hardware cannot read the configured switches.
    """
    spec = get_driver_spec(driver_type)
    switches = setup_profile.limit_switches
    if (
        not use_dummy_driver
        and switches is not None
        and switches.uses_driver_reference
        and not spec.supports_driver_reference_switches
    ):
        raise ValueError(
            f"{spec.driver_type.value} cannot read driver-reference limit switches "
            f"required by the '{setup_profile.key.value}' setup. Use TMC5160 for "
            "this setup, select a verified GPIO-backed setup, or use "
            "--use-dummy-driver for simulation."
        )
