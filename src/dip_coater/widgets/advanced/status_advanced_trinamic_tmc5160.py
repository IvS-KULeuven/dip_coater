from textual.app import ComposeResult
from textual.widgets import Label, Rule

from dip_coater.widgets.advanced.status_advanced_base import StatusAdvancedBase


class StatusAdvancedTrinamicTMC5160(StatusAdvancedBase):
    def additional_widgets(self) -> ComposeResult:
        yield Label(id="status-interpolation")
        yield Label(id="status-chopper-mode")
        yield Rule()
        yield Label(id="status-stealthchop-enabled")
        yield Label(id="status-stealthchop-threshold")
        yield Label(id="status-stallguard-enabled")
        yield Label(id="status-stallguard-filter-enabled")
        yield Label(id="status-stallguard-threshold")
        yield Label(id="status-coolstep-enabled")
        yield Label(id="status-coolstep-threshold")

    def update_interpolation(self, interpolation: bool):
        self.query_one("#status-interpolation", Label).update(
            f"Interpolation: {interpolation}"
        )

    def update_chopper_mode(self, chopper_mode):
        label = getattr(chopper_mode, "label", str(chopper_mode))
        self.query_one("#status-chopper-mode", Label).update(
            f"Chopper Mode: {label}"
        )

    def update_stealthchop_enabled(self, stealthchop_enabled: bool):
        self.query_one("#status-stealthchop-enabled", Label).update(
            f"StealthChop enabled: {stealthchop_enabled}"
        )

    def update_stealthchop_threshold(self, stealthchop_threshold: float):
        self.query_one("#status-stealthchop-threshold", Label).update(
            f"StealthChop threshold: {stealthchop_threshold:.2f} rev/s"
        )

    def update_stallguard_enabled(self, stallguard_enabled: bool):
        self.query_one("#status-stallguard-enabled", Label).update(
            f"StallGuard enabled: {stallguard_enabled}"
        )

    def update_stallguard_filter_enabled(self, stallguard_filter_enabled: bool):
        self.query_one("#status-stallguard-filter-enabled", Label).update(
            f"StallGuard filter enabled: {stallguard_filter_enabled}"
        )

    def update_stallguard_threshold(self, stallguard_threshold: int):
        self.query_one("#status-stallguard-threshold", Label).update(
            f"StallGuard threshold: {stallguard_threshold}"
        )

    def update_coolstep_enabled(self, coolstep_enabled: bool):
        self.query_one("#status-coolstep-enabled", Label).update(
            f"CoolStep enabled: {coolstep_enabled}"
        )

    def update_coolstep_threshold(self, coolstep_threshold: int):
        self.query_one("#status-coolstep-threshold", Label).update(
            f"CoolStep threshold: {coolstep_threshold}"
        )
