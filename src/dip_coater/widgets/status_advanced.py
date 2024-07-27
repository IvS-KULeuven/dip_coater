from textual.app import ComposeResult
from textual.reactive import reactive
from textual.containers import Vertical
from textual.widgets import Static, Label, Rule


class StatusAdvanced(Static):
    step_mode = reactive("Step Mode: ")
    acceleration = reactive("Acceleration: ")
    motor_current = reactive("Motor current: ")

    invert_motor_direction = reactive("Invert motor direction: ")
    interpolate = reactive("Interpolation: ")
    spread_cycle = reactive("Spread Cycle: ")

    homing_revs = reactive("Homing revolutions: ")
    homing_threshold = reactive("Homing StallGuard threshold: ")
    homing_speed = reactive("Homing speed: ")

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(id="status-step-mode")
            yield Label(id="status-acceleration")
            yield Label(id="status-motor-current")
            yield Rule()
            yield Label(id="status-invert-motor-direction")
            yield Label(id="status-interpolate")
            yield Label(id="status-spread-cycle")
            yield Rule()
            yield Label(id="status-homing-revolutions")
            yield Label(id="status-homing-threshold")
            yield Label(id="status-homing-speed")

    def watch_step_mode(self, step_mode: str):
        self.query_one("#status-step-mode", Label).update(step_mode)

    def update_step_mode(self, step_mode: str):
        self.step_mode = f"Step Mode: {step_mode}"

    def watch_acceleration(self, acceleration: str):
        self.query_one("#status-acceleration", Label).update(acceleration)

    def update_acceleration(self, acceleration: float):
        self.acceleration = f"Acceleration: {acceleration} mm/s\u00b2"

    def watch_motor_current(self, motor_current: str):
        self.query_one("#status-motor-current", Label).update(motor_current)

    def update_motor_current(self, motor_current: int):
        self.motor_current = f"Motor current: {motor_current} mA"

    def watch_invert_motor_direction(self, invert_direction: str):
        self.query_one("#status-invert-motor-direction", Label).update(invert_direction)

    def update_invert_motor_direction(self, invert_direction: bool):
        self.invert_motor_direction = f"Invert motor direction: {invert_direction}"

    def watch_interpolate(self, interpolate: str):
        self.query_one("#status-interpolate", Label).update(interpolate)

    def update_interpolate(self, interpolate: bool):
        self.interpolate = f"Interpolation: {interpolate}"

    def watch_spread_cycle(self, spread_cycle: str):
        self.query_one("#status-spread-cycle", Label).update(spread_cycle)

    def update_spread_cycle(self, spread_cycle: bool):
        self.spread_cycle = f"Spread Cycle: {spread_cycle}"

    def watch_homing_revs(self, homing_revs: str):
        self.query_one("#status-homing-revolutions", Label).update(homing_revs)

    def update_homing_revs(self, homing_revs: int):
        self.homing_revs = f"Homing revolutions: {homing_revs}"

    def watch_homing_threshold(self, homing_threshold: str):
        self.query_one("#status-homing-threshold", Label).update(homing_threshold)

    def update_homing_threshold(self, homing_threshold: int):
        self.homing_threshold = f"Homing StallGuard threshold: {homing_threshold}"

    def watch_homing_speed(self, homing_speed: str):
        self.query_one("#status-homing-speed", Label).update(homing_speed)

    def update_homing_speed(self, homing_speed: float):
        self.homing_speed = f"Homing speed: {homing_speed} mm/s"
