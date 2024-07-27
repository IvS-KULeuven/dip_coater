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
from dip_coater.widgets.status import Status
from dip_coater.widgets.distance_controls import DistanceControls
from dip_coater.widgets.speed_controls import SpeedControls
from dip_coater.widgets.advanced_settings import AdvancedSettings
from dip_coater.widgets.step_mode import StepMode
from dip_coater.widgets.position_controls import PositionControls

from dip_coater.gpio import GPIOBase, GpioMode, GpioEdge, GpioPUD
from dip_coater.app_state import app_state
from TMC_2209._TMC_2209_move import StopMode
from dip_coater.motor.tmc2209 import TMC2209_MotorDriver


class MotorControls(Static):
    def __init__(self, gpio: GPIOBase, motor_driver: TMC2209_MotorDriver):
        super().__init__()
        self.GPIO = gpio
        self.motor_driver = motor_driver
        app_state.homing_found = False

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
        self.update_limit_switch_up_status(LIMIT_SWITCH_UP_PIN)
        self.update_limit_switch_down_status(LIMIT_SWITCH_DOWN_PIN)

    def update_status_widgets(self):
        status = self.app.query_one("#status")
        status.update_homing_found(app_state.homing_found)
        status.update_motor_state(app_state.motor_state)

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

    @property
    def motor_state(self):
        return app_state.motor_state

    def set_motor_state(self, state: str):
        app_state.motor_state = state
        self.update_status_widgets()

    @on(Button.Pressed, "#move-up")
    async def move_up_action(self):
        distance_mm, speed_mm_s, accel_mm_s2, step_mode = self.get_parameters()
        await self.move_up(distance_mm, speed_mm_s, accel_mm_s2)

    async def move_up(self, distance_mm: float, speed_mm_s: float, acceleration_mm_s2: float = None):
        log = self.app.query_one("#logger", RichLog)
        if app_state.motor_state == "enabled":
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
        if app_state.motor_state == "enabled":
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
        if app_state.motor_state == "disabled":
            self.motor_driver.enable_motor()
            self.bind_limit_switches_to_motor()
            self.set_motor_state("enabled")
            log.write(f"[green]Motor is now enabled.[/]")

    @on(Button.Pressed, "#disable-motor")
    async def disable_motor_action(self):
        log = self.app.query_one("#logger", RichLog)
        if app_state.motor_state == "homing":
            log.write("[red]We cannot disable the motor while homing is in progress[/]")
            return
        elif app_state.motor_state == "moving":
            log.write("[red]We cannot disable the motor while homing is moving[/]")
            return
        elif app_state.motor_state == "enabled":
            self.motor_driver.disable_motor()
            self.set_motor_state("disabled")
            log.write(f"[dark_orange]Motor is now disabled.[/]")

    @on(Button.Pressed, "#do-homing")
    async def do_homing_action(self):
        if app_state.motor_state == "enabled":
            await self.perform_homing()
        elif app_state.motor_state == "homing":
            # Do nothing when already homing
            return
        else:
            log = self.app.query_one("#logger", RichLog)
            log.write("[red]We cannot do homing when the motor is disabled[/]")

    @on(Button.Pressed, "#stop-moving")
    async def stop_moving_action(self):
        log = self.app.query_one("#logger", RichLog)
        if app_state.motor_state == "moving":
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
        app_state.homing_found = homing_found
        self.app.query_one(Status).update_homing_found(app_state.homing_found)
        self.app.query_one(PositionControls).update_button_states(homing_found)

    def setup_limit_switches_io(self):
        self._setup_limit_switch_io(LIMIT_SWITCH_UP_PIN, LIMIT_SWITCH_UP_NC)
        self.GPIO.add_event_callback(LIMIT_SWITCH_UP_PIN, self.update_limit_switch_up_status)
        self._setup_limit_switch_io(LIMIT_SWITCH_DOWN_PIN, LIMIT_SWITCH_DOWN_NC)
        self.GPIO.add_event_callback(LIMIT_SWITCH_DOWN_PIN, self.update_limit_switch_down_status)

    def _setup_limit_switch_io(self, limit_switch_pin, limit_switch_nc=True, bouncetime=5):
        self.GPIO.setup(limit_switch_pin, GpioMode.IN, pull_up_down=GpioPUD.PUD_UP)
        self.GPIO.remove_event_detect(limit_switch_pin)
        self.GPIO.add_event_detect(limit_switch_pin, GpioEdge.BOTH, callback=None, bouncetime=bouncetime)

    def update_limit_switch_up_status(self, pin_number):
        triggered = self.GPIO.input(pin_number) == 1 if LIMIT_SWITCH_UP_NC else self.GPIO.input(pin_number) == 0
        self.app.query_one("#status").update_limit_switch_up(triggered)

    def update_limit_switch_down_status(self, pin_number):
        triggered = self.GPIO.input(pin_number) == 1 if LIMIT_SWITCH_DOWN_NC else self.GPIO.input(pin_number) == 0
        self.app.query_one("#status").update_limit_switch_down(triggered)

    def bind_limit_switches_to_motor(self):
        """ Bind the limit switches to stop the motor driver."""
        self.motor_driver.bind_limit_switch(LIMIT_SWITCH_UP_PIN, NC=LIMIT_SWITCH_UP_NC)
        self.motor_driver.bind_limit_switch(LIMIT_SWITCH_DOWN_PIN, NC=LIMIT_SWITCH_DOWN_NC)
