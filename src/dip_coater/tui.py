import logging
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
from textual.widgets import Markdown
from textual.widgets import RadioButton
from textual.widgets import RadioSet
from textual.widgets import RichLog
from textual.widgets import Static
from textual.widgets import TabPane
from textual.widgets import TabbedContent
from textual.widgets import TextArea
from textual.widgets import Collapsible
from textual.widgets import Checkbox
from textual.widgets import Select
from textual.widgets import Rule
from textual.validation import Number, Function
from textual.binding import Binding
from importlib.metadata import version

import argparse
import asyncio
import logging
import json

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

from RPi import GPIO
from TMC_2209._TMC_2209_logger import Loglevel
from TMC_2209._TMC_2209_move import MovementAbsRel, StopMode
from dip_coater.motor import TMC2209_MotorDriver
from dip_coater.threading_util import StoppableThreadTimer, AsyncioStoppableTimer

# Logging settings
STEP_MODE_WRITE_TO_LOG = False
DEFAULT_LOGGING_LEVEL = Loglevel.INFO  # NONE, ERROR, INFO, DEBUG, MOVEMENT, ALL

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
MAX_DISTANCE = 100
MIN_DISTANCE = 0

# Position settings (mm)
DEFAULT_POSITION = 10
POSITION_STEP_COARSE = 5
POSITION_STEP_FINE = 1
MAX_POSITION = 100
MIN_POSITION = 0

# Acceleration settings (mm/s^2)
DEFAULT_ACCELERATION = 30
MIN_ACCELERATION = 0.5
MAX_ACCELERATION = 50

