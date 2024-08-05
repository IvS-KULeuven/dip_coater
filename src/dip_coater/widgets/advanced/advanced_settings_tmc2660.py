from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Checkbox

from dip_coater.widgets.advanced.advanced_settings_base import AdvancedSettingsBase


class AdvancedSettingsTMC2660(AdvancedSettingsBase):
    def __init__(self, app_state):
        super().__init__(app_state)

    def additional_widgets(self) -> ComposeResult:
        with Horizontal(id="interpolation-container"):
            yield Checkbox("Invert motor direction",
                           value=self.app_state.config.INVERT_MOTOR_DIRECTION,
                           id="invert-direction-checkbox", classes="checkbox")
