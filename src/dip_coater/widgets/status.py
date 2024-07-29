import asyncio

from textual.widgets import Static
from textual.reactive import reactive
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Label
from textual.widgets import Rule

from dip_coater.motor.tmc2209 import TMC2209_MotorDriver
from dip_coater.app_state import app_state
from dip_coater.utils.threading_util import AsyncioStoppableTimer


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
        self.update_motor_state(app_state.motor_state)
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
        position = app_state.motor_driver.get_current_position()
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
