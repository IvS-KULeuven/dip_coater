from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Checkbox, Label, Rule

from dip_coater.widgets.advanced.advanced_settings_base import AdvancedSettingsBase


class AdvancedSettingsTMC5160(AdvancedSettingsBase):
    def additional_widgets(self) -> ComposeResult:
        with Horizontal(id="tmc5160-note-container"):
            yield Checkbox(
                "Invert motor direction",
                value=self.app_state.setup_profile.invert_motor_direction,
                id="invert-direction-checkbox",
                classes="checkbox",
            )
        yield Rule()
        yield Label(
            "TMC5160 advanced settings",
            id="tmc5160-note",
        )
