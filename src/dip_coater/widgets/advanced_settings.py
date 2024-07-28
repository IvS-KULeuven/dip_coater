from textual.reactive import reactive
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.validation import Number
from textual import on, events
from textual.widgets import Static, Label, Button, Checkbox, Rule, Input, RadioButton, RichLog

from dip_coater.constants import (
       DEFAULT_ACCELERATION, DEFAULT_CURRENT, INVERT_MOTOR_DIRECTION, USE_INTERPOLATION, USE_SPREAD_CYCLE,
       HOMING_REVOLUTIONS, HOMING_THRESHOLD, HOMING_SPEED_MM_S, MIN_ACCELERATION, MAX_ACCELERATION, MIN_CURRENT,
       MAX_CURRENT, HOMING_MIN_REVOLUTIONS, HOMING_MAX_REVOLUTIONS, HOMING_MIN_THRESHOLD, HOMING_MAX_THRESHOLD,
       HOMING_MIN_SPEED, HOMING_MAX_SPEED, DEFAULT_STEP_MODE, STEP_MODES, STEP_MODE_LABELS
)
from dip_coater.widgets.step_mode import StepMode
from dip_coater.widgets.status_advanced import StatusAdvanced
from dip_coater.motor.tmc2209 import TMC2209_MotorDriver
from dip_coater.utils.helpers import clamp

