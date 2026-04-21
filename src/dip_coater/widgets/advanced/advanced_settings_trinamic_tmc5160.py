from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual import on
from textual.widgets import Checkbox

from dip_coater.utils.SettingChanged import SettingChanged
from dip_coater.widgets.advanced.advanced_settings_base import AdvancedSettingsBase


class AdvancedSettingsTrinamicTMC5160(AdvancedSettingsBase):
    _interpolation: reactive[bool | None] = reactive(None)

    def __init__(self, app_state):
        super().__init__(app_state)
        self.update_interpolation(self.app_state.config.USE_INTERPOLATION)

    def additional_widgets(self) -> ComposeResult:
        with Horizontal(id="interpolation-container"):
            yield Checkbox(
                "Invert motor direction",
                value=self.app_state.setup_profile.invert_motor_direction,
                id="invert-direction-checkbox",
                classes="checkbox",
            )
            yield Checkbox(
                "Interpolation",
                value=self._interpolation,
                id="interpolation-checkbox",
                classes="checkbox",
            )

    def reset_settings_to_default(self):
        super().reset_settings_to_default()
        self.update_interpolation(self.app_state.config.USE_INTERPOLATION)
        self.query_one(
            "#interpolation-checkbox", Checkbox
        ).value = self.app_state.config.USE_INTERPOLATION

    @on(Checkbox.Changed, "#interpolation-checkbox")
    def toggle_interpolation(self, event: Checkbox.Changed):
        self.update_interpolation(event.checkbox.value)

    def update_interpolation(self, interpolation: reactive[bool | None]):
        self._interpolation = interpolation

    def watch__interpolation(self, interpolation: bool):
        if interpolation is None:
            return
        self.post_message(SettingChanged("interpolation", interpolation))
