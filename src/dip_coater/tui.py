from pathlib import Path

from textual import on
from textual.app import App
from textual.app import ComposeResult
from textual.command import DiscoveryHit
from textual.command import Hit
from textual.command import Hits
from textual.command import Provider
from textual.containers import Container
from textual.containers import Horizontal
from textual.containers import Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button
from textual.widgets import Footer
from textual.widgets import Header
from textual.widgets import Label
from textual.widgets import MarkdownViewer
from textual.widgets import RadioButton
from textual.widgets import RadioSet
from textual.widgets import RichLog
from textual.widgets import Static

# Mock the import of RPi when the package is not available
try:
    import RPi
except ModuleNotFoundError:
    import sys
    import MyRPi
    sys.modules["RPi"] = MyRPi

import dip_coater.motor as motor

STEP_MODE_WRITE_TO_LOG = False

DEFAULT_SPEED = 10
SPEED_STEP = 1
MAX_SPEED = 100
MIN_SPEED = 1

DEFAULT_DISTANCE = 50
DISTANCE_STEP = 10
MAX_DISTANCE = 300
MIN_DISTANCE = 0

STEP_MODE = {
    "I16": "1/16",
    "I8": "1/8",
    "I4": "1/4",
    "I2": "Half",
    "I1": "Full",
}

class StepMode(Static):
    def __init__(self):
        super().__init__()
        self.step_mode = '1/4'

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Step Mode")
            with RadioSet(id="step-mode"):
                yield RadioButton("1/16", id="I16")
                yield RadioButton("1/8", id="I8")
                yield RadioButton("1/4", id="I4", value=True)
                yield RadioButton("1/2", id="I2")
                yield RadioButton("1", id="I1")

    def on_mount(self):
        self.app.query_one(Status).step_mode = f"StepMode: 1/4 mm/s"

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        self.step_mode = STEP_MODE[event.pressed.id]
        if STEP_MODE_WRITE_TO_LOG:
            log = self.app.query_one(RichLog)
            log.write(f"StepMode set to {event.pressed.label} mm/s")
        self.app.query_one(Status).step_mode = f"Step Mode: {event.pressed.label} mm/s ({self.step_mode})"


class MotorControls(Static):
    def __init__(self):
        super().__init__()
        self._motor_state: str = "disabled"

    def compose(self) -> ComposeResult:
        yield Button("move UP", id="move-up")
        yield Button("move DOWN", id="move-down")
        yield Button("enable motor", id="enable-motor")
        yield Button("disable motor", id="disable-motor")

    @property
    def motor_state(self):
        return self._motor_state

    def get_parameters(self) -> tuple:
        widget = self.app.query_one(DistanceControls)
        distance_mm = widget.distance
        widget = self.app.query_one(SpeedControls)
        speed_mm_s = widget.speed
        widget = self.app.query_one(StepMode)
        step_mode = widget.step_mode
        return distance_mm, speed_mm_s, step_mode

    @on(Button.Pressed, "#move-up")
    def move_up(self):
        log = self.app.query_one(RichLog)
        if self._motor_state == "enabled":
            distance_mm, speed_mm_s, step_mode = self.get_parameters()
            steps, delay = motor.calculate_steps_and_delay(distance_mm, speed_mm_s, step_mode)
            log.write(f"Moving up ({distance_mm=}, {speed_mm_s=}, {step_mode=}) with {steps=} and {delay=}.")

            motor.move_up(distance_mm, speed_mm_s, step_mode)
        else:
            log.write("[red]We cannot move up when the motor is disabled[/]")

    @on(Button.Pressed, "#move-down")
    def move_down(self):
        log = self.app.query_one(RichLog)
        if self._motor_state == "enabled":
            distance_mm, speed_mm_s, step_mode = self.get_parameters()
            steps, delay = motor.calculate_steps_and_delay(distance_mm, speed_mm_s, step_mode)
            log.write(f"Moving down ({distance_mm=}, {speed_mm_s=}, {step_mode=}) with {steps=} and {delay=}.")

            motor.move_down(distance_mm, speed_mm_s, step_mode)
        else:
            log.write("[red]We cannot move down when the motor is disabled[/]")

    @on(Button.Pressed, "#enable-motor")
    def enable_motor(self):
        log = self.app.query_one(RichLog)
        if self._motor_state == "disabled":
            motor.enable_motor()
            self._motor_state = "enabled"
            log.write(f"Motor is now enabled.")
            self.app.query_one(Status).motor = "Motor: [green]ENABLED[/]"

    @on(Button.Pressed, "#disable-motor")
    def disable_motor(self):
        log = self.app.query_one(RichLog)
        if self._motor_state == "enabled":
            motor.disable_motor()
            self._motor_state = "disabled"
            log.write(f"[dark_orange]Motor is now disabled.[/]")
            self.app.query_one(Status).motor = "Motor: [dark_orange]DISABLED[/]"


