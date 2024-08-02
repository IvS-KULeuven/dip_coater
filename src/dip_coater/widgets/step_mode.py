from textual.containers import Vertical
from textual.app import ComposeResult
from textual.widgets import Label, RadioSet, RadioButton, RichLog, Static

from dip_coater.constants import (
    STEP_MODES, DEFAULT_STEP_MODE, STEP_MODE_LABELS, STEP_MODE_WRITE_TO_LOG
)


class StepMode(Static):
    def __init__(self, app_state):
        super().__init__()
        self.step_mode = STEP_MODES[DEFAULT_STEP_MODE]
        self.app_state = app_state

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Step Mode")
            with RadioSet(id="step-mode"):
                for mode, label in STEP_MODE_LABELS.items():
                    yield RadioButton(label, id=mode)

    def on_mount(self):
        self.app_state.motor_driver.set_microsteps(self.step_mode)
        self.query_one(f"#{DEFAULT_STEP_MODE}", RadioButton).value = True

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        step_mode = STEP_MODES[event.pressed.id]
        self.set_microsteps(step_mode, event.pressed.label)

    def set_microsteps(self, step_mode: int, step_mode_label):
        self.step_mode = step_mode
        self.app_state.motor_driver.set_microsteps(self.step_mode)
        if STEP_MODE_WRITE_TO_LOG:
            log = self.app.query_one("#logger", RichLog)
            log.write(f"StepMode set to {step_mode_label} µsteps.")
        self.app_state.status_advanced.step_mode = f"Step Mode: {step_mode_label} µsteps"