# Step mode settings
STEP_MODES = {
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
STEP_MODE_LABELS = {
    "I1": "1",
    "I2": "1/2",
    "I4": "1/4",
    "I8": "1/8",
    "I16": "1/16",
    "I32": "1/32",
    "I64": "1/64",
    "I128": "1/128",
    "I256": "1/256",
}
DEFAULT_STEP_MODE = "I8"

# Current settings (in mA)
DEFAULT_CURRENT = 1500
MIN_CURRENT = 31    # Minimum current that can be sensed by the TMC2209
MAX_CURRENT = 2000  # Absolute max limit for TMC2209!

# Limit switch settings
LIMIT_SWITCH_UP_PIN = 19
LIMIT_SWITCH_UP_NC = True       # Normally closed (NC) or normally open (NO)
LIMIT_SWITCH_DOWN_PIN = 26
LIMIT_SWITCH_DOWN_NC = True     # Normally closed (NC) or normally open (NO)

# Homing settings
#HOMING_REVOLUTIONS = 25
HOMING_REVOLUTIONS = 5  # For testing
HOMING_MAX_DISTANCE = 100   # mm
HOMING_MIN_REVOLUTIONS = 1
HOMING_MAX_REVOLUTIONS = 100
HOMING_THRESHOLD = 100
HOMING_MIN_THRESHOLD = 1
HOMING_MAX_THRESHOLD = 255
HOMING_SPEED_MM_S = 2
HOMING_MIN_SPEED = 0.2
HOMING_MAX_SPEED = 5
HOME_UP = True      # Home the motor upwards (True) or downwards (False)

# Other motor settings
INVERT_MOTOR_DIRECTION = False
USE_SPREAD_CYCLE = False
USE_INTERPOLATION = True

# Application config file
CONFIG_FILE = "dip_coater_config.json"


class StepMode(Static):
    def __init__(self, motor_driver: TMC2209_MotorDriver):
        super().__init__()
        self.step_mode = STEP_MODES[DEFAULT_STEP_MODE]
        self.motor_driver = motor_driver
        self.motor_driver.set_stepmode(self.step_mode)

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Step Mode")
            with RadioSet(id="step-mode"):
                for mode, label in STEP_MODE_LABELS.items():
                    yield RadioButton(label, id=mode)

    def on_mount(self):
        self.query_one(f"#{DEFAULT_STEP_MODE}", RadioButton).value = True

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        step_mode = STEP_MODES[event.pressed.id]
        self.set_stepmode(step_mode, event.pressed.label)

    def set_stepmode(self, stepmode: int, step_mode_label):
        self.step_mode = stepmode
        self.motor_driver.set_stepmode(self.step_mode)
        if STEP_MODE_WRITE_TO_LOG:
            log = self.app.query_one("#logger", RichLog)
            log.write(f"StepMode set to {step_mode_label} µsteps.")
        self.app.query_one(StatusAdvanced).step_mode = f"Step Mode: {step_mode_label} µsteps"


class MotorControls(Static):
    def __init__(self, motor_driver: TMC2209_MotorDriver):
        super().__init__()
        self._motor_state: str = "disabled"
        self.homing_found = False
        self.motor_driver = motor_driver

    def compose(self) -> ComposeResult:
        yield Button("Move UP ↑", id="move-up", variant="primary")
        yield Button("Move DOWN ↓", id="move-down", variant="primary")
        yield Button("ENABLE motor", id="enable-motor", variant="success")
        yield Button("DISABLE motor", id="disable-motor", variant="error")
        yield Button("Do HOMING", id="do-homing")
        yield Button("STOP moving", id="stop-moving", variant="error")

    def _on_mount(self, event: events.Mount) -> None:
        self.app.query_one(Status).update_homing_found(self.homing_found)
        self.setup_limit_switches_io()
        self.update_limit_switch_up_status(LIMIT_SWITCH_UP_PIN)
        self.update_limit_switch_down_status(LIMIT_SWITCH_DOWN_PIN)

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

    def set_motor_state(self, state: str):
        self._motor_state = state
        self.app.query_one(Status).update_motor_state(self._motor_state)

    @on(Button.Pressed, "#move-up")
    async def move_up_action(self):
        distance_mm, speed_mm_s, accel_mm_s2, step_mode = self.get_parameters()
        await self.move_up(distance_mm, speed_mm_s, accel_mm_s2)

    async def move_up(self, distance_mm: float, speed_mm_s: float, acceleration_mm_s2: float = None):
        log = self.app.query_one("#logger", RichLog)
        if self._motor_state == "enabled":
            def_dist, def_speed, def_accel, step_mode = self.get_parameters()
            if acceleration_mm_s2 is None:
                acceleration_mm_s2 = def_accel
            log.write(
                f"Moving up ({distance_mm=} mm, {speed_mm_s=} mm/s, {acceleration_mm_s2=} mm/s\u00b2, {step_mode=} µs).")
            self.set_motor_state("moving")
            await asyncio.sleep(0.1)
            try:
                self.motor_driver.move_up(distance_mm, speed_mm_s, acceleration_mm_s2, [LIMIT_SWITCH_UP_PIN])
                stop = await self.motor_driver.wait_for_motor_done_async()
                if stop == StopMode.NO:
                    log.write(f"-> Finished moving up.")
                else:
                    log.write(f"[red]-> Stopped moving up {stop}.[/]")
                self.set_motor_state("enabled")
            except ValueError as e:
                log.write(f"[red]{e}[/]")
                self.set_motor_state("enabled")
        else:
            log.write("[red]We cannot move up when the motor is disabled[/]")

    @on(Button.Pressed, "#move-down")
    async def move_down_action(self):
        distance_mm, speed_mm_s, accel_mm_s2, step_mode = self.get_parameters()
        await self.move_down(distance_mm, speed_mm_s, accel_mm_s2)

    async def move_down(self, distance_mm: float, speed_mm_s: float, acceleration_mm_s2: float = None):
        log = self.app.query_one("#logger", RichLog)
        if self._motor_state == "enabled":
            def_dist, def_speed, def_accel, step_mode = self.get_parameters()
            if acceleration_mm_s2 is None:
                acceleration_mm_s2 = def_accel
            log.write(
                f"Moving down ({distance_mm=} mm, {speed_mm_s=} mm/s, {acceleration_mm_s2=} mm/s\u00b2, {step_mode=} µs).")
            self.set_motor_state("moving")
            await asyncio.sleep(0.1)
            try:
                self.motor_driver.move_down(distance_mm, speed_mm_s, acceleration_mm_s2, [LIMIT_SWITCH_DOWN_PIN])
                stop = await self.motor_driver.wait_for_motor_done_async()
                if stop == StopMode.NO:
                    log.write(f"-> Finished moving down.")
                else:
                    log.write(f"[red]-> Stopped moving down {stop}.[/]")
                self.set_motor_state("enabled")
            except ValueError as e:
                log.write(f"[red]{e}[/]")
                self.set_motor_state("enabled")
        else:
            log.write("[red]We cannot move down when the motor is disabled[/]")

    @on(Button.Pressed, "#enable-motor")
    async def enable_motor_action(self):
        log = self.app.query_one("#logger", RichLog)
        if self._motor_state == "disabled":
            self.motor_driver.enable_motor()
            self.bind_limit_switches_to_motor()
            self.set_motor_state("enabled")
            log.write(f"[green]Motor is now enabled.[/]")

    @on(Button.Pressed, "#disable-motor")
    async def disable_motor_action(self):
        log = self.app.query_one("#logger", RichLog)
        if self._motor_state == "homing":
            log.write("[red]We cannot disable the motor while homing is in progress[/]")
            return
        elif self._motor_state == "moving":
            log.write("[red]We cannot disable the motor while homing is moving[/]")
            return
        elif self._motor_state == "enabled":
            self.motor_driver.disable_motor()
            self.set_motor_state("disabled")
            log.write(f"[dark_orange]Motor is now disabled.[/]")

    @on(Button.Pressed, "#do-homing")
    async def do_homing_action(self):
        if self._motor_state == "enabled":
            await self.perform_homing()
        elif self._motor_state == "homing":
            # Do nothing when already homing
            return
        else:
            log = self.app.query_one("#logger", RichLog)
            log.write("[red]We cannot do homing when the motor is disabled[/]")

    @on(Button.Pressed, "#stop-moving")
    async def stop_moving_action(self):
        log = self.app.query_one("#logger", RichLog)
        if self._motor_state == "moving":
            self.motor_driver.stop_motor()
            log.write("[dark_orange]Motor movement stopped.[/]")
        else:
            log.write("[red]No movement to stop[/]")

    async def perform_homing(self, home_up: bool = HOME_UP):
        log = self.app.query_one("#logger", RichLog)
        speed = self.app.query_one(AdvancedSettings).homing_speed

        log.write(f"[cyan]Starting limit switch homing ({speed=} mm/s)...[/]")
        self.set_motor_state("homing")
        await asyncio.sleep(0.1)
        try:
            distance = HOMING_MAX_DISTANCE if home_up else -HOMING_MAX_DISTANCE
            homing_found = self.motor_driver.do_limit_switch_homing(LIMIT_SWITCH_UP_PIN, LIMIT_SWITCH_DOWN_PIN,
                                                                    distance, speed)
            if homing_found:
                log.write("-> Finished homing.")
            else:
                log.write("[red]Homing failed[/]")
            self.set_homing_found(homing_found)
        except ValueError as e:
            log.write(f"[red]{e}[/]")
        finally:
            self.setup_limit_switches_io()  # Re-bind the limit switches after homing
        self.set_motor_state("enabled")
        self.bind_limit_switches_to_motor()  # Re-bind the limit switches after homing

    def set_homing_found(self, homing_found: bool):
        self.homing_found = homing_found
        self.app.query_one(Status).update_homing_found(self.homing_found)
        self.app.query_one(PositionControls).update_button_states(homing_found)

    def setup_limit_switches_io(self):
        self._setup_limit_switch_io(LIMIT_SWITCH_UP_PIN, LIMIT_SWITCH_UP_NC)
        GPIO.add_event_callback(LIMIT_SWITCH_UP_PIN, self.update_limit_switch_up_status)
        self._setup_limit_switch_io(LIMIT_SWITCH_DOWN_PIN, LIMIT_SWITCH_DOWN_NC)
        GPIO.add_event_callback(LIMIT_SWITCH_DOWN_PIN, self.update_limit_switch_down_status)

    @staticmethod
    def _setup_limit_switch_io(limit_switch_pin, limit_switch_nc=True, bouncetime=5):
        GPIO.setup(limit_switch_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.remove_event_detect(limit_switch_pin)
        GPIO.add_event_detect(limit_switch_pin, GPIO.BOTH, bouncetime=bouncetime)

    def update_limit_switch_up_status(self, pin_number):
        triggered = GPIO.input(pin_number) == 1 if LIMIT_SWITCH_UP_NC else GPIO.input(pin_number) == 0
        self.app.query_one(Status).update_limit_switch_up(triggered)

    def update_limit_switch_down_status(self, pin_number):
        triggered = GPIO.input(pin_number) == 1 if LIMIT_SWITCH_DOWN_NC else GPIO.input(pin_number) == 0
        self.app.query_one(Status).update_limit_switch_down(triggered)

    def bind_limit_switches_to_motor(self):
        """ Bind the limit switches to stop the motor driver."""
        self.motor_driver.bind_limit_switch(LIMIT_SWITCH_UP_PIN, NC=LIMIT_SWITCH_UP_NC)
        self.motor_driver.bind_limit_switch(LIMIT_SWITCH_DOWN_PIN, NC=LIMIT_SWITCH_DOWN_NC)


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


class DistanceControls(Static):
    distance = reactive(DEFAULT_DISTANCE)

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
        self.app.query_one(Status).update_distance(distance)


class PositionControls(Static):
    position = reactive("0")

    def __init__(self, motor_driver: TMC2209_MotorDriver):
        super().__init__()
        self.motor_driver = motor_driver

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label("Position: ", id="position-label")
            yield Button(f"-- {DISTANCE_STEP_COARSE}", id="position-down-coarse", classes="btn-position-control btn-position")
            yield Button(f"- {DISTANCE_STEP_FINE}", id="position-down-fine", classes="btn-position-control btn-position")
            yield Button(f"+ {DISTANCE_STEP_FINE}", id="position-up-fine", classes="btn-position-control btn-position")
            yield Button(f"++ {DISTANCE_STEP_COARSE}", id="position-up-coarse", classes="btn-position-control btn-position")
            yield Button("Set to current position", id="set-to-current-pos-btn", classes="btn-position")
            yield Input(
                value="0",
                type="number",
                placeholder="Position (mm)",
                id="position-input",
                validate_on=["submitted"],
                validators=[Number(minimum=0, maximum=250)],
            )
            yield Label("mm", id="position-unit")
            yield Button("Move to position", id="move-to-position-btn", variant="primary", classes="btn-position")

    def _on_mount(self, event: events.Mount) -> None:
        self.update_button_states(self.motor_driver.is_homing_found())

    @on(Button.Pressed, "#position-down-coarse")
    def decrease_position_coarse(self):
        new_position = self.position - POSITION_STEP_COARSE
        self.set_position(new_position)

    @on(Button.Pressed, "#position-down-fine")
    def decrease_distance_fine(self):
        new_position = self.position - POSITION_STEP_FINE
        self.set_position(new_position)

    @on(Button.Pressed, "#position-up-fine")
    def increase_position_fine(self):
        new_position = self.position + POSITION_STEP_FINE
        self.set_position(new_position)

    @on(Button.Pressed, "#position-up-coarse")
    def increase_position_coarse(self):
        new_position = self.position + POSITION_STEP_COARSE
        self.set_position(new_position)

    @on(Button.Pressed, "#set-to-current-pos-btn")
    def set_to_current_position(self):
        pos = self.motor_driver.get_current_position()
        if pos is not None:
            self.set_position(pos)

    @on(Button.Pressed, "#move-to-position-btn")
    async def move_to_position_action(self):
        pos = float(self.position)
        speed = self.app.query_one(SpeedControls).speed
        accel = self.app.query_one(AdvancedSettings).acceleration
        await self.move_to_position(pos, speed, accel)

    async def move_to_position(self, position_mm: float, speed_mm_s: float = None, acceleration_mm_s2: float = None,
                               home_up: bool = HOME_UP):
        self.motor_driver.run_to_position(position_mm, speed_mm_s, acceleration_mm_s2, home_up)

    def set_position(self, position: float):
        validated_position = clamp(position, MIN_POSITION, MAX_POSITION)
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


class Status(Static):
    speed = reactive("Speed: ")
    distance = reactive("Distance: ")
    homing_found = reactive("Homing found: ")
    limit_switch_up = reactive("Limit switch up: ")
    limit_switch_down = reactive("Limit switch down: ")
    motor = reactive("Motor: ")
    position = reactive("Position: ")

    position_thread = None

    def __init__(self, motor_driver: TMC2209_MotorDriver, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.motor_driver = motor_driver

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(id="status-speed")
            yield Label(id="status-distance")
            yield Label(id="status-homing-found")
            yield Label(id="status-limit-switch-up")
            yield Label(id="status-limit-switch-down")
            yield Rule()
            yield Label(id="status-motor")
            yield Label(id="status-position")

    def on_mount(self):
        motor_state = self.app.query_one(MotorControls).motor_state
        self.update_motor_state(motor_state)
        self.position_thread = AsyncioStoppableTimer(0.5, self.fetch_new_position)
        self.position_thread.start()

    def watch_speed(self, speed: str):
        self.query_one("#status-speed", Label).update(speed)

    def update_speed(self, speed: float):
        self.speed = f"Speed: {speed} mm/s"

    def watch_distance(self, distance: str):
        self.query_one("#status-distance", Label).update(distance)

    def update_distance(self, distance: float):
        self.distance = f"Distance: {distance} mm"

    def watch_homing_found(self, homing_found: str):
        self.query_one("#status-homing-found", Label).update(homing_found)

    def update_homing_found(self, homing_finished: bool):
        self.homing_found = f"Homing found: {homing_finished}"

    def watch_limit_switch_up(self, limit_switch_up: str):
        self.query_one("#status-limit-switch-up", Label).update(limit_switch_up)

    def update_limit_switch_up(self, limit_switch_up: bool):
        str_limit_switch_up = "[dark_orange]Triggered[/]" if limit_switch_up else "Open"
        self.limit_switch_up = f"Limit switch up: {str_limit_switch_up}"

    def watch_limit_switch_down(self, limit_switch_down: str):
        self.query_one("#status-limit-switch-down", Label).update(limit_switch_down)

    def update_limit_switch_down(self, limit_switch_down: bool):
        str_limit_switch_down = "[dark_orange]Triggered[/]" if limit_switch_down else "Open"
        self.limit_switch_down = f"Limit switch down: {str_limit_switch_down}"

    def watch_motor(self, motor: str):
        self.query_one("#status-motor", Label).update(motor)

    def update_motor_state(self, motor_state: str):
        if motor_state == "enabled":
            color = "green"
        elif motor_state == "disabled":
            color = "dark_orange"
        elif motor_state == "homing":
            color = "cyan"
        elif motor_state == "moving":
            color = "blue"
        else:
            color = "red"
        self.motor = f"Motor: [{color}]{motor_state.upper()}[/]"

    def watch_position(self, position: str):
        self.query_one("#status-position", Label).update(position)

    async def fetch_new_position(self):
        position = self.motor_driver.get_current_position()
        await self.update_position(position)

    async def update_position(self, position_mm: float):
        if position_mm is None:
            self.position = "Position: UNKNOWN (do homing first)"
        else:
            self.position = f"Position: {position_mm} mm"
        await asyncio.sleep(0.1)

    def on_unmount(self):
        if self.position_thread is not None:
            self.position_thread.stop()


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

            yield Rule(classes="rule")

            with Horizontal():
                yield Label("Logging level: ", id="logging-level-label")
                options = self.create_log_level_options()
                yield Select(options,
                             value=DEFAULT_LOGGING_LEVEL.value,
                             allow_blank=False,
                             name="Select logging level",
                             id="logging-level-select")

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

        self.query_one("#logging-level-select", Select).value = DEFAULT_LOGGING_LEVEL.value

    @staticmethod
    def create_log_level_options() -> list:
        options = []
        for level in Loglevel:
            options.append((level.name, level.value))
        return options

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

    @on(Select.Changed, "#logging-level-select")
    def action_set_loglevel(self, event: Select.Changed):
        level = Loglevel(event.value)
        self.set_loglevel(level)

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

    def set_loglevel(self, level: Loglevel):
        self.motor_driver.set_loglevel(level)


class Coder(Static):
    code = ""

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Enter your Coder API code below and press 'RUN code' to execute it.")
            with Collapsible(title="View Coder API", collapsed=True, id="coder-api-collapsible"):
                with open(Path(__file__).parent / "coder_API.md") as text:
                    md = Markdown(
                        text.read(),
                        id="coder-api-markdown",
                    )
                    md.code_dark_theme = "monokai"
                    yield md
            yield TextArea(
                "print(\"Hello, World!\")",
                language="python",
                show_line_numbers=True,
                id="code-editor",
            )
            with Horizontal(id="run-and-load-code-container"):
                yield Button(
                    "RUN code",
                    id="run-code-btn",
                    variant="success",
                )
                yield Button(
                    "LOAD code from file",
                    id="load-code-btn",
                )
                with Vertical(id="coder-path-input-container"):
                    yield Input(
                        value="<dummy input>",
                        type="text",
                        placeholder="Input file path to python code, or empty for default code",
                        id="code-file-path-input",
                        validate_on=["changed"],
                        validators=[Function(self.is_file_path_valid_python,
                                             "File path does not point to valid Python (.py) file")],
                    )
                    yield Label("", id="coder-path-invalid-reasons")

    def _on_mount(self, event: events.Mount) -> None:
        config_file_path = config_load_coder_filepath()
        self.query_one("#code-file-path-input", Input).value = config_file_path
        self.load_code_from_file(config_file_path)

    @on(Button.Pressed, "#run-code-btn")
    async def run_code(self):
        self.code = self.app.query_one("#code-editor", TextArea).text
        tabbed_content = self.app.query_one("#tabbed-content", TabbedContent)
        tabbed_content.active = "main-tab"
        await asyncio.sleep(0.1)
        await self.exec_code_async()

    def set_editor_text(self, text: str):
        self.query_one("#code-editor", TextArea).text = text

    @on(Input.Changed)
    def show_invalid_reasons(self, event: Input.Changed) -> None:
        # Updating the UI to show the reasons why validation failed
        if not event.validation_result.is_valid:
            (self.query_one("#coder-path-invalid-reasons", Label)
                .update(f"[red]{event.validation_result.failure_descriptions}[/]"))
        else:
            (self.query_one("#coder-path-invalid-reasons", Label)
                .update("[green]Valid file path[/]"))

    @staticmethod
    def is_file_path_valid_python(file_path: str) -> bool:
        # Default code is allowed
        if file_path is None or file_path == "":
            return True
        return Path(file_path).suffix == ".py"

    @on(Input.Submitted, "#code-file-path-input")
    @on(Button.Pressed, "#load-code-btn")
    def submit_speed_input(self):
        file_path_input = self.query_one("#code-file-path-input", Input)
        file_path = file_path_input.value

        if not self.is_file_path_valid_python(file_path):
            return

        self.load_code_from_file(file_path)
        config_save_coder_filepath(file_path)

    def load_code_from_file(self, file_path: str):
        if file_path is None or file_path == "":
            self.load_default_code()
        else:
            self.load_code_into_editor(file_path)

    def load_code_into_editor(self, file_path):
        with open(file_path) as text:
            self.set_editor_text(text.read())

    def load_default_code(self):
        file_path = Path(__file__).parent / "code_editor_init_content.py"
        self.load_code_into_editor(file_path)

    async def exec_code_async(self):
        log = self.app.query_one("#logger", RichLog)
        try:
            log.write("[blue]Executing code >>>>>>>>>>>>[/]")
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self.exec_code)
            log.write("[dark_cyan]>>>>>>>>>>>> Code finished.[/]")
        except Exception as e:
            log.write(f"[red]Error executing code: {e}[/]")
            raise e

    def exec_code(self):
        exec(self.code)

    @staticmethod
    def async_run(func, *args):
        async def run():
            await func(*args)
        asyncio.run(run())

    ''' ========== API for the code editor ========== '''

    def enable_motor(self):
        self.async_run(self.app.query_one(MotorControls).enable_motor_action)

    def disable_motor(self):
        self.async_run(self.app.query_one(MotorControls).disable_motor_action)

    def move_up(self, distance_mm: float, speed_mm_s: float, acceleration_mm_s2: float = None):
        # NOTE: We are purposely not changing the distance, speed and acceleration settings here,
        # as this may be undesirable in some cases.
        self.async_run(self.app.query_one(MotorControls).move_up, distance_mm, speed_mm_s, acceleration_mm_s2)

    def move_down(self, distance_mm: float, speed_mm_s: float, acceleration_mm_s2: float = None):
        # NOTE: We are purposely not changing the distance, speed and acceleration settings here,
        # as this may be undesirable in some cases.
        self.async_run(self.app.query_one(MotorControls).move_down, distance_mm, speed_mm_s, acceleration_mm_s2)

    def home_motor(self, home_up: bool = HOME_UP):
        self.async_run(self.app.query_one(MotorControls).perform_homing, home_up)

    def move_to_position(self, position_mm: float, speed_mm_s: float, acceleration_mm_s2: float = None,
                         home_up: bool = HOME_UP):
        self.async_run(self.app.query_one(PositionControls).move_to_position, position_mm, speed_mm_s,
                       acceleration_mm_s2, home_up)

    def sleep(self, seconds: float):
        log = self.app.query_one("#logger", RichLog)
        log.write(f"[cyan]...Sleeping for {seconds} seconds...[/]")
        self.async_run(asyncio.sleep, seconds)


class MotorLoggerHandler(logging.Handler):
    def __init__(self, logger_widget: RichLog) -> None:
        super().__init__()
        self.logger_widget = logger_widget

    def emit(self, record) -> None:
        self.logger_widget.write(self.colorize(record))

    def colorize(self, record):
        message = self.format(record)
        if record.levelno == Loglevel.ERROR.value:
            return f"[red]{message}[/]"
        elif record.levelno == Loglevel.WARNING.value:
            return f"[dark_orange]{message}[/]"
        elif record.levelno == Loglevel.MOVEMENT.value:
            return f"[cyan]{message}[/]"
        return message


class DipCoaterApp(App):
    """A Textual App to control a dip coater motor."""

    CSS_PATH = "tui.tcss"
    BINDINGS = [
        Binding("t", "toggle_dark", "Toggle dark mode"),
        Binding("q", "request_quit", "Quit"),
        Binding("h", "show_help", "Help"),
        Binding("w", "move_up", "Move up", show=False),
        Binding("s", "move_down", "Move down", show=False),
        Binding("a", "enable_motor", "Enable the motor", show=False),
        Binding("d", "disable_motor", "Disable the motor", show=False),
    ]
    COMMANDS = App.COMMANDS | {HelpCommand}

    def __init__(self):
        super().__init__()
        self.motor_logger_widget = RichLog(markup=True, id="motor-logger")
        motor_logger_handler = MotorLoggerHandler(self.motor_logger_widget)
        logging_format = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", "%Y%m%d %H:%M:%S")
        self.motor_driver = TMC2209_MotorDriver(stepmode=STEP_MODES[DEFAULT_STEP_MODE],
                                                current=DEFAULT_CURRENT,
                                                invert_direction=INVERT_MOTOR_DIRECTION,
                                                interpolation=USE_INTERPOLATION,
                                                spread_cycle=USE_SPREAD_CYCLE,
                                                loglevel=DEFAULT_LOGGING_LEVEL,
                                                log_handlers=[motor_logger_handler],
                                                log_formatter=logging_format)

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
                        yield SpeedControls()
                        yield DistanceControls()
                        yield PositionControls(self.motor_driver)
                        yield MotorControls(self.motor_driver)
                        yield RichLog(markup=True, id="logger")
                    with Vertical(id="right-side"):
                        yield Status(self.motor_driver, id="status")
            with TabPane("Advanced", id="advanced-tab"):
                with Horizontal():
                    with Vertical(id="left-side-advanced"):
                        yield AdvancedSettings(self.motor_driver)
                        yield self.motor_logger_widget
                    with Vertical(id="right-side-advanced"):
                        yield StatusAdvanced(id="status-advanced")
                        yield Button("Reset to defaults", id="reset-to-defaults-btn", variant="error")
            with TabPane("Coder", id="coder-tab"):
                yield Coder()

    @on(Button.Pressed, "#reset-to-defaults-btn")
    def reset_to_defaults(self):
        self.query_one(AdvancedSettings).reset_settings_to_default()

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark

    def action_request_quit(self) -> None:
        self.motor_driver.cleanup()
        self.app.exit()

    def action_show_help(self) -> None:
        self.push_screen(HelpScreen())

    async def action_move_up(self) -> None:
        await self.query_one(MotorControls).move_up_action()

    async def action_move_down(self) -> None:
        await self.query_one(MotorControls).move_down_action()

    async def action_enable_motor(self) -> None:
        await self.query_one(MotorControls).enable_motor_action()

    async def action_disable_motor(self) -> None:
        await self.query_one(MotorControls).disable_motor_action()


""" Utility functions """


def clamp(value, min_value, max_value):
    """Clamp a value between a minimum and maximum value."""
    return max(min(value, max_value), min_value)


def config_save_coder_filepath(filepath: str):
    data = {'coder_filepath': filepath}
    with open(CONFIG_FILE, "w") as file:
        json.dump(data, file)


def config_load_coder_filepath():
    try:
        with open(CONFIG_FILE, "r") as file:
            data = json.load(file)
            return data.get('coder_filepath')
    except FileNotFoundError:
        return ""
    except json.JSONDecodeError:        # JSON file is empty or corrupted
        return ""


def main():
    global DEFAULT_LOGGING_LEVEL
    parser = argparse.ArgumentParser(description='Process logging level.')
    parser.add_argument('-l', '--log-level', type=str, default=DEFAULT_LOGGING_LEVEL.name,
                        choices=['NONE', 'ERROR', 'INFO', 'DEBUG', 'MOVEMENT', 'ALL'],
                        help='Set the logging level')
    args = parser.parse_args()

    # Convert string level to the appropriate value in your Loglevel enum
    DEFAULT_LOGGING_LEVEL = getattr(Loglevel, args.log_level)

    app = DipCoaterApp()
    package_version = version("dip-coater")
    app.title = f"Dip Coater v{package_version}"
    app.run()


if __name__ == '__main__':
    main()
