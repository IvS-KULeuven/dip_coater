from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.validation import Number
from textual import on
from textual.widgets import Static, Label, Button, Input

from dip_coater.constants import (
    DEFAULT_DISTANCE, DISTANCE_STEP_COARSE, DISTANCE_STEP_FINE, MAX_DISTANCE, MIN_DISTANCE
)
from dip_coater.utils.helpers import clamp

class DistanceControls(Static):
    distance = reactive(DEFAULT_DISTANCE)

    def __init__(self, app_state):
        super().__init__()
        self.app_state = app_state

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label("Distance: ", id="distance-label")
            yield Button(f"-- {DISTANCE_STEP_COARSE}", id="distance-down-coarse", classes="btn-distance-control")
            yield Button(f"- {DISTANCE_STEP_FINE}", id="distance-down-fine", classes="btn-distance-control")
            yield Button(f"+ {DISTANCE_STEP_FINE}", id="distance-up-fine", classes="btn-distance-control")
            yield Button(f"++ {DISTANCE_STEP_COARSE}", id="distance-up-coarse", classes="btn-distance-control")
            yield Input(
                value=f"{DEFAULT_DISTANCE}",
                type="number",
                placeholder="Distance (mm)",
                id="distance-input",
                validate_on=["submitted"],
                validators=[Number(minimum=MIN_DISTANCE, maximum=MAX_DISTANCE)],
            )
            yield Label("mm", id="distance-unit")

    @on(Button.Pressed, "#distance-down-coarse")
    def decrease_distance_coarse(self):
        new_distance = self.distance - DISTANCE_STEP_COARSE
        self.set_distance(new_distance)

    @on(Button.Pressed, "#distance-down-fine")
    def decrease_distance_fine(self):
        new_distance = self.distance - DISTANCE_STEP_FINE
        self.set_distance(new_distance)

    @on(Button.Pressed, "#distance-up-fine")
    def increase_distance_fine(self):
        new_distance = self.distance + DISTANCE_STEP_FINE
        self.set_distance(new_distance)

    @on(Button.Pressed, "#distance-up-coarse")
    def increase_distance_coarse(self):
        new_distance = self.distance + DISTANCE_STEP_COARSE
        self.set_distance(new_distance)

    @on(Input.Submitted, "#distance-input")
    def submit_distance_input(self):
        distance_input = self.query_one("#distance-input", Input)
        distance = float(distance_input.value)
        self.set_distance(distance)

    def set_distance(self, distance: float):
        validated_distance = clamp(distance, MIN_DISTANCE, MAX_DISTANCE)
        self.distance = round(validated_distance, 1)

    def watch_distance(self, distance: float):
        distance_input = self.query_one("#distance-input", Input)
        distance_input.value = f"{distance}"
        self.app_state.status.update_distance(distance)