class AdvancedSettings(Static):
    acceleration = reactive(DEFAULT_ACCELERATION)
    motor_current = reactive(DEFAULT_CURRENT)
    invert_motor_direction = reactive(INVERT_MOTOR_DIRECTION)
    interpolate = reactive(USE_INTERPOLATION)
    spread_cycle = reactive(USE_SPREAD_CYCLE)
    homing_revs = reactive(HOMING_REVOLUTIONS)
    homing_threshold = reactive(HOMING_THRESHOLD)
    homing_speed = reactive(HOMING_SPEED_MM_S)

    def __init__(self, motor_driver: TMC2209_MotorDriver):
        super().__init__()
        self.motor_driver = motor_driver

    def compose(self) -> ComposeResult:
        with Vertical():
            yield StepMode(self.motor_driver)
            with Horizontal():
                with Horizontal():
                    yield Label("Acceleration: ", id="acceleration-label")
                    yield Input(
                        value=f"{self.acceleration}",
                        type="number",
                        placeholder="Acceleration (mm/s\u00b2)",
                        id="acceleration-input",
                        validate_on=["submitted"],
                        validators=[Number(minimum=MIN_ACCELERATION, maximum=MAX_ACCELERATION)],
                        classes="input-fields",
                    )
                    yield Label("mm/s\u00b2", id="acceleration-unit")
                with Horizontal():
                    yield Label("Motor current: ", id="motor-current-label")
                    yield Input(
                        value=f"{self.motor_current}",
                        type="number",
                        placeholder="Motor current (mA)",
                        id="motor-current-input",
                        validate_on=["submitted"],
                        validators=[Number(minimum=MIN_CURRENT, maximum=MAX_CURRENT)],
                        classes="input-fields",
                    )
                    yield Label("mA", id="motor-current-unit")
            with Horizontal(id="interpolation-container"):
                yield Checkbox("Invert motor direction", value=INVERT_MOTOR_DIRECTION, id="invert-motor-checkbox",
                               classes="checkbox")
                yield Checkbox("Interpolation", value=self.interpolate, id="interpolation-checkbox", classes="checkbox")
                yield Checkbox("Spread Cycle (T)/Stealth Chop (F)", value=self.spread_cycle, id="spread-cycle-checkbox", classes="checkbox")

            yield Rule(classes="rule")

            with Horizontal(id="homing-container"):
                with Horizontal():
                    yield Label("Homing revolutions: ", id="homing-revolutions-label")
                    yield Input(
                        value=f"{self.homing_revs}",
                        type="number",
                        placeholder="Homing revolutions",
                        id="homing-revolutions-input",
                        validate_on=["submitted"],
                        validators=[Number(minimum=HOMING_MIN_REVOLUTIONS, maximum=HOMING_MAX_REVOLUTIONS)],
                        classes="input-fields",
                    )
                with Horizontal():
                    yield Label("Homing threshold: ", id="homing-threshold-label")
                    yield Input(
                        value=f"{self.homing_threshold}",
                        type="number",
                        placeholder="Homing threshold",
                        id="homing-threshold-input",
                        validate_on=["submitted"],
                        validators=[Number(minimum=HOMING_MIN_THRESHOLD, maximum=HOMING_MAX_THRESHOLD)],
                        classes="input-fields",
                    )
                with Horizontal():
                    yield Label("Homing speed: ", id="homing-speed-label")
                    yield Input(
                        value=f"{self.homing_speed}",
                        type="number",
                        placeholder="Homing speed (RPM)",
                        id="homing-speed-input",
                        validate_on=["submitted"],
                        validators=[Number(minimum=HOMING_MIN_SPEED, maximum=HOMING_MAX_SPEED)],
                        classes="input-fields",
                    )
                    yield Label("RPM", id="homing-speed-unit")
            yield Button("Test StallGuard Threshold", id="test-stallguard-threshold-btn")

    def _on_mount(self, event: events.Mount) -> None:
        self.app.query_one(StatusAdvanced).update_acceleration(self.acceleration)
        self.app.query_one(StatusAdvanced).update_motor_current(self.motor_current)

        self.app.query_one(StatusAdvanced).update_invert_motor_direction(self.invert_motor_direction)
        self.app.query_one(StatusAdvanced).update_interpolate(self.interpolate)
        self.app.query_one(StatusAdvanced).update_spread_cycle(self.spread_cycle)

        self.app.query_one(StatusAdvanced).update_homing_revs(self.homing_revs)
        self.app.query_one(StatusAdvanced).update_homing_threshold(self.homing_threshold)
        self.app.query_one(StatusAdvanced).update_homing_speed(self.homing_speed)

    def reset_settings_to_default(self):
        self.query_one(StepMode).set_stepmode(STEP_MODES[DEFAULT_STEP_MODE], STEP_MODE_LABELS[DEFAULT_STEP_MODE])
        self.query_one(StepMode).query_one(f"#{DEFAULT_STEP_MODE}", RadioButton).value = True
        self.set_acceleration(DEFAULT_ACCELERATION)
        self.query_one("#acceleration-input", Input).value = f"{DEFAULT_ACCELERATION}"
        self.set_motor_current(DEFAULT_CURRENT)
        self.query_one("#motor-current-input", Input).value = f"{DEFAULT_CURRENT}"

        self.set_invert_motor_direction(INVERT_MOTOR_DIRECTION)
        self.query_one("#invert-motor-checkbox", Checkbox).value = INVERT_MOTOR_DIRECTION
        self.set_interpolate(USE_INTERPOLATION)
        self.query_one("#interpolation-checkbox", Checkbox).value = USE_INTERPOLATION
        self.set_spread_cycle(USE_SPREAD_CYCLE)
        self.query_one("#spread-cycle-checkbox", Checkbox).value = USE_SPREAD_CYCLE

        self.set_homing_revs(HOMING_REVOLUTIONS)
        self.query_one("#homing-revolutions-input", Input).value = f"{HOMING_REVOLUTIONS}"
        self.set_homing_threshold(HOMING_THRESHOLD)
        self.query_one("#homing-threshold-input", Input).value = f"{HOMING_THRESHOLD}"
        self.set_homing_speed(HOMING_SPEED_MM_S)
        self.query_one("#homing-speed-input", Input).value = f"{HOMING_SPEED_MM_S}"

    @on(Input.Submitted, "#acceleration-input")
    def submit_acceleration_input(self):
        acceleration_input = self.query_one("#acceleration-input", Input)
        acceleration = float(acceleration_input.value)
        acceleration_validated = clamp(acceleration, MIN_ACCELERATION, MAX_ACCELERATION)
        acceleration_input.value = f"{acceleration_validated}"
        self.set_acceleration(acceleration_validated)

    @on(Input.Submitted, "#motor-current-input")
    def submit_motor_current_input(self):
        motor_current_input = self.query_one("#motor-current-input", Input)
        motor_current = int(motor_current_input.value)
        motor_current_validated = clamp(motor_current, MIN_CURRENT, MAX_CURRENT)
        motor_current_input.value = f"{motor_current_validated}"
        self.set_motor_current(motor_current_validated)

    @on(Checkbox.Changed, "#invert-motor-checkbox")
    def toggle_invert_motor(self, event: Checkbox.Changed):
        invert_motor = event.checkbox.value
        self.set_invert_motor_direction(invert_motor)

    @on(Checkbox.Changed, "#interpolation-checkbox")
    def toggle_interpolation(self, event: Checkbox.Changed):
        interpolate = event.checkbox.value
        self.set_interpolate(interpolate)

    @on(Checkbox.Changed, "#spread-cycle-checkbox")
    def toggle_spread_cycle(self, event: Checkbox.Changed):
        spread_cycle = event.checkbox.value
        self.set_spread_cycle(spread_cycle)

    @on(Input.Submitted, "#homing-revolutions-input")
    def submit_homing_revs_input(self):
        homing_revs_input = self.query_one("#homing-revolutions-input", Input)
        homing_revs = int(homing_revs_input.value)
        homing_revs_validated = clamp(homing_revs, HOMING_MIN_REVOLUTIONS, HOMING_MAX_REVOLUTIONS)
        homing_revs_input.value = f"{homing_revs_validated}"
        self.set_homing_revs(homing_revs_validated)

    @on(Input.Submitted, "#homing-threshold-input")
    def submit_homing_threshold_input(self):
        homing_threshold_input = self.query_one("#homing-threshold-input", Input)
        homing_threshold = int(homing_threshold_input.value)
        homing_threshold_validated = clamp(homing_threshold, HOMING_MIN_THRESHOLD, HOMING_MAX_THRESHOLD)
        homing_threshold_input.value = f"{homing_threshold_validated}"
        self.set_homing_threshold(homing_threshold_validated)

    @on(Input.Submitted, "#homing-speed-input")
    def submit_homing_speed_input(self):
        homing_speed_input = self.query_one("#homing-speed-input", Input)
        homing_speed = float(homing_speed_input.value)
        homing_speed_validated = clamp(homing_speed, HOMING_MIN_SPEED, HOMING_MAX_SPEED)
        homing_speed_input.value = f"{homing_speed_validated}"
        self.set_homing_speed(homing_speed_validated)

    @on(Button.Pressed, "#test-stallguard-threshold-btn")
    async def test_stallguard_threshold(self):
        log = self.app.query_one("#logger", RichLog)
        log.write("[cyan]Testing StallGuard threshold...[/]")
        self.motor_driver.test_stallguard_threshold()
        log.write("[cyan]-> Finished testing StallGuard threshold.[/]")

    def set_acceleration(self, acceleration: float):
        validated_acceleration = clamp(acceleration, MIN_ACCELERATION, MAX_ACCELERATION)
        self.acceleration = round(validated_acceleration, 1)
        self.app.query_one(StatusAdvanced).update_acceleration(self.acceleration)

    def set_motor_current(self, motor_current: int):
        self.motor_current = clamp(motor_current, MIN_CURRENT, MAX_CURRENT)
        self.motor_driver.set_current(self.motor_current)
        self.app.query_one(StatusAdvanced).update_motor_current(self.motor_current)

    def set_invert_motor_direction(self, invert_direction: bool):
        self.invert_motor_direction = invert_direction
        self.motor_driver.set_direction(self.invert_motor_direction)
        self.app.query_one(StatusAdvanced).update_invert_motor_direction(self.invert_motor_direction)

    def set_interpolate(self, interpolate: bool):
        self.interpolate = interpolate
        self.motor_driver.set_interpolation(self.interpolate)
        self.app.query_one(StatusAdvanced).update_interpolate(self.interpolate)

    def set_spread_cycle(self, spread_cycle: bool):
        self.spread_cycle = spread_cycle
        self.motor_driver.set_spreadcycle(self.spread_cycle)
        self.app.query_one(StatusAdvanced).update_spread_cycle(self.spread_cycle)

    def set_homing_revs(self, homing_revs: int):
        self.homing_revs = homing_revs
        self.app.query_one(StatusAdvanced).update_homing_revs(self.homing_revs)

    def set_homing_threshold(self, homing_threshold: int):
        self.homing_threshold = homing_threshold
        self.app.query_one(StatusAdvanced).update_homing_threshold(self.homing_threshold)

    def set_homing_speed(self, homing_speed: float):
        self.homing_speed = homing_speed
        self.app.query_one(StatusAdvanced).update_homing_speed(self.homing_speed)
