from textual.app import ComposeResult
from textual.widgets import Label

from dip_coater.widgets.advanced.status_advanced_base import StatusAdvancedBase


class StatusAdvancedTrinamicTMC5160(StatusAdvancedBase):
    def additional_widgets(self) -> ComposeResult:
        yield Label(id="status-interpolation")

    def update_interpolation(self, interpolation: bool):
        self.query_one("#status-interpolation", Label).update(
            f"Interpolation: {interpolation}"
        )
