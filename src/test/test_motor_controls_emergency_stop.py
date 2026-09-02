import asyncio

import pytest
from textual import on
from textual.app import App, ComposeResult
from textual.widgets import Button, RichLog

from dip_coater.widgets.motor_controls import MotorControls
from dip_coater.widgets.position_controls import PositionControls


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
        self.home_started = asyncio.Event()
        self.stopped = False
        self.disabled = False
        self.wait_cancelled = False
        self.wait_error = None
        self.wait_result = None
        self.stop_error = None
        self.disable_error = None
        self.enable_error = None
        self.enabled = False

    def enable_motor(self):
        if self.enable_error is not None:
            raise self.enable_error
        self.enabled = True

    def move_up(self, distance_mm, speed_mm_s, acceleration_mm_s2):
        self.move = (distance_mm, speed_mm_s, acceleration_mm_s2)

    def move_down(self, distance_mm, speed_mm_s, acceleration_mm_s2):
        self.move = (distance_mm, speed_mm_s, acceleration_mm_s2)

    def move_to_position(self, position_mm, speed_mm_s, acceleration_mm_s2):
        self.move = (position_mm, speed_mm_s, acceleration_mm_s2)

    async def wait_for_motor_done_async(self, active_limit_direction=None):
        self.wait_started.set()
        if self.wait_error is not None:
            raise self.wait_error
        if self.wait_result is not None:
            return self.wait_result
        if self.disabled:
            return None
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            self.wait_cancelled = True
            raise

    async def home_async(self, speed_mm_s, home_direction=None):
        self.home_started.set()
        await asyncio.Event().wait()

    def stop_motor(self):
        self.stopped = True
        if self.stop_error is not None:
            raise self.stop_error

    def disable_motor(self):
        self.disabled = True
        if self.disable_error is not None:
            raise self.disable_error

    def is_homing_found(self):
        return True


class FakeAdvancedSettings:
    def get_acceleration(self):
        return 1.0

    def get_homing_speed(self):
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


class BarePositionControls(PositionControls):
    def compose(self) -> ComposeResult:
        return []

    def _on_mount(self, event):
        pass

    def watch_position(self, position):
        pass

    def update_button_states(self, homing_found):
        pass


class EmergencyStopHarness(App):
    def __init__(self, app_state):
        super().__init__()
        self.app_state = app_state
        self.motor_controls = MotorControls(app_state)
        self.app_state.motor_controls = self.motor_controls
        self.position_controls = BarePositionControls(app_state)
        self.app_state.position_controls = self.position_controls

    def compose(self) -> ComposeResult:
        yield self.motor_controls
        yield self.position_controls
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
@pytest.mark.parametrize("failing_action", ["stop", "disable"])
async def test_emergency_stop_attempts_every_action_after_driver_failure(
    failing_action,
):
    app_state = FakeAppState()
    app_state.motor_state = "moving"
    error = RuntimeError(f"{failing_action} failed")
    if failing_action == "stop":
        app_state.motion_controller.stop_error = error
    else:
        app_state.motion_controller.disable_error = error
    app = EmergencyStopHarness(app_state)

    async with app.run_test():
        await app_state.motor_controls.disable_motor_action()

    assert app_state.motion_controller.stopped is True
    assert app_state.motion_controller.disabled is True
    assert app_state.motor_state == "fault"


@pytest.mark.asyncio
async def test_enable_failure_stops_disables_and_sets_fault_state():
    app_state = FakeAppState()
    app_state.motor_state = "disabled"
    app_state.motion_controller.enable_error = RuntimeError("enable failed")
    app = EmergencyStopHarness(app_state)

    async with app.run_test():
        await app_state.motor_controls.enable_motor_action()

    assert app_state.motion_controller.stopped is True
    assert app_state.motion_controller.disabled is True
    assert app_state.motor_state == "fault"


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


