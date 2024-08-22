from textual.app import ComposeResult
from textual.widgets import Label

from dip_coater.widgets.advanced.status_advanced_base import StatusAdvancedBase


class StatusAdvancedTMC2660(StatusAdvancedBase):
    def __init__(self, app_state, *args, **kwargs):
        super().__init__(app_state, *args, **kwargs)

    def additional_widgets(self) -> ComposeResult:
        yield Label(id="status-interpolation")

    def update_interpolation(self, interpolation: bool):
        self.query_one("#status-interpolation", Label).update(f"Interpolation: {interpolation}")
