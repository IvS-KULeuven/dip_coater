from textual.containers import Vertical
from textual.app import ComposeResult
from textual.widgets import Label, RadioSet, RadioButton, RichLog, Static

from dip_coater.constants import (
    STEP_MODES, DEFAULT_STEP_MODE, STEP_MODE_LABELS, STEP_MODE_WRITE_TO_LOG
)
from dip_coater.widgets.status_advanced import StatusAdvanced
from dip_coater.motor.tmc2209 import TMC2209_MotorDriver


class StepMode(Static):
    def __init__(self, motor_driver: TMC2209_MotorDriver):
        super().__init__()
        self.step_mode = STEP_MODES[DEFAULT_STEP_MODE]
        self.motor_driver = motor_driver
        self.motor_driver.set_stepmode(self.step_mode)

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Step Mode")
            with RadioSet(id="step-mode"):
                for mode, label in STEP_MODE_LABELS.items():
                    yield RadioButton(label, id=mode)

    def on_mount(self):
        self.query_one(f"#{DEFAULT_STEP_MODE}", RadioButton).value = True

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        step_mode = STEP_MODES[event.pressed.id]
        self.set_stepmode(step_mode, event.pressed.label)

    def set_stepmode(self, stepmode: int, step_mode_label):
        self.step_mode = stepmode
        self.motor_driver.set_stepmode(self.step_mode)
        if STEP_MODE_WRITE_TO_LOG:
            log = self.app.query_one("#logger", RichLog)
            log.write(f"StepMode set to {step_mode_label} µsteps.")
        self.app.query_one(StatusAdvanced).step_mode = f"Step Mode: {step_mode_label} µsteps"
