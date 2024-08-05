from textual.app import ComposeResult
from textual.reactive import reactive
from textual import on, events
from textual.containers import Vertical, Horizontal
from textual.validation import Number
from textual.widgets import Static, Checkbox, Input, RadioButton, Label

from dip_coater.widgets.step_mode import StepMode
from dip_coater.utils.helpers import clamp
from dip_coater.utils.SettingChanged import SettingChanged


class AdvancedSettingsBase(Static):
    _acceleration: reactive[float | None] = reactive(None)
    _current: reactive[int | None] = reactive(None)
    _current_standstill: reactive[int | None] = reactive(None)
    _invert_motor_direction: reactive[bool | None] = reactive(None)

    def __init__(self, app_state):
        super().__init__()
        self.app_state = app_state

        self.app_state.step_mode = StepMode(self.app_state)

    # --------------- UI INIT ---------------

    def compose(self) -> ComposeResult:
        with Vertical() as v:
            yield self.app_state.step_mode
            with Horizontal():
                with Horizontal():
                    yield Label("Acceleration: ", id="acceleration-label")
                    yield Input(
                        value=f"{self._acceleration}",
                        type="number",
                        placeholder="Acceleration (mm/s\u00b2)",
                        id="acceleration-input",
                        validate_on=["submitted"],
                        validators=[Number(minimum=self.app_state.config.MIN_ACCELERATION,
                                           maximum=self.app_state.config.MAX_ACCELERATION)],
                        classes="input-fields",
                    )
                    yield Label("mm/s\u00b2", id="acceleration-unit")
                with Horizontal():
                    yield Label("Motor current: ", id="current-label")
                    yield Input(
                        value=f"{self._current}",
                        type="number",
                        placeholder="Motor current (mA)",
                        id="current-input",
                        validate_on=["submitted"],
                        validators=[Number(minimum=self.app_state.config.MIN_CURRENT,
                                           maximum=self.app_state.config.MAX_CURRENT)],
                        classes="input-fields",
                    )
                    yield Label("mA", id="current-unit")
                with Horizontal():
                    yield Label("Motor standstill current: ", id="current-standstill-label")
                    yield Input(
                        value=f"{self._current_standstill}",
                        type="number",
                        placeholder="Standstill current (mA)",
                        id="current-standstill-input",
                        validate_on=["submitted"],
                        validators=[Number(minimum=self.app_state.config.MIN_CURRENT,
                                           maximum=self.app_state.config.MAX_CURRENT)],
                        classes="input-fields",
                    )
                    yield Label("mA", id="current-standstill-unit")
            yield from self.additional_widgets()

    def additional_widgets(self) -> ComposeResult:
        """Override this method in subclasses to add additional widgets."""
        yield from ()

    def _on_mount(self, event: events.Mount) -> None:
        self.reset_settings_to_default()

    def reset_settings_to_default(self):
        self.app_state.step_mode.update_microsteps(self.app_state.config.DEFAULT_STEP_MODE)
        self.app_state.step_mode.query_one(f"#{self.app_state.config.DEFAULT_STEP_MODE}",
                                           RadioButton).value = True
        self.update_acceleration(self.app_state.config.DEFAULT_ACCELERATION)
        self.query_one("#acceleration-input", Input).value = \
            f"{self.app_state.config.DEFAULT_ACCELERATION}"
        self.update_invert_motor_direction(self.app_state.config.INVERT_MOTOR_DIRECTION)
        self.query_one("#invert-motor-checkbox", Checkbox).value = (
            self.app_state.config.INVERT_MOTOR_DIRECTION)

        self.update_current(self.app_state.config.DEFAULT_CURRENT)
        self.query_one("#current-input", Input).value = \
            f"{self.app_state.config.DEFAULT_CURRENT}"
        self.update_current_standstill(self.app_state.config.DEFAULT_CURRENT_STANDSTILL)
        self.query_one("#current-standstill-input", Input).value = \
            f"{self.app_state.config.DEFAULT_CURRENT_STANDSTILL}"

    # --------------- WIDGET INTERACTIONS ---------------

    @on(Input.Submitted, "#acceleration-input")
    def submit_acceleration_input(self):
        acceleration_input = self.query_one("#acceleration-input", Input)
        acceleration = float(acceleration_input.value)
        acceleration_validated = clamp(acceleration, self.app_state.config.MIN_ACCELERATION,
                                       self.app_state.config.MAX_ACCELERATION)
        acceleration_input.value = f"{acceleration_validated}"
        self.update_acceleration(acceleration_validated)

    def update_acceleration(self, acceleration: reactive[float | None]):
        validated_acceleration = clamp(acceleration, self.app_state.config.MIN_ACCELERATION,
                                       self.app_state.config.MAX_ACCELERATION)
        self._acceleration = round(validated_acceleration, 1)

    @on(Input.Submitted, "#current-input")
    def submit_current_input(self):
        current_input = self.query_one("#current-input", Input)
        current = int(current_input.value)
        current_validated = clamp(current, self.app_state.config.MIN_CURRENT, self.app_state.config.MAX_CURRENT)
        current_input.value = f"{current_validated}"
        self.update_current(current_validated)

    def update_current(self, current: reactive[int | None]):
        self._current = clamp(current, self.app_state.config.MIN_CURRENT, self.app_state.config.MAX_CURRENT)

    @on(Input.Submitted, "#current-standstill-input")
    def submit_current_standstill_input(self):
        current_standstill_input = self.query_one("#current-standstill-input", Input)
        current_standstill = int(current_standstill_input.value)
        current_standstill_validated = clamp(current_standstill, self.app_state.config.MIN_CURRENT,
                                             self.app_state.config.MAX_CURRENT)
        current_standstill_input.value = f"{current_standstill_validated}"
        self.update_current_standstill(current_standstill_validated)

    def update_current_standstill(self, current_standstill: reactive[int | None]):
        self._current_standstill = clamp(current_standstill, self.app_state.config.MIN_CURRENT,
                                         self.app_state.config.MAX_CURRENT)

    @on(Checkbox.Changed, "#invert-motor-checkbox")
    def toggle_invert_motor(self, event: Checkbox.Changed):
        invert_direction = event.checkbox.value
        self.update_invert_motor_direction(invert_direction)

    def update_invert_motor_direction(self, invert_direction: reactive[bool | None]):
        self._invert_motor_direction = invert_direction

    # --------------- WATCHERS (called automatically when reactive has changed) ---------------
    
    def watch__acceleration(self, acceleration: float):
        if acceleration is None:
            return
        self.post_message(SettingChanged("acceleration", acceleration))

    def watch__current(self, current: int):
        if current is None:
            return
        self.post_message(SettingChanged("current", current))

    def watch__current_standstill(self, current_standstill: int):
        if current_standstill is None:
            return
        self.post_message(SettingChanged("current_standstill", current_standstill))

    def watch__invert_motor_direction(self, invert_direction: bool):
        if invert_direction is None:
            return
        self.post_message(SettingChanged("invert_direction", invert_direction))

    # --------------- GETTERS/SETTERS ---------------

    def get_acceleration(self) -> float:
        return self._acceleration
