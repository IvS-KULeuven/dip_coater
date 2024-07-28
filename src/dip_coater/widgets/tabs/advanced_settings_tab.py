from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, TabPane

from dip_coater.widgets.advanced_settings import AdvancedSettings
from dip_coater.widgets.status_advanced import StatusAdvanced

class AdvancedSettingsTab(TabPane):
    def __init__(self, app_state):
        super().__init__("Advanced", id="advanced-tab")
        self.app_state = app_state

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical(id="left-side-advanced"):
                yield AdvancedSettings(self.app_state.motor_driver)
            with Vertical(id="right-side-advanced"):
                yield StatusAdvanced(id="status-advanced")
                yield Button("Reset to defaults", id="reset-to-defaults-btn", variant="error")
