from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual import on
from textual.widgets import Checkbox

from dip_coater.widgets.advanced.advanced_settings_base import AdvancedSettingsBase
from dip_coater.utils.SettingChanged import SettingChanged


class AdvancedSettingsTMC2660(AdvancedSettingsBase):
    _interpolation: reactive[bool | None] = reactive(None)

    def __init__(self, app_state):
        super().__init__(app_state)

    def additional_widgets(self) -> ComposeResult:
        with Horizontal(id="interpolation-container"):
            yield Checkbox("Invert motor direction",
                           value=self.app_state.config.INVERT_MOTOR_DIRECTION,
                           id="invert-direction-checkbox", classes="checkbox")
            yield Checkbox("Interpolation", value=self._interpolation,
                           id="interpolation-checkbox", classes="checkbox")

    def reset_settings_to_default(self):
        super().reset_settings_to_default()

        self.update_interpolation(self.app_state.config.USE_INTERPOLATION)
        self.query_one("#interpolation-checkbox", Checkbox).value = (
            self.app_state.config.USE_INTERPOLATION)

    # --------------- WIDGET INTERACTIONS ---------------

    @on(Checkbox.Changed, "#interpolation-checkbox")
    def toggle_interpolation(self, event: Checkbox.Changed):
        interpolation = event.checkbox.value
        self.update_interpolation(interpolation)

    def update_interpolation(self, interpolation: reactive[bool | None]):
        self._interpolation = interpolation

    # --------------- WATCHERS (called automatically when reactive has changed) ---------------

    def watch__interpolation(self, interpolation: bool):
        if interpolation is None:
            return
        self.post_message(SettingChanged("interpolation", interpolation))
