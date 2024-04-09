from pathlib import Path

from textual import on, events
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
from textual.widgets import Input
from textual.widgets import MarkdownViewer
from textual.widgets import RadioButton
from textual.widgets import RadioSet
from textual.widgets import RichLog
from textual.widgets import Static
from textual.widgets import TabPane
from textual.widgets import TabbedContent
from textual.widgets import TextArea
from textual.validation import Number

import argparse
import asyncio
import time

# Mock the import of RPi when the package is not available
try:
    import RPi
except ModuleNotFoundError:
    import sys
    import MyRPi
    sys.modules["RPi"] = MyRPi

try:
    import TMC_2209
except ModuleNotFoundError:
    import sys
    import MyTMC_2209 as TMC_2209
    sys.modules["TMC_2209"] = TMC_2209

from TMC_2209._TMC_2209_logger import Loglevel
from dip_coater.motor import TMC2209_MotorDriver

# Logging settings
STEP_MODE_WRITE_TO_LOG = False
LOGGING_LEVEL = Loglevel.ERROR  # NONE, ERROR, INFO, DEBUG, MOVEMENT, ALL

# Speed settings (mm/s)
DEFAULT_SPEED = 5
SPEED_STEP_COARSE = 1
SPEED_STEP_FINE = 0.1
MAX_SPEED = 20
MIN_SPEED = 0.01

# Distance settings (mm)
DEFAULT_DISTANCE = 10
DISTANCE_STEP_COARSE = 5
DISTANCE_STEP_FINE = 1
MAX_DISTANCE = 250
MIN_DISTANCE = 0

# Acceleration settings (mm/s^2)
DEFAULT_ACCELERATION = 20
MIN_ACCELERATION = 0.5
MAX_ACCELERATION = 50

STEP_MODE = {
    "I1": 1,
    "I2": 2,
    "I4": 4,
    "I8": 8,
    "I16": 16,
    "I32": 32,
    "I64": 64,
    "I128": 128,
    "I256": 256,
}

class StepMode(Static):
    def __init__(self, motor_driver: TMC2209_MotorDriver):
        super().__init__()
        self.step_mode = 8
        self.motor_driver = motor_driver
        self.motor_driver.set_stepmode(self.step_mode)

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Step Mode")
            with RadioSet(id="step-mode"):
                yield RadioButton("1", id="I1")
                yield RadioButton("1/2", id="I2")
                yield RadioButton("1/4", id="I4")
                yield RadioButton("1/8", id="I8", value=True)
                yield RadioButton("1/16", id="I16")
                yield RadioButton("1/32", id="I32")
                #yield RadioButton("1/64", id="I64")
                #yield RadioButton("1/128", id="I128")
                #yield RadioButton("1/256", id="I256")

    def on_mount(self):
        self.app.query_one(Status).step_mode = f"StepMode: 1/8 µsteps"

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        self.step_mode = STEP_MODE[event.pressed.id]
        self.motor_driver.set_stepmode(self.step_mode)
        if STEP_MODE_WRITE_TO_LOG:
            log = self.app.query_one("#logger", RichLog)
            log.write(f"StepMode set to {event.pressed.label} µsteps.")
        self.app.query_one(Status).step_mode = f"Step Mode: {event.pressed.label} µsteps ({self.step_mode})"


