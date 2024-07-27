from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.validation import Number
from textual.widget import Widget
from textual.widgets import Button, Input, Label

from dip_coater.constants import (
    DEFAULT_SPEED, MAX_SPEED, MIN_SPEED, SPEED_STEP_COARSE, SPEED_STEP_FINE
)
from dip_coater.widgets.status import Status
from dip_coater.utils.helpers import clamp


class SpeedControls(Widget):
    speed = reactive(DEFAULT_SPEED)

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label("Speed: ", id="speed-label")
            yield Button(f"-- {SPEED_STEP_COARSE}", id="speed-down-coarse", classes="btn-speed-control")
            yield Button(f"- {SPEED_STEP_FINE}", id="speed-down-fine", classes="btn-speed-control")
            yield Button(f"+ {SPEED_STEP_FINE}", id="speed-up-fine", classes="btn-speed-control")
            yield Button(f"++ {SPEED_STEP_COARSE}", id="speed-up-coarse", classes="btn-speed-control")
            yield Input(
                value=f"{DEFAULT_SPEED}",
                type="number",
                placeholder="Speed (mm/s)",
                id="speed-input",
                validate_on=["submitted"],
                validators=[Number(minimum=MIN_SPEED, maximum=MAX_SPEED)],
            )
            yield Label("mm/s", id="speed-unit")

    @on(Button.Pressed, "#speed-down-coarse")
    def decrease_speed_coarse(self):
        new_speed = self.speed - SPEED_STEP_COARSE
        self.set_speed(new_speed)

    @on(Button.Pressed, "#speed-down-fine")
    def decrease_speed_fine(self):
        new_speed = self.speed - SPEED_STEP_FINE
        self.set_speed(new_speed)

    @on(Button.Pressed, "#speed-up-fine")
    def increase_speed_fine(self):
        new_speed = self.speed + SPEED_STEP_FINE
        self.set_speed(new_speed)

    @on(Button.Pressed, "#speed-up-coarse")
    def increase_speed_coarse(self):
        new_speed = self.speed + SPEED_STEP_COARSE
        self.set_speed(new_speed)

    @on(Input.Submitted, "#speed-input")
    def submit_speed_input(self):
        speed_input = self.query_one("#speed-input", Input)
        speed = float(speed_input.value)
        self.set_speed(speed)

    def set_speed(self, speed: float):
        validated_speed = clamp(speed, MIN_SPEED, MAX_SPEED)
        self.speed = round(validated_speed, 2)

    def watch_speed(self, speed: float):
        speed_input = self.query_one("#speed-input", Input)
        speed_input.value = f"{speed}"
        self.app.query_one(Status).update_speed(speed)
