from dip_coater.mechanical.mechanical_setup import MechanicalSetup
from dip_coater.mechanical.setup_large_coater import SetupLargeCoater
from dip_coater.mechanical.setup_small_coater import SetupSmallCoater
from dip_coater.motor_driver.motor_driver_interface import AvailableMotorDrivers
from dip_coater.setup_profiles.machine_profile import (
    AvailableMachineSetups,
    HomeDirection,
    LimitSwitchSetup,
    MachineProfile,
)


_GPIO_LIMIT_SWITCHES = LimitSwitchSetup.gpio(
    up_pin=19,
    down_pin=26,
    up_nc=True,
    down_nc=True,
)
_LANDUNGSBRUECKE_REFERENCE_LIMIT_SWITCHES = LimitSwitchSetup.tmc5160_reference()

_PROFILES = {
    AvailableMachineSetups.SMALL_COATER: MachineProfile(
        key=AvailableMachineSetups.SMALL_COATER,
        label="Small Coater",
        mechanical_setup=SetupSmallCoater(),
        invert_motor_direction=False,
        home_direction=HomeDirection.UP,
        limit_switches=_GPIO_LIMIT_SWITCHES,
        min_position_mm=0.0,
        max_position_mm=100.0,
        homing_max_distance_mm=100.0,
    ),
    AvailableMachineSetups.LARGE_COATER: MachineProfile(
        key=AvailableMachineSetups.LARGE_COATER,
        label="Large Coater",
        mechanical_setup=SetupLargeCoater(),
        invert_motor_direction=True,
        home_direction=HomeDirection.DOWN,
        limit_switches=_LANDUNGSBRUECKE_REFERENCE_LIMIT_SWITCHES,
        min_position_mm=0.0,
        max_position_mm=100.0,
        homing_max_distance_mm=100.0,
    ),
}

DEFAULT_SETUP_BY_DRIVER = {
    AvailableMotorDrivers.TMC2209: AvailableMachineSetups.SMALL_COATER,
    AvailableMotorDrivers.TMC2660: AvailableMachineSetups.LARGE_COATER,
    AvailableMotorDrivers.TMC5160: AvailableMachineSetups.LARGE_COATER,
}


def list_machine_setups() -> list[AvailableMachineSetups]:
    return list(_PROFILES.keys())


def get_default_setup_for_driver(
    driver_type: AvailableMotorDrivers,
) -> AvailableMachineSetups:
    return DEFAULT_SETUP_BY_DRIVER[driver_type]


def get_machine_profile(setup_key: AvailableMachineSetups | str) -> MachineProfile:
    if not isinstance(setup_key, AvailableMachineSetups):
        setup_key = AvailableMachineSetups(setup_key)
    try:
        return _PROFILES[setup_key]
    except KeyError as exc:
        raise ValueError(f"Unsupported machine setup: '{setup_key}'") from exc


def create_custom_profile(
    base_profile: MachineProfile,
    *,
    mm_per_revolution: float | None = None,
    gearbox_ratio: float | None = None,
    steps_per_revolution: int | None = None,
    invert_motor_direction: bool | None = None,
    home_direction: HomeDirection | None = None,
) -> MachineProfile:
    mechanical_setup = MechanicalSetup(
        mm_per_revolution=(
            base_profile.mechanical_setup.mm_per_revolution
            if mm_per_revolution is None
            else mm_per_revolution
        ),
        gearbox_ratio=(
            base_profile.mechanical_setup.gearbox_ratio
            if gearbox_ratio is None
            else gearbox_ratio
        ),
        steps_per_revolution=(
            base_profile.mechanical_setup.steps_per_revolution
            if steps_per_revolution is None
            else steps_per_revolution
        ),
    )
    return MachineProfile(
        key=AvailableMachineSetups.CUSTOM,
        label=f"Custom ({base_profile.label})",
        mechanical_setup=mechanical_setup,
        invert_motor_direction=(
            base_profile.invert_motor_direction
            if invert_motor_direction is None
            else invert_motor_direction
        ),
        home_direction=base_profile.home_direction
        if home_direction is None
        else home_direction,
        limit_switches=base_profile.limit_switches,
        min_position_mm=base_profile.min_position_mm,
        max_position_mm=base_profile.max_position_mm,
        homing_max_distance_mm=base_profile.homing_max_distance_mm,
    )