class MotorControls(Static):
    def __init__(self, motor_driver: TMC2209_MotorDriver):
        super().__init__()
        self._motor_state: str = "disabled"
        self.motor_driver = motor_driver

    def compose(self) -> ComposeResult:
        yield Button("Move UP", id="move-up")
        yield Button("Move DOWN", id="move-down")
        yield Button("Enable motor", id="enable-motor")
        yield Button("Disable motor", id="disable-motor")

    @property
    def motor_state(self):
        return self._motor_state

    def get_parameters(self) -> tuple:
        widget = self.app.query_one(DistanceControls)
        distance_mm = widget.distance
        widget = self.app.query_one(SpeedControls)
        speed_mm_s = widget.speed
        widget = self.app.query_one(AdvancedSettings)
        accel_mm_s2 = widget.acceleration
        widget = self.app.query_one(StepMode)
        step_mode = widget.step_mode
        return distance_mm, speed_mm_s, accel_mm_s2, step_mode

    @on(Button.Pressed, "#move-up")
    def move_up_action(self):
        distance_mm, speed_mm_s, accel_mm_s2, step_mode = self.get_parameters()
        self.move_up(distance_mm, speed_mm_s, accel_mm_s2)

    def move_up(self, distance_mm: float, speed_mm_s: float, acceleration_mm_s2: float = None):
        log = self.app.query_one("#logger", RichLog)
        if self._motor_state == "enabled":
            def_dist, def_speed, def_accel, step_mode = self.get_parameters()
            if acceleration_mm_s2 is None:
                acceleration_mm_s2 = def_accel
            log.write(
                f"Moving up ({distance_mm=} mm, {speed_mm_s=} mm/s, {acceleration_mm_s2=} mm/s^2, {step_mode=} step mode).")
            self.motor_driver.move_up(distance_mm, speed_mm_s, acceleration_mm_s2)
        else:
            log.write("[red]We cannot move up when the motor is disabled[/]")

    @on(Button.Pressed, "#move-down")
    def move_down_action(self):
        distance_mm, speed_mm_s, accel_mm_s2, step_mode = self.get_parameters()
        self.move_down(distance_mm, speed_mm_s, accel_mm_s2)

    def move_down(self, distance_mm: float, speed_mm_s: float, acceleration_mm_s2: float = None):
        log = self.app.query_one("#logger", RichLog)
        if self._motor_state == "enabled":
            def_dist, def_speed, def_accel, step_mode = self.get_parameters()
            if acceleration_mm_s2 is None:
                acceleration_mm_s2 = def_accel
            log.write(
                f"Moving down ({distance_mm=} mm, {speed_mm_s=} mm/s, {acceleration_mm_s2=} mm/s^2, {step_mode=} step mode).")
            self.motor_driver.move_down(distance_mm, speed_mm_s, acceleration_mm_s2)
        else:
            log.write("[red]We cannot move down when the motor is disabled[/]")

    @on(Button.Pressed, "#enable-motor")
    def enable_motor_action(self):
        log = self.app.query_one("#logger", RichLog)
        if self._motor_state == "disabled":
            self.motor_driver.enable_motor()
            self._motor_state = "enabled"
            log.write(f"[green]Motor is now enabled.[/]")
            self.app.query_one(Status).motor = "Motor: [green]ENABLED[/]"

    @on(Button.Pressed, "#disable-motor")
    def disable_motor_action(self):
        log = self.app.query_one("#logger", RichLog)
        if self._motor_state == "enabled":
            self.motor_driver.disable_motor()
            self._motor_state = "disabled"
            log.write(f"[dark_orange]Motor is now disabled.[/]")
            self.app.query_one(Status).motor = "Motor: [dark_orange]DISABLED[/]"


class SpeedControls(Widget):
    speed = reactive(DEFAULT_SPEED)

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label("Speed: ", id="speed-label")
            yield Button(f"-- {SPEED_STEP_COARSE}", id="speed-down-coarse")
            yield Button(f"- {SPEED_STEP_FINE}", id="speed-down-fine")
            yield Button(f"+ {SPEED_STEP_FINE}", id="speed-up-fine")
            yield Button(f"++ {SPEED_STEP_COARSE}", id="speed-up-coarse")
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
        validated_speed = self.validate_speed(speed)
        self.speed = round(validated_speed, 2)

    def watch_speed(self, speed: float):
        speed_input = self.query_one("#speed-input", Input)
        speed_input.value = f"{speed}"
        self.app.query_one(Status).speed = f"Speed: {speed} mm/s"

    @staticmethod
    def validate_speed(speed: float) -> int:
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
            yield Button(f"-- {DISTANCE_STEP_COARSE}", id="distance-down-coarse")
            yield Button(f"- {DISTANCE_STEP_FINE}", id="distance-down-fine")
            yield Button(f"+ {DISTANCE_STEP_FINE}", id="distance-up-fine")
            yield Button(f"++ {DISTANCE_STEP_COARSE}", id="distance-up-coarse")
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
    def submit_speed_input(self):
        distance_input = self.query_one("#distance-input", Input)
        distance = float(distance_input.value)
        self.set_distance(distance)

    def set_distance(self, distance: float):
        validated_distance = self.validate_distance(distance)
        self.distance = round(validated_distance, 1)

    def watch_distance(self, distance: float):
        distance_input = self.query_one("#distance-input", Input)
        distance_input.value = f"{distance}"
        self.app.query_one(Status).distance = f"Distance: {distance} mm"

    @staticmethod
    def validate_distance(distance: float) -> float:
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

class StatusAdvanced(Static):
    acceleration = reactive("Acceleration: ")

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(id="status-acceleration")

    def watch_acceleration(self, acceleration: str):
        self.query_one("#status-acceleration", Label).update(acceleration)

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


class AdvancedSettings(Static):
    acceleration = reactive(DEFAULT_ACCELERATION)

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label("Acceleration: ", id="acceleration-label")
            yield Input(
                value=f"{DEFAULT_ACCELERATION}",
                type="number",
                placeholder="Acceleration (mm/s^2)",
                id="acceleration-input",
                validate_on=["submitted"],
                validators=[Number(minimum=MIN_ACCELERATION, maximum=MAX_ACCELERATION)],
            )
            yield Label("mm/s^2", id="acceleration-unit")
        # TODO: set motor current?
        # TODO: toggle interpolation?
        # TODO: set logging level using Select widget?

    def _on_mount(self, event: events.Mount) -> None:
        self.app.query_one(StatusAdvanced).acceleration = f"Acceleration: {DEFAULT_ACCELERATION} mm/s^2"

    @on(Input.Submitted, "#acceleration-input")
    def submit_acceleration_input(self):
        acceleration_input = self.query_one("#acceleration-input", Input)
        acceleration = float(acceleration_input.value)
        self.acceleration = acceleration
        self.app.query_one(StatusAdvanced).acceleration = f"Acceleration: {acceleration} mm/s^2"

    def set_acceleration(self, acceleration: float):
        validated_acceleration = self.validate_acceleration(acceleration)
        self.acceleration = round(validated_acceleration, 1)

    @staticmethod
    def validate_acceleration(acceleration: float) -> float:
        if acceleration > MAX_ACCELERATION:
            acceleration = MAX_ACCELERATION
        elif acceleration < MIN_ACCELERATION:
            acceleration = MIN_ACCELERATION
        return acceleration


