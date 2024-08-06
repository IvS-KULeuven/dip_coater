from textual.app import ComposeResult
from textual import on, events
from textual.reactive import reactive
from textual.validation import Number
from textual.containers import Horizontal
from textual.widgets import Static, Label, Button, Input

from dip_coater.widgets.speed_controls import SpeedControls
from dip_coater.utils.helpers import clamp


class PositionControls(Static):
    def __init__(self, app_state):
        super().__init__()
        self.app_state = app_state

        self.position: reactive[float | None] = reactive(None)

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label("Position: ", id="position-label")
            yield Button(f"-- {self.app_state.config.DISTANCE_STEP_COARSE}",
                         id="position-down-coarse",
                         classes="btn-position-control btn-position")
            yield Button(f"- {self.app_state.config.DISTANCE_STEP_FINE}",
                         id="position-down-fine",
                         classes="btn-position-control btn-position")
            yield Button(f"+ {self.app_state.config.DISTANCE_STEP_FINE}",
                         id="position-up-fine",
                         classes="btn-position-control btn-position")
            yield Button(f"++ {self.app_state.config.DISTANCE_STEP_COARSE}",
                         id="position-up-coarse",
                         classes="btn-position-control btn-position")
            yield Button("Set to current position", id="set-to-current-pos-btn",
                         classes="btn-position")
            yield Input(
                value="0",
                type="number",
                placeholder="Position (mm)",
                id="position-input",
                validate_on=["submitted"],
                validators=[Number(minimum=0, maximum=250)],
            )
            yield Label("mm", id="position-unit")
            yield Button("Move to position", id="move-to-position-btn", variant="primary",
                         classes="btn-small btn-position")

    def _on_mount(self, event: events.Mount) -> None:
        self.position = 0
        self.update_button_states(self.app_state.motor_driver.is_homing_found())

    @on(Button.Pressed, "#position-down-coarse")
    def decrease_position_coarse(self):
        new_position = self.position - self.app_state.config.POSITION_STEP_COARSE
        self.set_position(new_position)

    @on(Button.Pressed, "#position-down-fine")
    def decrease_distance_fine(self):
        new_position = self.position - self.app_state.config.POSITION_STEP_FINE
        self.set_position(new_position)

    @on(Button.Pressed, "#position-up-fine")
    def increase_position_fine(self):
        new_position = self.position + self.app_state.config.POSITION_STEP_FINE
        self.set_position(new_position)

    @on(Button.Pressed, "#position-up-coarse")
    def increase_position_coarse(self):
        new_position = self.position + self.app_state.config.POSITION_STEP_COARSE
        self.set_position(new_position)

    @on(Button.Pressed, "#set-to-current-pos-btn")
    def set_to_current_position(self):
        pos = self.app_state.motor_driver.get_current_position_mm()
        if pos is not None:
            self.set_position(pos)

    @on(Button.Pressed, "#move-to-position-btn")
    async def move_to_position_action(self):
        pos = float(self.position)
        speed = self.app.query_one(SpeedControls).speed
        accel = self.app_state.advanced_settings.get_acceleration()
        await self.move_to_position(pos, speed, accel)

    async def move_to_position(self, position_mm: float, speed_mm_s: float = None,
                               acceleration_mm_s2: float = None, home_up: bool = None):
        if home_up is None:
            home_up = self.app_state.config.HOME_UP
        self.app_state.motor_driver.run_to_position(position_mm, speed_mm_s, acceleration_mm_s2,
                                                    home_up)

    def set_position(self, position: float):
        validated_position = clamp(position, self.app_state.config.MIN_POSITION,
                                   self.app_state.config.MAX_POSITION)
        self.position = round(validated_position, 1)

    def watch_position(self, position: float):
        distance_input = self.query_one("#position-input", Input)
        distance_input.value = f"{position}"

    @on(Input.Submitted, "#position-input")
    def submit_position_input(self):
        position_input = self.query_one("#position-input", Input)
        position = float(position_input.value)
        self.set_position(position)

    def update_button_states(self, homing_found):
        self.query_one("#set-to-current-pos-btn", Button).disabled = not homing_found
        self.query_one("#move-to-position-btn", Button).disabled = not homing_found
