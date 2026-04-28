from textual.widgets import Static
from textual.reactive import reactive
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Label
from textual.widgets import RichLog, Rule

from dip_coater.utils.threading_util import AsyncioStoppableTimer


MOTOR_STATE_COLORS = {
    "enabled": "green",
    "disabled": "red",
    "homing": "cyan",
    "moving": "blue",
}


def motor_state_badge(motor_state: str | None) -> str:
    state = motor_state or "unknown"
    color = MOTOR_STATE_COLORS.get(state, "red")
    return f"[{color}]{state.upper()}[/]"


def limit_switch_state_badge(triggered: bool) -> str:
    if triggered:
        return "[red]Triggered[/]"
    return "[green]Open[/]"


class Status(Static):
    speed: reactive[float | None] = reactive(None)
    distance: reactive[float | None] = reactive(None)
    homing_found: reactive[bool | None] = reactive(None)
    limit_switch_up: reactive[bool | None] = reactive(None)
    limit_switch_down: reactive[bool | None] = reactive(None)
    motor_state: reactive[str | None] = reactive(None)
    position: reactive[float | None] = reactive(None)
    status_error: reactive[str | None] = reactive(None)

    position_thread = None

    def __init__(self, app_state, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app_state = app_state
        self._last_polling_error: str | None = None

    def _driver_label(self) -> str:
        driver_label = self.app_state.driver_type.name
        if getattr(self.app_state.motor_driver, "is_dummy", False):
            driver_label += " (dummy)"
        return driver_label

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(f"Driver type: [blue]{self._driver_label()}[/]")
            yield Label(f"Setup: [blue]{self.app_state.setup_profile.label}[/]")
            yield Label(id="status-state-strip", classes="state-strip")
            yield Rule()
            yield Label(id="status-speed")
            yield Label(id="status-distance")
            yield Label(id="status-homing-found")
            yield Label(id="status-limit-switch-up")
            yield Label(id="status-limit-switch-down")
            yield Rule()
            yield Label(id="status-position")
            yield Label(id="status-error")

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
        try:
            self.fetch_limit_switches()
        except Exception as error:
            self.record_polling_error(error)
            return
        if self.app_state.motor_state in ("moving", "homing"):
            self.clear_polling_error()
            return
        try:
            position = self.app_state.motion_controller.get_current_position_mm()
        except Exception as error:
            self.record_polling_error(error)
            return
        self.clear_polling_error()
        await self.update_position(position)

    def fetch_limit_switches(self):
        controller = self.app_state.motion_controller
        if not controller.supports_limit_switches:
            return
        from dip_coater.setup_profiles.machine_profile import HomeDirection

        self.update_limit_switch_up(controller.read_limit_switch(HomeDirection.UP))
        self.update_limit_switch_down(controller.read_limit_switch(HomeDirection.DOWN))
        motor_controls = getattr(self.app_state, "motor_controls", None)
        if motor_controls is not None:
            motor_controls.update_status_widgets()

    async def update_position(self, position_mm: float):
        self.position = position_mm

    def record_polling_error(self, error: Exception):
        message = f"Status polling failed: {error}"
        self.status_error = message
        self.app_state.motor_state = "fault"
        if self.is_mounted:
            self.update_motor_state("fault")
        motor_controls = getattr(self.app_state, "motor_controls", None)
        if motor_controls is not None:
            motor_controls.update_status_widgets()
        if message == self._last_polling_error:
            return
        self._last_polling_error = message
        try:
            self.app.query_one("#logger", RichLog).write(f"[red]{message}[/]")
        except Exception:
            pass

    def clear_polling_error(self):
        if self.status_error is None:
            return
        self.status_error = None
        self._last_polling_error = None

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
        homing_status = "yes" if homing_found else "no"
        self.query_one("#status-homing-found", Label).update(
            f"Homed: {homing_status}"
        )

    def watch_limit_switch_up(self, limit_switch_up: str):
        if limit_switch_up is None:
            return
        str_limit_switch_up = limit_switch_state_badge(limit_switch_up)
        msg = f"Limit switch up: {str_limit_switch_up}"
        self.query_one("#status-limit-switch-up", Label).update(msg)

    def watch_limit_switch_down(self, limit_switch_down: str):
        if limit_switch_down is None:
            return
        str_limit_switch_down = limit_switch_state_badge(limit_switch_down)
        msg = f"Limit switch down: {str_limit_switch_down}"
        self.query_one("#status-limit-switch-down", Label).update(msg)

    def watch_motor_state(self, motor_state: str):
        badge = motor_state_badge(motor_state)
        self.query_one("#status-state-strip", Label).update(f"State: {badge}")

    def watch_position(self, position: str):
        if position is None:
            msg = "Position: UNKNOWN (do homing first)"
        else:
            msg = f"Position: {position:.1f} mm"
        self.query_one("#status-position", Label).update(msg)

    def watch_status_error(self, status_error: str | None):
        if not self.is_mounted:
            return
        if status_error is None:
            msg = ""
        else:
            msg = f"[red]{status_error}[/]"
        self.query_one("#status-error", Label).update(msg)
