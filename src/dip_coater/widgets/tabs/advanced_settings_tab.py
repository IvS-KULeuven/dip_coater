from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, TabPane

from dip_coater.widgets.advanced_settings import AdvancedSettings
from dip_coater.widgets.status_advanced import StatusAdvanced

class AdvancedSettingsTab(TabPane):
    def __init__(self, app_state):
        super().__init__("Advanced", id="advanced-tab")
        self.app_state = app_state
        self.app_state.status_advanced = StatusAdvanced(self.app_state, id="status-advanced")
        self.app_state.advanced_settings = AdvancedSettings(self.app_state)

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical(id="left-side-advanced"):
                yield self.app_state.advanced_settings
            with Vertical(id="right-side-advanced"):
                yield self.app_state.status_advanced
                yield Button("Reset to defaults", id="reset-to-defaults-btn", variant="error")
