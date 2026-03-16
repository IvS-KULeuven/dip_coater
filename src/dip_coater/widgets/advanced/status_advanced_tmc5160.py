from textual.app import ComposeResult
from textual.widgets import Label, Rule

from dip_coater.widgets.advanced.status_advanced_base import StatusAdvancedBase


class StatusAdvancedTMC5160(StatusAdvancedBase):
    def additional_widgets(self) -> ComposeResult:
        yield Rule()
        yield Label(
            "TMC5160 backend",
            id="status-tmc5160-note",
        )
