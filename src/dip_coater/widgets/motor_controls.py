from textual.widgets import Button, RichLog
from textual.widgets import Static
from textual.app import ComposeResult
from textual import on, events

import asyncio

from dip_coater.constants import (
    LIMIT_SWITCH_UP_PIN, LIMIT_SWITCH_UP_NC,
    LIMIT_SWITCH_DOWN_PIN, LIMIT_SWITCH_DOWN_NC,
    HOME_UP, HOMING_MAX_DISTANCE
)
from dip_coater.widgets.advanced_settings import AdvancedSettings
from dip_coater.widgets.position_controls import PositionControls

from dip_coater.gpio import GpioMode, GpioEdge, GpioPUD, GpioState
from TMC_2209._TMC_2209_move import StopMode


class MotorControls(Static):
    def __init__(self, app_state):
        super().__init__()
        self.app_state = app_state
        self.app_state.homing_found = False

    def compose(self) -> ComposeResult:
        yield Button("Move UP ↑", id="move-up", variant="primary")
        yield Button("Move DOWN ↓", id="move-down", variant="primary")
        yield Button("ENABLE motor", id="enable-motor", variant="success")
        yield Button("DISABLE motor", id="disable-motor", variant="error")
        yield Button("Do HOMING", id="do-homing")
        #yield Button("STOP moving", id="stop-moving", variant="error")         Doesn't work currently...

    def _on_mount(self, event: events.Mount) -> None:
        self.update_status_widgets()
        self.setup_limit_switches_io()
        self.bind_limit_switches_to_ui()
        self.update_limit_switch_up_status(LIMIT_SWITCH_UP_PIN)
        self.update_limit_switch_down_status(LIMIT_SWITCH_DOWN_PIN)

    def update_status_widgets(self):
        self.app_state.status.update_homing_found(self.app_state.homing_found)
        self.app_state.status.update_motor_state(self.app_state.motor_state)

    def get_parameters(self) -> tuple:
        distance_mm = self.app_state.distance_controls.distance
        speed_mm_s = self.app_state.speed_controls.speed
        accel_mm_s2 = self.app_state.advanced_settings.acceleration
        step_mode = self.app_state.step_mode.step_mode
        return distance_mm, speed_mm_s, accel_mm_s2, step_mode

    @property
    def motor_state(self):
        return self.app_state.motor_state

    def set_motor_state(self, state: str):
        self.app_state.motor_state = state
        self.update_status_widgets()
        if state == "moving":
            self.bind_limit_switches_to_motor()
        else:
            self.bind_limit_switches_to_ui()

    @on(Button.Pressed, "#move-up")
    async def move_up_action(self):
        distance_mm, speed_mm_s, accel_mm_s2, step_mode = self.get_parameters()
        await self.move_up(distance_mm, speed_mm_s, accel_mm_s2)

    async def move_up(self, distance_mm: float, speed_mm_s: float, acceleration_mm_s2: float = None):
        log = self.app.query_one("#logger", RichLog)
        if self.app_state.motor_state == "enabled":
            def_dist, def_speed, def_accel, step_mode = self.get_parameters()
            if acceleration_mm_s2 is None:
                acceleration_mm_s2 = def_accel
            log.write(
                f"Moving up ({distance_mm=} mm, {speed_mm_s=} mm/s, {acceleration_mm_s2=} mm/s\u00b2, {step_mode=} µs).")
            self.set_motor_state("moving")
            await asyncio.sleep(0.1)
            try:
                self.app_state.motor_driver.move_up(distance_mm, speed_mm_s, acceleration_mm_s2, [LIMIT_SWITCH_UP_PIN])
                stop = await self.app_state.motor_driver.wait_for_motor_done_async()
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
        if self.app_state.motor_state == "enabled":
            def_dist, def_speed, def_accel, step_mode = self.get_parameters()
            if acceleration_mm_s2 is None:
                acceleration_mm_s2 = def_accel
            log.write(
                f"Moving down ({distance_mm=} mm, {speed_mm_s=} mm/s, {acceleration_mm_s2=} mm/s\u00b2, {step_mode=} µs).")
            self.set_motor_state("moving")
            await asyncio.sleep(0.1)
            try:
                self.app_state.motor_driver.move_down(distance_mm, speed_mm_s, acceleration_mm_s2, [LIMIT_SWITCH_DOWN_PIN])
                stop = await self.app_state.motor_driver.wait_for_motor_done_async()
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
        if self.app_state.motor_state == "disabled":
            self.app_state.motor_driver.enable_motor()
            self.set_motor_state("enabled")
            log.write(f"[green]Motor is now enabled.[/]")

    @on(Button.Pressed, "#disable-motor")
    async def disable_motor_action(self):
        log = self.app.query_one("#logger", RichLog)
        if self.app_state.motor_state == "homing":
            log.write("[red]We cannot disable the motor while homing is in progress[/]")
            return
        elif self.app_state.motor_state == "moving":
            log.write("[red]We cannot disable the motor while homing is moving[/]")
            return
        elif self.app_state.motor_state == "enabled":
            self.app_state.motor_driver.disable_motor()
            self.set_motor_state("disabled")
            log.write(f"[dark_orange]Motor is now disabled.[/]")

    @on(Button.Pressed, "#do-homing")
    async def do_homing_action(self):
        if self.app_state.motor_state == "enabled":
            await self.perform_homing()
        elif self.app_state.motor_state == "homing":
            # Do nothing when already homing
            return
        else:
            log = self.app.query_one("#logger", RichLog)
            log.write("[red]We cannot do homing when the motor is disabled[/]")

    @on(Button.Pressed, "#stop-moving")
    async def stop_moving_action(self):
        log = self.app.query_one("#logger", RichLog)
        if self.app_state.motor_state == "moving":
            self.app_state.motor_driver.stop_motor()
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
            homing_found = self.app_state.motor_driver.do_limit_switch_homing(LIMIT_SWITCH_UP_PIN, LIMIT_SWITCH_DOWN_PIN,
                                                                    distance, speed)
            if homing_found:
                log.write("-> Finished homing.")
            else:
                log.write("[red]Homing failed[/]")
            self.set_homing_found(homing_found)
        except ValueError as e:
            log.write(f"[red]{e}[/]")
        self.set_motor_state("enabled")

    def set_homing_found(self, homing_found: bool):
        self.app_state.homing_found = homing_found
        self.app_state.status.update_homing_found(self.app_state.homing_found)
        self.app.query_one(PositionControls).update_button_states(homing_found)

    def setup_limit_switches_io(self):
        self._setup_limit_switch_io(LIMIT_SWITCH_UP_PIN, LIMIT_SWITCH_UP_NC)
        self._setup_limit_switch_io(LIMIT_SWITCH_DOWN_PIN, LIMIT_SWITCH_DOWN_NC)

    def _setup_limit_switch_io(self, limit_switch_pin, limit_switch_nc=True):
        self.app_state.gpio.setup(limit_switch_pin, GpioMode.IN, pull_up_down=GpioPUD.PUD_UP)


    def update_limit_switch_up_status(self, pin):
        triggered = self.app_state.gpio.input(LIMIT_SWITCH_UP_PIN) == GpioState.HIGH if LIMIT_SWITCH_UP_NC else self.app_state.gpio.input(LIMIT_SWITCH_UP_PIN) == GpioState.LOW
        self.app_state.status.update_limit_switch_up(triggered)

    def update_limit_switch_down_status(self, pin):
        triggered = self.app_state.gpio.input(LIMIT_SWITCH_DOWN_PIN) == GpioState.HIGH if LIMIT_SWITCH_DOWN_NC else self.app_state.gpio.input(LIMIT_SWITCH_DOWN_PIN) == GpioState.LOW
        self.app_state.status.update_limit_switch_down(triggered)

    def bind_limit_switches_to_motor(self):
        """ Bind the limit switches to stop the motor driver."""
        self.app_state.motor_driver.bind_limit_switch(LIMIT_SWITCH_UP_PIN, NC=LIMIT_SWITCH_UP_NC)
        self.app_state.motor_driver.bind_limit_switch(LIMIT_SWITCH_DOWN_PIN, NC=LIMIT_SWITCH_DOWN_NC)

    def bind_limit_switches_to_ui(self):
        self._bind_limit_switch_to_ui(LIMIT_SWITCH_UP_PIN, LIMIT_SWITCH_UP_NC,
                                      callback=self.update_limit_switch_up_status, bouncetime=None)
        self._bind_limit_switch_to_ui(LIMIT_SWITCH_DOWN_PIN, LIMIT_SWITCH_DOWN_NC,
                                      callback=self.update_limit_switch_down_status, bouncetime=None)

    def _bind_limit_switch_to_ui(self, limit_switch_pin, limit_switch_nc=True, callback=None, bouncetime=5):
        self.app_state.gpio.remove_event_detect(limit_switch_pin)
        self.app_state.gpio.add_event_detect(limit_switch_pin, GpioEdge.BOTH, callback=callback, bouncetime=bouncetime)
