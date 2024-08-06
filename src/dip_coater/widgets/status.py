import asyncio

from textual.widgets import Static
from textual.reactive import reactive
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Label
from textual.widgets import Rule

from dip_coater.utils.threading_util import AsyncioStoppableTimer


class Status(Static):
    speed: reactive[float | None] = reactive(None)
    distance: reactive[float | None] = reactive(None)
    homing_found: reactive[bool | None] = reactive(None)
    limit_switch_up: reactive[bool | None] = reactive(None)
    limit_switch_down: reactive[bool | None] = reactive(None)
    motor_state: reactive[str | None] = reactive(None)
    position: reactive[float | None] = reactive(None)

    position_thread = None

    def __init__(self, app_state, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app_state = app_state

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(f"Driver type: [blue]{self.app_state.driver_type.name}[/]")
            yield Rule()
            yield Label(id="status-speed")
            yield Label(id="status-distance")
            yield Label(id="status-homing-found")
            yield Label(id="status-limit-switch-up")
            yield Label(id="status-limit-switch-down")
            yield Rule()
            yield Label(id="status-motor-state")
            yield Label(id="status-position")

    def _on_mount(self) -> None:
        self.speed = self.app_state.config.DEFAULT_SPEED
        self.distance = self.app_state.config.DEFAULT_DISTANCE
        self.homing_found = self.app_state.homing_found
        self.limit_switch_up = False
        self.limit_switch_down = False
        self.position = 0
        self.update_motor_state(self.app_state.motor_state)
        self.position_thread = AsyncioStoppableTimer(0.5, self.fetch_new_position)
        self.position_thread.start()

    def update_speed(self, speed: float):
        self.speed = speed

    def update_distance(self, distance: float):
        self.distance = distance

    def update_homing_found(self, homing_found: bool):
        self.homing_found = homing_found

    def update_limit_switch_up(self, limit_switch_up: bool):
        self.limit_switch_up = limit_switch_up

    def update_limit_switch_down(self, limit_switch_down: bool):
        self.limit_switch_down = limit_switch_down

    def update_motor_state(self, motor_state: str):
        self.motor_state = motor_state

    async def fetch_new_position(self):
        position = self.app_state.motor_driver.get_current_position_mm()
        await self.update_position(position)

    async def update_position(self, position_mm: float):
        self.position = position_mm

    def on_unmount(self):
        if self.position_thread is not None:
            self.position_thread.stop()

    # --------------- WATCHERS (called automatically when reactive has changed) ---------------

    def watch_speed(self, speed: str):
        if speed is None:
            return
        self.query_one("#status-speed", Label).update(f"Speed: {speed} mm/s")

    def watch_distance(self, distance: str):
        if distance is None:
            return
        self.query_one("#status-distance", Label).update(f"Distance: {distance:.1f} mm")
    
    def watch_homing_found(self, homing_found: str):
        if homing_found is None:
            return
        self.query_one("#status-homing-found", Label).update(f"Homing found: {homing_found}")

    def watch_limit_switch_up(self, limit_switch_up: str):
        if limit_switch_up is None:
            return
        str_limit_switch_up = "[dark_orange]Triggered[/]" if limit_switch_up else "Open"
        msg = f"Limit switch up: {str_limit_switch_up}"
        self.query_one("#status-limit-switch-up", Label).update(msg)
    
    def watch_limit_switch_down(self, limit_switch_down: str):
        if limit_switch_down is None:
            return
        str_limit_switch_down = "[dark_orange]Triggered[/]" if limit_switch_down else "Open"
        msg = f"Limit switch down: {str_limit_switch_down}"
        self.query_one("#status-limit-switch-down", Label).update(msg)

    def watch_motor_state(self, motor_state: str):
        if motor_state is None:
            motor_state = "UNKNOWN"
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
        self.query_one("#status-motor-state", Label).update(f"Motor state: [{color}]{motor_state.upper()}[/]")

    def watch_position(self, position: str):
        if position is None:
            msg = "Position: UNKNOWN (do homing first)"
        else:
            msg = f"Position: {position:.1f} mm"
        self.query_one("#status-position", Label).update(msg)
