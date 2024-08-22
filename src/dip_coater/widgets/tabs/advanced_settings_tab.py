from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, TabPane

from dip_coater.widgets.advanced.advanced_settings_tmc2209 import AdvancedSettingsTMC2209
from dip_coater.widgets.advanced.advanced_settings_tmc2660 import AdvancedSettingsTMC2660
from dip_coater.widgets.advanced.status_advanced_tmc2209 import StatusAdvancedTMC2209
from dip_coater.widgets.advanced.status_advanced_tmc2660 import StatusAdvancedTMC2660
from dip_coater.utils.SettingChanged import SettingChanged
from dip_coater.motor.motor_driver_interface import AvailableMotorDrivers


def create_advanced_settings(driver_type, app_state):
    if driver_type == AvailableMotorDrivers.TMC2209:
        return AdvancedSettingsTMC2209(app_state)
    elif driver_type == AvailableMotorDrivers.TMC2660:
        return AdvancedSettingsTMC2660(app_state)
    else:
        raise ValueError(f"Unsupported driver type: '{driver_type}'")


def create_advanced_status(driver_type, app_state, *args, **kwargs):
    if driver_type == AvailableMotorDrivers.TMC2209:
        return StatusAdvancedTMC2209(app_state, *args, **kwargs)
    elif driver_type == AvailableMotorDrivers.TMC2660:
        return StatusAdvancedTMC2660(app_state, *args, **kwargs)
    else:
        raise ValueError(f"Unsupported driver type: '{driver_type}'")


class AdvancedSettingsTab(TabPane):
    def __init__(self, app_state):
        super().__init__("Advanced", id="advanced-tab")
        self.app_state = app_state
        self.app_state.status_advanced = create_advanced_status(self.app_state.driver_type, self.app_state,
                                                                id="status-advanced")
        self.app_state.advanced_settings = create_advanced_settings(self.app_state.driver_type, self.app_state)

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical(id="left-side-advanced"):
                yield self.app_state.advanced_settings
            with Vertical(id="right-side-advanced"):
                yield self.app_state.status_advanced
                yield Button("Reset to defaults", id="reset-to-defaults-btn", variant="error")

    def on_setting_changed(self, event: SettingChanged):
        match event.setting_name:
            case "acceleration":
                self.app_state.motor_driver.set_acceleration(event.value)
                self.app_state.status_advanced.update_acceleration(event.value)
            case "current":
                self.app_state.motor_driver.set_current(event.value)
                self.app_state.status_advanced.update_current(event.value)
            case "current_standstill":
                self.app_state.motor_driver.set_current_standstill(event.value)
                self.app_state.status_advanced.update_current_standstill(event.value)
            case "invert_direction":
                self.app_state.motor_driver.invert_direction(event.value)
                self.app_state.status_advanced.update_invert_motor_direction(event.value)
            case "interpolation":
                self.app_state.motor_driver.set_interpolation(event.value)
                self.app_state.status_advanced.update_interpolation(event.value)
            case "chopper_mode":
                self.app_state.motor_driver.set_chopper_mode(event.value)
                self.app_state.status_advanced.update_chopper_mode(event.value)
            case "spread_cycle":
                self.app_state.motor_driver.set_spread_cycle(event.value)
                self.app_state.status_advanced.update_spread_cycle(event.value)
            case "stallguard_enabled":
                self.app_state.motor_driver.set_stallguard_enabled(event.value)
                self.app_state.status_advanced.update_stallguard_enabled(event.value)
            case "stallguard_filter_enabled":
                self.app_state.motor_driver.set_stallguard_filter_enabled(event.value)
                self.app_state.status_advanced.update_stallguard_filter_enabled(event.value)
            case "stallguard_threshold":
                self.app_state.motor_driver.set_stallguard_threshold(event.value)
                self.app_state.status_advanced.update_stallguard_threshold(event.value)
            case "coolstep_enabled":
                self.app_state.motor_driver.set_coolstep_enabled(event.value)
                self.app_state.status_advanced.update_coolstep_enabled(event.value)
            case "coolstep_threshold":
                self.app_state.motor_driver.set_coolstep_threshold(event.value)
                self.app_state.status_advanced.update_coolstep_threshold(event.value)
            case "threshold_speed":
                self.app_state.status_advanced.update_threshold_speed(event.value)
                self.app_state.advanced_settings.update_control_mode_widgets_value()
            case "threshold_speed_enabled":
                self.app_state.status_advanced.update_threshold_speed_enabled(event.value)
                self.app_state.advanced_settings.update_control_mode_widgets_value()
                self.app_state.advanced_settings.update_control_mode_widgets_state()
            case "homing_revs":
                self.app_state.status_advanced.update_homing_revs(event.value)
            case "homing_threshold":
                self.app_state.status_advanced.update_homing_threshold(event.value)
            case "homing_speed":
                self.app_state.status_advanced.update_homing_speed(event.value)
            case _:
                raise ValueError(f"Unsupported setting: '{event.setting_name}'")
