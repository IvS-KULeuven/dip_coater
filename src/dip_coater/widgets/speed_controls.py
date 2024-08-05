from textual import on, events
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.validation import Number
from textual.widget import Widget
from textual.widgets import Button, Input, Label

from dip_coater.utils.helpers import clamp


class SpeedControls(Widget):
    speed = reactive(None)

    def __init__(self, app_state):
        super().__init__()
        self.app_state = app_state

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label("Speed: ", id="speed-label")
            yield Button(f"-- {self.app_state.config.SPEED_STEP_COARSE}",
                         id="speed-down-coarse", classes="btn-speed-control")
            yield Button(f"- {self.app_state.config.SPEED_STEP_FINE}",
                         id="speed-down-fine", classes="btn-speed-control")
            yield Button(f"+ {self.app_state.config.SPEED_STEP_FINE}",
                         id="speed-up-fine", classes="btn-speed-control")
            yield Button(f"++ {self.app_state.config.SPEED_STEP_COARSE}",
                         id="speed-up-coarse", classes="btn-speed-control")
            yield Input(
                value=f"{self.app_state.config.DEFAULT_SPEED}",
                type="number",
                placeholder="Speed (mm/s)",
                id="speed-input",
                validate_on=["submitted"],
                validators=[Number(minimum=self.app_state.config.MIN_SPEED,
                                   maximum=self.app_state.config.MAX_SPEED)],
            )
            yield Label("mm/s", id="speed-unit")

    def _on_mount(self, event: events.Mount) -> None:
        self.update_speed(self.app_state.config.DEFAULT_SPEED)

    @on(Button.Pressed, "#speed-down-coarse")
    def decrease_speed_coarse(self):
        new_speed = self.speed - self.app_state.config.SPEED_STEP_COARSE
        self.update_speed(new_speed)

    @on(Button.Pressed, "#speed-down-fine")
    def decrease_speed_fine(self):
        new_speed = self.speed - self.app_state.config.SPEED_STEP_FINE
        self.update_speed(new_speed)

    @on(Button.Pressed, "#speed-up-fine")
    def increase_speed_fine(self):
        new_speed = self.speed + self.app_state.config.SPEED_STEP_FINE
        self.update_speed(new_speed)

    @on(Button.Pressed, "#speed-up-coarse")
    def increase_speed_coarse(self):
        new_speed = self.speed + self.app_state.config.SPEED_STEP_COARSE
        self.update_speed(new_speed)

    @on(Input.Submitted, "#speed-input")
    def submit_speed_input(self):
        speed_input = self.query_one("#speed-input", Input)
        speed = float(speed_input.value)
        self.update_speed(speed)

    def update_speed(self, speed: float):
        validated_speed = clamp(speed, self.app_state.config.MIN_SPEED,
                                self.app_state.config.MAX_SPEED)
        self.speed = round(validated_speed, 2)

    def watch_speed(self, speed: float):
        speed_input = self.query_one("#speed-input", Input)
        speed_input.value = f"{speed}"
        self.app_state.status.update_speed(speed)
        self.app_state.advanced_settings.update_motor_configuration()
