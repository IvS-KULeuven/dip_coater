from textual.app import ComposeResult
from textual.widgets import Label, Rule, Static

from dip_coater.widgets.advanced.status_advanced_base import StatusAdvancedBase


class StatusAdvancedTMC2209(StatusAdvancedBase):
    def __init__(self, app_state, *args, **kwargs):
        super().__init__(app_state, *args, **kwargs)

    def additional_widgets(self) -> ComposeResult:
        yield Label(id="status-interpolation")
        yield Label(id="status-spread-cycle")
        yield Rule()
        yield Label(id="status-speed-mode")
        yield Label(id="status-threshold-speed")
        yield Rule()
        yield Label(id="status-homing-revolutions")
        yield Label(id="status-homing-threshold")
        yield Label(id="status-homing-speed")

    def update_interpolation(self, interpolation: bool):
        self.query_one("#status-interpolation", Label).update(f"Interpolation: {interpolation}")

    def update_spread_cycle(self, spread_cycle: bool):
        self.query_one("#status-spread-cycle", Label).update(f"Spread Cycle: {spread_cycle}")

    def update_speed_mode(self, threshold_enabled: bool, threshold_speed: float):
        mode = "CUSTOM" if not threshold_enabled else "High-speed" \
            if self.app_state.speed_controls.speed > threshold_speed else "Low-speed"
        self.query_one("#status-speed-mode", Static).update(f"Speed mode: {mode}")

    def update_threshold_speed(self, threshold_speed: float):
        self.query_one("#status-threshold-speed", Static).update(f"Threshold Speed: {threshold_speed:.2f} mm/s")
        self.update_speed_mode(self.app_state.advanced_settings.get_threshold_speed_enabled(), threshold_speed)

    def update_threshold_speed_enabled(self, enabled: bool):
        self.update_speed_mode(enabled, self.app_state.advanced_settings.get_threshold_speed())

    def update_homing_revs(self, homing_revs: int):
        self.query_one("#status-homing-revolutions", Label).update(f"Homing revolutions: {homing_revs}")

    def update_homing_threshold(self, homing_threshold: int):
        self.query_one("#status-homing-threshold", Label).update(f"Homing StallGuard threshold: {homing_threshold}")

    def update_homing_speed(self, homing_speed: float):
        self.query_one("#status-homing-speed", Label).update(f"Homing speed: {homing_speed} mm/s")
