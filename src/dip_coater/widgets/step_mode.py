from textual.containers import Vertical
from textual.app import ComposeResult
from textual.widgets import Label, RadioSet, RadioButton, RichLog, Static


class StepMode(Static):
    def __init__(self, app_state):
        super().__init__()
        self.app_state = app_state
        self.step_mode = self.app_state.config.STEP_MODES[self.app_state.config.DEFAULT_STEP_MODE]

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Step Mode")
            with RadioSet(id="step-mode"):
                for mode, label in self.app_state.config.STEP_MODE_LABELS.items():
                    yield RadioButton(label, id=mode)

    def on_mount(self):
        self.app_state.motor_driver.set_microsteps(self.step_mode)
        self.query_one(f"#{self.app_state.config.DEFAULT_STEP_MODE}", RadioButton).value = True

    def update_microsteps(self, microsteps: int):
        """ Update the microsteps value.

        :param microsteps: The microsteps value (1, 2, 4, ...).
        """
        step_mode = self.app_state.config.STEP_MODES[microsteps]
        self.set_microsteps(step_mode, self.app_state.config.STEP_MODE_LABELS[microsteps])

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        step_mode = self.app_state.config.STEP_MODES[event.pressed.id]
        self.set_microsteps(step_mode, event.pressed.label)

    def set_microsteps(self, step_mode: int, step_mode_label):
        self.step_mode = step_mode
        self.app_state.motor_driver.set_microsteps(self.step_mode)
        if self.app_state.config.STEP_MODE_WRITE_TO_LOG:
            log = self.app.query_one("#logger", RichLog)
            log.write(f"StepMode set to {step_mode_label} µsteps.")
        self.app_state.status_advanced.update_step_mode(step_mode_label)