class SpeedControls(Widget):
    speed = reactive(DEFAULT_SPEED)

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label("Speed: ", id="speed-label")
            yield Button("UP", id="speed-up")
            yield Button("DOWN", id="speed-down")
            yield Label(f"{DEFAULT_SPEED} mm/s", id="speed-value")

    @on(Button.Pressed, "#speed-up")
    def increase_speed(self):
        if self.speed == 1:
            self.speed = SPEED_STEP
        else:
            self.speed += SPEED_STEP

    @on(Button.Pressed, "#speed-down")
    def decrease_speed(self):
        self.speed -= SPEED_STEP

    def watch_speed(self, speed: int):
        label = self.query_one("#speed-value", Label)
        label.update(f"{speed} mm/s")
        self.app.query_one(Status).speed = f"Speed: {speed} mm/s"

    def validate_speed(self, speed: int) -> int:
        if speed > MAX_SPEED:
            speed = MAX_SPEED
        elif speed < MIN_SPEED:
            speed = MIN_SPEED
        return speed


class DistanceControls(Static):
    distance = reactive(DEFAULT_DISTANCE)

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label("Distance: ", id="distance-label")
            yield Button("UP", id="distance-up")
            yield Button("DOWN", id="distance-down")
            yield Label(f"{DEFAULT_DISTANCE} mm", id="distance-value")

    @on(Button.Pressed, "#distance-up")
    def increase_distance(self):
        self.distance += DISTANCE_STEP

    @on(Button.Pressed, "#distance-down")
    def decrease_distance(self):
        self.distance -= DISTANCE_STEP

    def watch_distance(self, distance: int):
        label = self.query_one("#distance-value", Label)
        label.update(f"{distance} mm")
        self.app.query_one(Status).distance = f"Distance: {distance} mm"

    def validate_distance(self, distance: int) -> int:
        if distance > MAX_DISTANCE:
            distance = MAX_DISTANCE
        elif distance < MIN_DISTANCE:
            distance = MIN_DISTANCE
        return distance


class Status(Static):
    step_mode = reactive("Step Mode: ")
    speed = reactive("Speed: ")
    distance = reactive("Distance: ")
    motor = reactive("Motor: ")

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(id="status-step-mode")
            yield Label(id="status-speed")
            yield Label(id="status-distance")
            yield Label(id="status-motor")

    def on_mount(self):
        motor_state = self.app.query_one(MotorControls).motor_state
        color = "green" if motor_state == "enabled" else "dark_orange"
        self.motor = f"Motor: [{color}]{motor_state.upper()}[/]"

    def watch_step_mode(self, step_mode: str):
        self.query_one("#status-step-mode", Label).update(step_mode)

    def watch_speed(self, speed: str):
        self.query_one("#status-speed", Label).update(speed)

    def watch_distance(self, distance: str):
        self.query_one("#status-distance", Label).update(distance)

    def watch_motor(self, motor: str):
        self.query_one("#status-motor", Label).update(motor)


class HelpCommand(Provider):

    async def discover(self) -> Hits:
        app = self.app
        assert isinstance(app, DipCoaterApp)

        yield DiscoveryHit(
            display="Help",
            command=app.action_show_help,
            text="help text ??",
            help="Open help screen...",
        )

    async def search(self, query: str) -> Hits:
        """Search for Python files."""
        matcher = self.matcher(query)

        app = self.app
        assert isinstance(app, DipCoaterApp)

        command = f"help"
        score = matcher.match(command)
        if score > 0:
            yield Hit(
                score,
                matcher.highlight(command),
                app.action_show_help,
                help="Open help screen...",
            )


class HelpScreen(ModalScreen[None]):
    BINDINGS = [("escape", "pop_screen", "Close the help screen")]

    def compose(self) -> ComposeResult:
        with Container(id="help-container"):
            with open(Path(__file__).parent / "help.md") as text:
                yield MarkdownViewer(text.read(), show_table_of_contents=False)

class DipCoaterApp(App):
    """A Textual App to control a dip coater motor."""

    CSS_PATH = "tui.tcss"
    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("q", "request_quit", "Quit"),
        ("h", "show_help", "Help"),
    ]
    COMMANDS = App.COMMANDS | {HelpCommand}
    def on_mount(self):
        motor.init_motor_driver()

        # on_mount() is called after compose(), so the RichLog is known
        log = self.query_one(RichLog)
        log.write("Motor has been initialised.")

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Footer()
        with Horizontal():
            with Vertical(id="left-side"):
                yield StepMode()
                yield SpeedControls()
                yield DistanceControls()
                yield MotorControls()
                yield RichLog(markup=True, id="logger")
            with Vertical(id="right-side"):
                yield Status()

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark

    def action_request_quit(self) -> None:
        motor.disable_motor()
        motor.GPIO.cleanup()
        self.app.exit()

    def action_show_help(self):
        self.push_screen(HelpScreen())


def main():
    app = DipCoaterApp()
    app.run()


if __name__ == '__main__':
    main()
