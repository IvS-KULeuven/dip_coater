from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static, Label, Rule


class StatusAdvancedBase(Static):
    def __init__(self, app_state, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app_state = app_state

    def compose(self) -> ComposeResult:
        with Vertical() as v:
            yield Label(id="status-step-mode")
            yield Label(id="status-acceleration")
            yield Label(id="status-current")
            yield Label(id="status-current-standstill")
            yield Rule()
            yield Label(id="status-invert-direction")
            yield from self.additional_widgets()

    def additional_widgets(self) -> ComposeResult:
        """Override this method in subclasses to add additional widgets."""
        yield from ()

    def update_step_mode(self, step_mode: str):
        self.query_one("#status-step-mode", Label).update(f"Step Mode: {step_mode} µsteps")

    def update_acceleration(self, acceleration: float):
        self.query_one("#status-acceleration", Label).update(f"Acceleration: {acceleration} mm/s\u00b2")

    def update_current(self, current: int):
        self.query_one("#status-current", Label).update(f"Motor current: {current} mA")

    def update_current_standstill(self, current_standstill: int):
        self.query_one("#status-current-standstill", Label).update(
            f"Motor current standstill: {current_standstill} mA")

    def update_invert_motor_direction(self, invert_direction: bool):
        self.query_one("#status-invert-direction", Label).update(f"Invert motor direction: {invert_direction}")
