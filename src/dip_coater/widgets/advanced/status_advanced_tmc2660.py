from textual.app import ComposeResult
from textual.widgets import Label

from dip_coater.widgets.advanced.status_advanced_base import StatusAdvancedBase
from dip_coater.motor.tmc2660 import ChopperMode


class StatusAdvancedTMC2660(StatusAdvancedBase):
    def __init__(self, app_state, *args, **kwargs):
        super().__init__(app_state, *args, **kwargs)

    def additional_widgets(self) -> ComposeResult:
        yield Label(id="status-interpolation")
        yield Label(id="status-chopper-mode")

    def update_interpolation(self, interpolation: bool):
        self.query_one("#status-interpolation", Label).update(f"Interpolation: {interpolation}")

    def update_chopper_mode(self, chopper_mode: ChopperMode):
        self.query_one("#status-chopper-mode", Label).update(f"Chopper Mode: {chopper_mode.label}")