@pytest.mark.asyncio
@pytest.mark.parametrize("method_name", ["move_up", "move_down"])
async def test_stop_during_motion_preflight_prevents_command_submission(method_name):
    app_state = FakeAppState()
    app = EmergencyStopHarness(app_state)

    async with app.run_test():
        move_task = asyncio.create_task(
            getattr(app_state.motor_controls, method_name)(10.0, 2.0, 1.0)
        )
        while app_state.motor_state != "moving":
            await asyncio.sleep(0)

        await app_state.motor_controls.disable_motor_action()
        await asyncio.wait_for(move_task, 1.0)

    assert not hasattr(app_state.motion_controller, "move")
    assert app_state.motion_controller.stopped is True
    assert app_state.motion_controller.disabled is True
    assert app_state.motor_state == "disabled"


@pytest.mark.asyncio
async def test_stop_during_homing_preflight_prevents_homing_command():
    app_state = FakeAppState()
    app = EmergencyStopHarness(app_state)

    async with app.run_test():
        app_state.motor_controls.set_homing_found = lambda value: None
        homing_task = asyncio.create_task(app_state.motor_controls.perform_homing())
        while app_state.motor_state != "homing":
            await asyncio.sleep(0)

        await app_state.motor_controls.disable_motor_action()
        try:
            await asyncio.sleep(0.15)
            assert app_state.motion_controller.home_started.is_set() is False
        finally:
            homing_task.cancel()
            await asyncio.gather(homing_task, return_exceptions=True)

    assert app_state.motion_controller.stopped is True
    assert app_state.motion_controller.disabled is True
    assert app_state.motor_state == "disabled"


@pytest.mark.asyncio
async def test_stop_during_absolute_move_preflight_prevents_command_submission():
    app_state = FakeAppState()
    app = EmergencyStopHarness(app_state)

    async with app.run_test():
        move_task = asyncio.create_task(
            app.position_controls.move_to_position(10.0, 2.0, 1.0)
        )
        while app_state.motor_state != "moving":
            await asyncio.sleep(0)

        await app_state.motor_controls.disable_motor_action()
        await asyncio.wait_for(move_task, 1.0)

    assert not hasattr(app_state.motion_controller, "move")
    assert app_state.motion_controller.stopped is True
    assert app_state.motion_controller.disabled is True
    assert app_state.motor_state == "disabled"


@pytest.mark.asyncio
async def test_motion_wait_error_stops_disables_and_sets_fault_state():
    app_state = FakeAppState()
    app_state.motion_controller.wait_error = RuntimeError("serial link lost")
    app = EmergencyStopHarness(app_state)

    async with app.run_test():
        await app_state.motor_controls.move_up(10.0, 2.0, 1.0)

    assert app_state.motion_controller.stopped is True
    assert app_state.motion_controller.disabled is True
    assert app_state.motor_state == "fault"


@pytest.mark.asyncio
async def test_abnormal_motion_stop_leaves_motor_disabled():
    app_state = FakeAppState()
    app_state.motion_controller.wait_result = "motion timed out after 10s"
    app = EmergencyStopHarness(app_state)

    async with app.run_test():
        await app_state.motor_controls.move_up(10.0, 2.0, 1.0)

    assert app_state.motion_controller.disabled is True
    assert app_state.motor_state == "disabled"


@pytest.mark.asyncio
async def test_abnormal_stop_reports_fault_when_shutdown_fails():
    app_state = FakeAppState()
    app_state.motion_controller.disable_error = RuntimeError("disable failed")
    app = EmergencyStopHarness(app_state)

    async with app.run_test():
        app_state.motor_controls.disable_after_abnormal_stop()

    assert app_state.motion_controller.stopped is True
    assert app_state.motion_controller.disabled is True
    assert app_state.motor_state == "fault"


@pytest.mark.asyncio
async def test_motion_state_locks_all_motion_setting_controls():
    app_state = FakeAppState()
    app = EmergencyStopHarness(app_state)

    async with app.run_test():
        app_state.motor_controls.set_motor_state("moving")

        assert app_state.speed_controls.disabled is True
        assert app_state.distance_controls.disabled is True
        assert app_state.position_controls.disabled is True
        assert app_state.advanced_settings.disabled is True
        assert app_state.step_mode.disabled is True

        app_state.motor_controls.set_motor_state("enabled")

        assert app_state.speed_controls.disabled is False
        assert app_state.distance_controls.disabled is False
        assert app_state.position_controls.disabled is False
        assert app_state.advanced_settings.disabled is False
        assert app_state.step_mode.disabled is False
