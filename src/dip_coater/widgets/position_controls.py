import asyncio

from textual.app import ComposeResult
from textual import on, events
from textual.reactive import reactive
from textual.validation import Number
from textual.containers import Horizontal
from textual.widgets import Static, Label, Button, Input, RichLog

from dip_coater.widgets.speed_controls import SpeedControls
from dip_coater.utils.helpers import clamp


class PositionControls(Static):
    position: reactive[float | None] = reactive(None)

    def __init__(self, app_state):
        super().__init__()
        self.app_state = app_state

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label("Position: ", id="position-label")
            yield Button(
                f"-- {self.app_state.config.DISTANCE_STEP_COARSE}",
                id="position-down-coarse",
                classes="btn-position-control btn-position",
            )
            yield Button(
                f"- {self.app_state.config.DISTANCE_STEP_FINE}",
                id="position-down-fine",
                classes="btn-position-control btn-position",
            )
            yield Button(
                f"+ {self.app_state.config.DISTANCE_STEP_FINE}",
                id="position-up-fine",
                classes="btn-position-control btn-position",
            )
            yield Button(
                f"++ {self.app_state.config.DISTANCE_STEP_COARSE}",
                id="position-up-coarse",
                classes="btn-position-control btn-position",
            )
            yield Button(
                "Set to current position",
                id="set-to-current-pos-btn",
                classes="btn-position",
            )
            yield Input(
                value="0",
                type="number",
                placeholder="Position (mm)",
                id="position-input",
                validate_on=["submitted"],
                validators=[
                    Number(
                        minimum=self.app_state.setup_profile.min_position_mm,
                        maximum=self.app_state.setup_profile.max_position_mm,
                    )
                ],
            )
            yield Label("mm", id="position-unit")
            yield Button(
                "Move to position",
                id="move-to-position-btn",
                variant="primary",
                classes="btn-small btn-position",
            )

    def _on_mount(self, event: events.Mount) -> None:
        self.position = 0
        self.update_button_states(self.app_state.motion_controller.is_homing_found())

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
        pos = self.app_state.motion_controller.get_current_position_mm()
        if pos is not None:
            self.set_position(pos)

    @on(Button.Pressed, "#move-to-position-btn")
    async def move_to_position_action(self):
        pos = float(self.position)
        speed = self.app.query_one(SpeedControls).speed
        accel = self.app_state.advanced_settings.get_acceleration()
        await self.move_to_position(pos, speed, accel)

    async def move_to_position(
        self,
        position_mm: float,
        speed_mm_s: float = None,
        acceleration_mm_s2: float = None,
        home_up: bool = None,
    ):
        log = self.app.query_one("#logger", RichLog)
        if self.app_state.motor_state != "enabled":
            log.write(
                "[red]Cannot move to a position while the motor is "
                f"{self.app_state.motor_state}.[/]"
            )
            return

        if acceleration_mm_s2 is None:
            acceleration_mm_s2 = self.app_state.advanced_settings.get_acceleration()

        log.write(
            f"[cyan]Moving to position ({position_mm=} mm, "
            f"{speed_mm_s=} mm/s, {acceleration_mm_s2=} mm/s\u00b2).[/]"
        )
        self.app_state.motor_controls.set_motor_state("moving")
        await asyncio.sleep(0.1)
        try:
            self.app_state.motion_controller.move_to_position(
                position_mm, speed_mm_s, acceleration_mm_s2
            )
            stop = await self.app_state.motion_controller.wait_for_motor_done_async()
            if self.app_state.motor_state == "disabled":
                return
            if stop is None or getattr(stop, "name", None) == "NO":
                log.write("[green]-> Finished moving to position.[/]")
            else:
                log.write(f"[red]-> Stopped moving to position {stop}.[/]")
        except ValueError as e:
            log.write(f"[red]{e}[/]")
        finally:
            if self.app_state.motor_state != "disabled":
                self.app_state.motor_controls.set_motor_state("enabled")

    def set_position(self, position: float):
        validated_position = clamp(
            position,
            self.app_state.setup_profile.min_position_mm,
            self.app_state.setup_profile.max_position_mm,
        )
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
