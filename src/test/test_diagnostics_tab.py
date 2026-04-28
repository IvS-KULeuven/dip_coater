from dip_coater.mechanical.mechanical_setup import MechanicalSetup
from dip_coater.motor_driver.motor_driver_interface import AvailableMotorDrivers
from dip_coater.setup_profiles.machine_profile import (
    AvailableMachineSetups,
    LimitSwitchSetup,
    MachineProfile,
)
from dip_coater.widgets.tabs.diagnostics_tab import (
    build_diagnostics_rows,
    format_diagnostics_rows,
)


class FakeDriver:
    is_dummy = True

    def get_left_endstop(self):
        return False

    def get_right_endstop(self):
        return True


class FakeMotionController:
    supports_limit_switches = True
    supports_homing = False
    supports_gpio_limit_switches = False
    supports_driver_reference_switches = True

    def read_limit_switch(self, direction):
        return direction.value == "up"

    def get_current_position_mm(self):
        return 12.3


class FakeAppState:
    driver_type = AvailableMotorDrivers.TMC5160
    motor_driver = FakeDriver()
    motion_controller = FakeMotionController()
    motor_state = "enabled"
    homing_found = False
    setup_profile = MachineProfile(
        key=AvailableMachineSetups.CUSTOM,
        label="Custom TMC",
        mechanical_setup=MechanicalSetup(mm_per_revolution=4.0),
        limit_switches=LimitSwitchSetup.tmc5160_reference(),
    )


def test_diagnostics_rows_include_driver_limits_and_raw_reference_state():
    rows = dict(build_diagnostics_rows(FakeAppState()))

    assert rows["Driver"] == "TMC5160 (dummy)"
    assert rows["Setup"] == "Custom TMC"
    assert rows["Motor state"] == "enabled"
    assert rows["Position"] == "12.3 mm"
    assert rows["UP limit switch"] == "triggered"
    assert rows["DOWN limit switch"] == "open"
    assert rows["UP limit config"] == "driver_reference, active_low"
    assert rows["TMC L reference raw"] == "low"
    assert rows["TMC R reference raw"] == "high"


def test_diagnostics_format_colorizes_state_values():
    output = format_diagnostics_rows(
        [
            ("Motor state", "disabled"),
            ("UP limit switch", "triggered"),
            ("DOWN limit switch", "open"),
        ]
    )

    assert "[dark_orange]disabled[/]" in output
    assert "[red]triggered[/]" in output
    assert "[green]open[/]" in output