class Coder(Static):
    code = ""

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Enter your Coder API code below and press 'RUN code' to execute it.")
            yield TextArea(
                "print(\"Hello, World!\")",
                language="python",
                show_line_numbers=True,
                id="code-editor",
            )
            yield Button(
                "RUN code",
                id="run-code-btn",
            )

    def _on_mount(self, event: events.Mount) -> None:
        with open(Path(__file__).parent / "code_editor_init_content.py") as text:
            self.set_editor_text(text.read())

    @on(Button.Pressed, "#run-code-btn")
    async def run_code(self):
        self.code = self.app.query_one("#code-editor", TextArea).text
        tabbed_content = self.app.query_one("#tabbed-content", TabbedContent)
        tabbed_content.active = "main-tab"
        await asyncio.sleep(0.1)
        await self.exec_code_async()

    async def exec_code_async(self):
        log = self.app.query_one("#logger", RichLog)
        try:
            log.write("[blue]Executing code >>>>>>>>>>>>[/]")
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self.exec_code)
            log.write("[dark_cyan]>>>>>>>>>>>> Code finished.[/]")
        except Exception as e:
            log.write(f"Error executing code: {e}")

    def exec_code(self):
        exec(self.code)

    def set_editor_text(self, text: str):
        self.query_one("#code-editor", TextArea).text = text

    ''' ========== API for the code editor ========== '''

    def enable_motor(self):
        self.app.query_one(MotorControls).enable_motor_action()

    def disable_motor(self):
        self.app.query_one(MotorControls).disable_motor_action()

    def move_up(self, distance_mm: float, speed_mm_s: float, acceleration_mm_s2: float = None):
        # NOTE: We are purposely not changing the distance, speed and acceleration settings here,
        # as this may be undesirable in some cases.
        self.app.query_one(MotorControls).move_up(distance_mm, speed_mm_s, acceleration_mm_s2)

    def move_down(self, distance_mm: float, speed_mm_s: float, acceleration_mm_s2: float = None):
        # NOTE: We are purposely not changing the distance, speed and acceleration settings here,
        # as this may be undesirable in some cases.
        self.app.query_one(MotorControls).move_down(distance_mm, speed_mm_s, acceleration_mm_s2)

    def sleep(self, seconds: float):
        log = self.app.query_one("#logger", RichLog)
        log.write(f"[cyan]...Sleeping for {seconds} seconds...[/]")
        time.sleep(seconds)


class DipCoaterApp(App):
    """A Textual App to control a dip coater motor."""

    CSS_PATH = "tui.tcss"
    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("q", "request_quit", "Quit"),
        ("h", "show_help", "Help"),
    ]
    COMMANDS = App.COMMANDS | {HelpCommand}

    def __init__(self):
        super().__init__()
        self.motor_driver = TMC2209_MotorDriver(_loglevel=LOGGING_LEVEL)

    def on_mount(self):
        # on_mount() is called after compose(), so the RichLog is known
        log = self.query_one("#logger", RichLog)
        log.write("Motor has been initialised.")

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Footer()
        with TabbedContent(initial="main-tab", id="tabbed-content"):
            with TabPane("Main", id="main-tab"):
                with Horizontal():
                    with Vertical(id="left-side"):
                        yield StepMode(self.motor_driver)
                        yield SpeedControls()
                        yield DistanceControls()
                        yield MotorControls(self.motor_driver)
                        yield RichLog(markup=True, id="logger")
                    with Vertical(id="right-side"):
                        yield Status()
            with TabPane("Advanced", id="advanced-tab"):
                with Horizontal():
                    with Vertical(id="left-side-advanced"):
                        yield AdvancedSettings()
                        yield RichLog(markup=True, id="motor-logger")       # TODO: write motor logs to here
                    with Vertical(id="right-side-advanced"):
                        yield StatusAdvanced()
            with TabPane("Coder", id="coder-tab"):
                yield Coder()

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark

    def action_request_quit(self) -> None:
        self.motor_driver.cleanup()
        self.app.exit()

    def action_show_help(self):
        self.push_screen(HelpScreen())


def main():
    global LOGGING_LEVEL
    parser = argparse.ArgumentParser(description='Process logging level.')
    parser.add_argument('-l', '--log-level', type=str, default='ERROR',
                        choices=['NONE', 'ERROR', 'INFO', 'DEBUG', 'MOVEMENT', 'ALL'],
                        help='Set the logging level')
    args = parser.parse_args()

    # Convert string level to the appropriate value in your Loglevel enum
    LOGGING_LEVEL = getattr(Loglevel, args.log_level)

    app = DipCoaterApp()
    app.run()


if __name__ == '__main__':
    main()
