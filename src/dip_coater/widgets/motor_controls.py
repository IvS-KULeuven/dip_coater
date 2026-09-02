import asyncio

from textual.widgets import Button, RichLog, Static
from textual.app import ComposeResult
from textual import on, events

from dip_coater.widgets.position_controls import PositionControls
from dip_coater.setup_profiles.machine_profile import HomeDirection


def is_normal_motor_stop(stop) -> bool:
    return stop is None or getattr(stop, "name", None) == "NO"


def control_button_disabled_states(
    *,
    motor_state: str,
    limit_switch_up: bool | None,
    limit_switch_down: bool | None,
    supports_limit_switches: bool,
    supports_homing: bool,
) -> dict[str, bool]:
    motor_enabled = motor_state == "enabled"
    up_switch_open = not supports_limit_switches or limit_switch_up is False
    down_switch_open = not supports_limit_switches or limit_switch_down is False
    return {
        "move-up": not (motor_enabled and up_switch_open),
        "move-down": not (motor_enabled and down_switch_open),
        "enable-motor": motor_state != "disabled",
        "disable-motor": motor_state not in ("enabled", "moving", "homing", "fault"),
        "do-homing": not (supports_homing and motor_enabled),
    }


class MotorControls(Static):
    def __init__(self, app_state):
        super().__init__()
        self.app_state = app_state
        self.app_state.homing_found = False
        self._homing_task: asyncio.Task | None = None
        self._motion_action_task: asyncio.Task | None = None
        self._motion_wait_task: asyncio.Task | None = None

    def compose(self) -> ComposeResult:
        yield Button("Move up ↑", id="move-up", variant="primary")
        yield Button("Move down ↓", id="move-down", variant="primary")
        yield Button("Enable motor", id="enable-motor", variant="success")
        yield Button("Stop and disable", id="disable-motor", variant="error")
        if self.app_state.motion_controller.supports_homing:
            yield Button("Home", id="do-homing")
        # yield Button("STOP moving", id="stop-moving", variant="error")         Doesn't work currently...

    def _on_mount(self, event: events.Mount) -> None:
        self.update_status_widgets()
        if self.app_state.motion_controller.supports_limit_switches:
            self.setup_limit_switches_io()
            self.bind_limit_switches_to_ui()
            self.update_limit_switch_up_status(None)
            self.update_limit_switch_down_status(None)

    def update_status_widgets(self):
        self.app_state.status.update_homing_found(self.app_state.homing_found)
        self.app_state.status.update_motor_state(self.app_state.motor_state)
        button_states = control_button_disabled_states(
            motor_state=self.app_state.motor_state,
            limit_switch_up=self.app_state.status.limit_switch_up,
            limit_switch_down=self.app_state.status.limit_switch_down,
            supports_limit_switches=(
                self.app_state.motion_controller.supports_limit_switches
            ),
            supports_homing=self.app_state.motion_controller.supports_homing,
        )
        for button_id, disabled in button_states.items():
            try:
                self.query_one(f"#{button_id}", Button).disabled = disabled
            except Exception:
                pass

    def get_parameters(self) -> tuple:
        distance_mm = self.app_state.distance_controls.distance
        speed_mm_s = self.app_state.speed_controls.speed
        accel_mm_s2 = self.app_state.advanced_settings.get_acceleration()
        step_mode = self.app_state.step_mode.step_mode
        return distance_mm, speed_mm_s, accel_mm_s2, step_mode

    @property
    def motor_state(self):
        return self.app_state.motor_state

    def set_motor_state(self, state: str):
        self.app_state.motor_state = state
        self.update_status_widgets()
        if self.app_state.motion_controller.supports_limit_switches:
            if state == "moving":
                self.bind_limit_switches_to_motor()
            else:
                self.bind_limit_switches_to_ui()

    async def wait_for_motion_done(self, **kwargs):
        wait_task = asyncio.create_task(
            self.app_state.motion_controller.wait_for_motor_done_async(**kwargs)
        )
        self._motion_wait_task = wait_task
        try:
            return await wait_task
        finally:
            if self._motion_wait_task is wait_task:
                self._motion_wait_task = None

    def _cancel_motion_wait(self) -> None:
        if self._motion_wait_task is not None and not self._motion_wait_task.done():
            self._motion_wait_task.cancel()

    def _stop_and_disable_safely(self) -> None:
        for safety_action in (
            self.app_state.motion_controller.stop_motor,
            self.app_state.motion_controller.disable_motor,
        ):
            try:
                safety_action()
            except Exception:
                pass

    def handle_motion_fault(self, error: Exception, operation: str) -> None:
        """Put the UI and motor into a fail-safe state after a driver error."""
        self._stop_and_disable_safely()
        self.set_motor_state("fault")
        self.app.query_one("#logger", RichLog).write(
            f"[red]{operation} failed; motor stopped and disabled: {error}[/]"
        )

    def disable_after_abnormal_stop(self) -> None:
        """Keep UI state aligned with a fail-safe stopped motor."""
        self._stop_and_disable_safely()
        self.set_motor_state("disabled")

    def start_motion_action(self, coroutine) -> None:
        if self._motion_action_task is not None and not self._motion_action_task.done():
            coroutine.close()
            return
        task = asyncio.create_task(self._run_motion_action(coroutine))
        self._motion_action_task = task

    async def _run_motion_action(self, coroutine) -> None:
        try:
            await coroutine
        finally:
            if self._motion_action_task is asyncio.current_task():
                self._motion_action_task = None

    @on(Button.Pressed, "#move-up")
    async def move_up_action(self):
        distance_mm, speed_mm_s, accel_mm_s2, step_mode = self.get_parameters()
        self.start_motion_action(self.move_up(distance_mm, speed_mm_s, accel_mm_s2))

    async def move_up(
        self, distance_mm: float, speed_mm_s: float, acceleration_mm_s2: float = None
    ):
        log = self.app.query_one("#logger", RichLog)
        if self.app_state.motor_state == "enabled":
            def_dist, def_speed, def_accel, step_mode = self.get_parameters()
            if acceleration_mm_s2 is None:
                acceleration_mm_s2 = def_accel
            log.write(
                f"[cyan]Moving up ({distance_mm=} mm, "
                f"{speed_mm_s=} mm/s, {acceleration_mm_s2=} mm/s\u00b2, {step_mode=} µs).[/]"
            )
            self.set_motor_state("moving")
            await asyncio.sleep(0.1)
            if self.app_state.motor_state != "moving":
                log.write("[dark_orange]-> Movement aborted before starting.[/]")
                return
            try:
                self.app_state.motion_controller.move_up(
                    distance_mm, speed_mm_s, acceleration_mm_s2
                )
                stop = await self.wait_for_motion_done(
                    active_limit_direction=HomeDirection.UP
                )
                if self.app_state.motor_state == "disabled":
                    return
                if is_normal_motor_stop(stop):
                    log.write("[green]-> Finished moving up.[/]")
                    self.set_motor_state("enabled")
                else:
                    log.write(f"[red]-> Stopped moving up: {stop}.[/]")
                    self.disable_after_abnormal_stop()
            except ValueError as e:
                log.write(f"[red]{e}[/]")
                if self.app_state.motor_state != "disabled":
                    self.set_motor_state("enabled")
            except asyncio.CancelledError:
                if self.app_state.motor_state == "disabled":
                    log.write("[dark_orange]-> Movement aborted.[/]")
                    return
                raise
            except Exception as e:
                self.handle_motion_fault(e, "Move up")
        else:
            log.write("[red]Cannot move up while the motor is disabled.[/]")

    @on(Button.Pressed, "#move-down")
    async def move_down_action(self):
        distance_mm, speed_mm_s, accel_mm_s2, step_mode = self.get_parameters()
        self.start_motion_action(self.move_down(distance_mm, speed_mm_s, accel_mm_s2))

    async def move_down(
        self, distance_mm: float, speed_mm_s: float, acceleration_mm_s2: float = None
    ):
        log = self.app.query_one("#logger", RichLog)
        if self.app_state.motor_state == "enabled":
            def_dist, def_speed, def_accel, step_mode = self.get_parameters()
            if acceleration_mm_s2 is None:
                acceleration_mm_s2 = def_accel
            log.write(
                f"[cyan]Moving down ({distance_mm=} mm, "
                f"{speed_mm_s=} mm/s, {acceleration_mm_s2=} mm/s\u00b2, {step_mode=} µs).[/]"
            )
            self.set_motor_state("moving")
            await asyncio.sleep(0.1)
            if self.app_state.motor_state != "moving":
                log.write("[dark_orange]-> Movement aborted before starting.[/]")
                return
            try:
                self.app_state.motion_controller.move_down(
                    distance_mm, speed_mm_s, acceleration_mm_s2
                )
                stop = await self.wait_for_motion_done(
                    active_limit_direction=HomeDirection.DOWN
                )
                if self.app_state.motor_state == "disabled":
                    return
                if is_normal_motor_stop(stop):
                    log.write("[green]-> Finished moving down.[/]")
                    self.set_motor_state("enabled")
                else:
                    log.write(f"[red]-> Stopped moving down: {stop}.[/]")
                    self.disable_after_abnormal_stop()
            except ValueError as e:
                log.write(f"[red]{e}[/]")
                if self.app_state.motor_state != "disabled":
                    self.set_motor_state("enabled")
            except asyncio.CancelledError:
                if self.app_state.motor_state == "disabled":
                    log.write("[dark_orange]-> Movement aborted.[/]")
                    return
                raise
            except Exception as e:
                self.handle_motion_fault(e, "Move down")
        else:
            log.write("[red]Cannot move down while the motor is disabled.[/]")

    @on(Button.Pressed, "#enable-motor")
    async def enable_motor_action(self):
        log = self.app.query_one("#logger", RichLog)
        if self.app_state.motor_state == "disabled":
            self.app_state.motion_controller.enable_motor()
            self.set_motor_state("enabled")
            log.write("[green]Motor is now enabled.[/]")

    async def disable_motor_action(self):
        log = self.app.query_one("#logger", RichLog)
        if self.app_state.motor_state in ("moving", "homing"):
            self.app_state.motion_controller.stop_motor()
            self.app_state.motion_controller.disable_motor()
            self.set_motor_state("disabled")
            log.write("[dark_orange]Emergency stop: motor stopped and disabled.[/]")
            self._cancel_motion_wait()
            if self._homing_task is not None and not self._homing_task.done():
                self._homing_task.cancel()
        elif self.app_state.motor_state in ("enabled", "fault"):
            self.app_state.motion_controller.disable_motor()
            self.set_motor_state("disabled")
            log.write("[dark_orange]Motor is now disabled.[/]")

    @on(Button.Pressed, "#do-homing")
    async def do_homing_action(self):
        if self.app_state.motor_state == "enabled":
            await self.perform_homing()
        elif self.app_state.motor_state == "homing":
            # Do nothing when already homing
            return
        else:
            log = self.app.query_one("#logger", RichLog)
            log.write("[red]Cannot home while the motor is disabled.[/]")

    @on(Button.Pressed, "#stop-moving")
    async def stop_moving_action(self):
        log = self.app.query_one("#logger", RichLog)
        if self.app_state.motor_state == "moving":
            self.app_state.motion_controller.stop_motor()
            log.write("[dark_orange]Motor movement stopped.[/]")
        else:
            log.write("[red]No movement to stop[/]")

    async def perform_homing(self, home_up: bool = None):
        log = self.app.query_one("#logger", RichLog)
        speed = self.app_state.advanced_settings.get_homing_speed()

        log.write(f"[cyan]Starting limit switch homing ({speed=} mm/s)...[/]")
        self.set_motor_state("homing")
        await asyncio.sleep(0.1)
        if self.app_state.motor_state != "homing":
            log.write("[dark_orange]-> Homing aborted before starting.[/]")
            return
        home_direction = (
            None
            if home_up is None
            else (HomeDirection.UP if home_up else HomeDirection.DOWN)
        )
        self._homing_task = asyncio.create_task(
            self.app_state.motion_controller.home_async(
                speed,
                home_direction=home_direction,
            )
        )
        try:
            homing_found = await self._homing_task
            if homing_found:
                log.write("-> Finished homing.")
            else:
                log.write("[red]Homing failed[/]")
            self.set_homing_found(homing_found)
        except asyncio.CancelledError:
            log.write("[dark_orange]-> Homing aborted.[/]")
            self.set_homing_found(False)
        except ValueError as e:
            log.write(f"[red]{e}[/]")
        except Exception as e:
            self.set_homing_found(False)
            self.handle_motion_fault(e, "Homing")
        finally:
            self._homing_task = None
        if self.app_state.motor_state == "homing":
            self.set_motor_state("enabled")

    def set_homing_found(self, homing_found: bool):
        self.app_state.homing_found = homing_found
        self.app_state.status.update_homing_found(self.app_state.homing_found)
        self.app.query_one(PositionControls).update_button_states(homing_found)

    def setup_limit_switches_io(self):
        self.app_state.motion_controller.setup_limit_switches_io()

    def update_limit_switch_up_status(self, pin):
        triggered = self.app_state.motion_controller.read_limit_switch(HomeDirection.UP)
        self.app_state.status.update_limit_switch_up(triggered)
        self.update_status_widgets()

    def update_limit_switch_down_status(self, pin):
        triggered = self.app_state.motion_controller.read_limit_switch(
            HomeDirection.DOWN
        )
        self.app_state.status.update_limit_switch_down(triggered)
        self.update_status_widgets()

    def bind_limit_switches_to_motor(self):
        """Bind the limit switches to stop the motor driver."""
        self.app_state.motion_controller.bind_limit_switches_to_motor()

    def bind_limit_switches_to_ui(self):
        self.app_state.motion_controller.bind_limit_switch_callback(
            direction=HomeDirection.UP,
            callback=self.update_limit_switch_up_status,
            bouncetime=None,
        )
        self.app_state.motion_controller.bind_limit_switch_callback(
            direction=HomeDirection.DOWN,
            callback=self.update_limit_switch_down_status,
            bouncetime=None,
        )
