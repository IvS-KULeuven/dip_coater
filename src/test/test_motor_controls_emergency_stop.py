import asyncio

import pytest
from textual import on
from textual.app import App, ComposeResult
from textual.widgets import Button, RichLog

from dip_coater.widgets.motor_controls import MotorControls


class FakeStatus:
    limit_switch_up = False
    limit_switch_down = False

    def update_homing_found(self, homing_found):
        self.homing_found = homing_found

    def update_motor_state(self, motor_state):
        self.motor_state = motor_state


class FakeMotionController:
    supports_limit_switches = False
    supports_homing = False

    def __init__(self):
        self.wait_started = asyncio.Event()
        self.stopped = False
        self.disabled = False
        self.wait_cancelled = False

    def move_up(self, distance_mm, speed_mm_s, acceleration_mm_s2):
        self.move = (distance_mm, speed_mm_s, acceleration_mm_s2)

    async def wait_for_motor_done_async(self, active_limit_direction=None):
        self.wait_started.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            self.wait_cancelled = True
            raise

    def stop_motor(self):
        self.stopped = True

    def disable_motor(self):
        self.disabled = True


class FakeAdvancedSettings:
    def get_acceleration(self):
        return 1.0


class FakeDistanceControls:
    distance = 5.0


class FakeSpeedControls:
    speed = 2.0


class FakeStepMode:
    step_mode = 16


class FakeAppState:
    def __init__(self):
        self.motor_state = "enabled"
        self.homing_found = False
        self.status = FakeStatus()
        self.motion_controller = FakeMotionController()
        self.advanced_settings = FakeAdvancedSettings()
        self.distance_controls = FakeDistanceControls()
        self.speed_controls = FakeSpeedControls()
        self.step_mode = FakeStepMode()
        self.motor_controls = None


class EmergencyStopHarness(App):
    def __init__(self, app_state):
        super().__init__()
        self.app_state = app_state
        self.motor_controls = MotorControls(app_state)
        self.app_state.motor_controls = self.motor_controls

    def compose(self) -> ComposeResult:
        yield self.motor_controls
        yield RichLog(markup=True, id="logger")

    @on(Button.Pressed, "#disable-motor")
    async def disable_motor(self):
        await self.app_state.motor_controls.disable_motor_action()


@pytest.mark.asyncio
async def test_stop_and_disable_button_cancels_active_motion_wait():
    app_state = FakeAppState()
    app = EmergencyStopHarness(app_state)

    async with app.run_test() as pilot:
        move_task = asyncio.create_task(
            app_state.motor_controls.move_up(10.0, 2.0, 1.0)
        )
        await asyncio.wait_for(app_state.motion_controller.wait_started.wait(), 1.0)

        assert app.query_one("#disable-motor", Button).disabled is False
        await pilot.click("#disable-motor")

        await asyncio.wait_for(move_task, 1.0)

    assert app_state.motion_controller.stopped is True
    assert app_state.motion_controller.disabled is True
    assert app_state.motion_controller.wait_cancelled is True
    assert app_state.motor_state == "disabled"


@pytest.mark.asyncio
async def test_stop_and_disable_button_interrupts_motion_started_from_ui_click():
    app_state = FakeAppState()
    app = EmergencyStopHarness(app_state)

    async with app.run_test() as pilot:
        move_click_task = asyncio.create_task(pilot.click("#move-up"))
        await asyncio.wait_for(app_state.motion_controller.wait_started.wait(), 1.0)

        assert app.query_one("#disable-motor", Button).disabled is False
        await pilot.click("#disable-motor")

        await asyncio.wait_for(move_click_task, 1.0)

    assert app_state.motion_controller.stopped is True
    assert app_state.motion_controller.disabled is True
    assert app_state.motion_controller.wait_cancelled is True
    assert app_state.motor_state == "disabled"
