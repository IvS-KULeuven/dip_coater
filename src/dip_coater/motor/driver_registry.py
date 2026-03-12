from dataclasses import dataclass
from typing import Any, Callable

from TMC_2209._TMC_2209_logger import Loglevel

from dip_coater.logging.tmc2660_logger import TMC2660LogLevel
from dip_coater.motor.motor_driver_interface import AvailableMotorDrivers, MotorDriver
from dip_coater.motor.tmc2209 import MotorDriverTMC2209
from dip_coater.motor.tmc2660 import (
    MotorDriverTMC2660,
    TMC2660LogLevel as TMC2660DriverLogLevel,
)
from dip_coater.setup_profiles.machine_profile import AvailableMachineSetups
from dip_coater.widgets.advanced.advanced_settings_tmc2209 import (
    AdvancedSettingsTMC2209,
)
from dip_coater.widgets.advanced.advanced_settings_tmc2660 import (
    AdvancedSettingsTMC2660,
)
from dip_coater.widgets.advanced.status_advanced_tmc2209 import StatusAdvancedTMC2209
from dip_coater.widgets.advanced.status_advanced_tmc2660 import StatusAdvancedTMC2660


@dataclass(frozen=True)
class MotorDriverSpec:
    driver_type: AvailableMotorDrivers
    requires_gpio: bool
    default_setup: AvailableMachineSetups
    driver_factory: Callable[..., MotorDriver]
    log_level_from_name: Callable[[str], Any]
    log_level_options: Callable[[], list[tuple[str, str]]]
    create_advanced_settings: Callable[[Any], Any]
    create_advanced_status: Callable[[Any], Any]


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
}


def get_driver_spec(driver_type: AvailableMotorDrivers | str) -> MotorDriverSpec:
    if not isinstance(driver_type, AvailableMotorDrivers):
        driver_type = AvailableMotorDrivers(driver_type)
    try:
        return _SPECS[driver_type]
    except KeyError as exc:
        raise ValueError(f"Unsupported driver type: '{driver_type}'") from exc
