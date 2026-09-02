from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, TabPane

from dip_coater.utils.SettingChanged import SettingChanged
from dip_coater.motor_driver.driver_registry import get_driver_spec


_SUPPORTED_SETTING_NAMES = frozenset({
    "acceleration",
    "current",
    "current_standstill",
    "invert_direction",
    "interpolation",
    "chopper_mode",
    "stealthchop_enabled",
    "stealthchop_threshold",
    "spread_cycle",
    "stallguard_enabled",
    "stallguard_filter_enabled",
    "stallguard_threshold",
    "coolstep_enabled",
    "coolstep_threshold",
    "threshold_speed",
    "threshold_speed_enabled",
    "homing_revs",
    "homing_threshold",
    "homing_speed",
})


class AdvancedSettingsTab(TabPane):
    def __init__(self, app_state):
        super().__init__("Advanced", id="advanced-tab")
        self.app_state = app_state
        self.driver_spec = get_driver_spec(self.app_state.driver_type)
        self.app_state.status_advanced = self.driver_spec.create_advanced_status(
            self.app_state,
            id="status-advanced",
        )
        self.app_state.advanced_settings = self.driver_spec.create_advanced_settings(
            self.app_state
        )

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical(id="left-side-advanced"):
                yield self.app_state.advanced_settings
            with Vertical(id="right-side-advanced"):
                yield self.app_state.status_advanced
                yield Button(
                    "Reset to defaults", id="reset-to-defaults-btn", variant="error"
                )

    def on_setting_changed(self, event: SettingChanged):
        if self.app_state.motor_state in ("moving", "homing"):
            return
        if event.setting_name not in _SUPPORTED_SETTING_NAMES:
            raise ValueError(f"Unsupported setting: '{event.setting_name}'")
        try:
            AdvancedSettingsTab._apply_setting(self, event)
        except Exception as error:
            self.app_state.motor_controls.handle_motion_fault(
                error, f"Update {event.setting_name} setting"
            )

    def _apply_setting(self, event: SettingChanged) -> None:
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
                self.app_state.status_advanced.update_invert_motor_direction(
                    event.value
                )
            case "interpolation":
                self.app_state.motor_driver.set_interpolation(event.value)
                self.app_state.status_advanced.update_interpolation(event.value)
            case "chopper_mode":
                self.app_state.motor_driver.set_chopper_mode(event.value)
                self.app_state.status_advanced.update_chopper_mode(event.value)
            case "stealthchop_enabled":
                self.app_state.motor_driver.set_stealthchop_enabled(event.value)
                self.app_state.status_advanced.update_stealthchop_enabled(event.value)
            case "stealthchop_threshold":
                self.app_state.motor_driver.set_stealthchop_threshold(event.value)
                self.app_state.status_advanced.update_stealthchop_threshold(
                    event.value
                )
            case "spread_cycle":
                self.app_state.motor_driver.set_spread_cycle(event.value)
                self.app_state.status_advanced.update_spread_cycle(event.value)
            case "stallguard_enabled":
                self.app_state.motor_driver.set_stallguard_enabled(event.value)
                self.app_state.status_advanced.update_stallguard_enabled(event.value)
            case "stallguard_filter_enabled":
                self.app_state.motor_driver.set_stallguard_filter_enabled(event.value)
                self.app_state.status_advanced.update_stallguard_filter_enabled(
                    event.value
                )
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
                self.app_state.advanced_settings.update_motor_configuration()
            case "threshold_speed_enabled":
                self.app_state.status_advanced.update_threshold_speed_enabled(
                    event.value
                )
                self.app_state.advanced_settings.update_motor_configuration()
                self.app_state.advanced_settings.update_control_mode_widgets_state()
            case "homing_revs":
                self.app_state.status_advanced.update_homing_revs(event.value)
            case "homing_threshold":
                self.app_state.status_advanced.update_homing_threshold(event.value)
            case "homing_speed":
                self.app_state.status_advanced.update_homing_speed(event.value)
