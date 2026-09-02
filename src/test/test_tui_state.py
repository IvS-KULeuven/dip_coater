from pathlib import Path
from types import SimpleNamespace

from dip_coater.widgets.motor_controls import (
    control_button_disabled_states,
    is_normal_motor_stop,
)
from dip_coater.widgets.status import Status, motor_state_badge
from dip_coater.widgets.status import limit_switch_state_badge


def test_motor_state_badge_uses_compact_state_label():
    assert motor_state_badge("enabled") == "[green]ENABLED[/]"
    assert motor_state_badge("moving") == "[blue]MOVING[/]"
    assert motor_state_badge("disabled") == "[red]DISABLED[/]"
    assert motor_state_badge("fault") == "[red]FAULT[/]"
    assert motor_state_badge(None) == "[red]UNKNOWN[/]"


def test_limit_switch_state_badge_colorizes_open_and_triggered():
    assert limit_switch_state_badge(False) == "[green]Open[/]"
    assert limit_switch_state_badge(True) == "[red]Triggered[/]"


def test_status_mount_uses_widget_owned_polling_timer():
    scheduled = []
    timer = object()
    callback = object()
    status = SimpleNamespace(
        app_state=SimpleNamespace(
            config=SimpleNamespace(DEFAULT_SPEED=1.0, DEFAULT_DISTANCE=2.0),
            homing_found=False,
            motor_state="disabled",
        ),
        update_motor_state=lambda _state: None,
        fetch_new_position=callback,
        set_interval=lambda interval, scheduled_callback: (
            scheduled.append((interval, scheduled_callback)) or timer
        ),
    )
    Status._on_mount(status)

    assert scheduled == [(0.5, callback)]
    assert status.position_timer is timer


def test_status_widget_only_has_compact_motor_state_line():
    status_source = Path(__file__).parents[1] / "dip_coater" / "widgets" / "status.py"
    source = status_source.read_text()

    assert "status-state-strip" in source
    assert "status-motor-state" not in source


def test_normal_motor_stop_does_not_depend_on_tmc2209_imports():
    class StopModeLike:
        name = "NO"

    assert is_normal_motor_stop(None) is True
    assert is_normal_motor_stop(StopModeLike()) is True
    assert is_normal_motor_stop("up limit switch triggered") is False


def test_control_buttons_disable_moves_toward_triggered_limit_switches():
    states = control_button_disabled_states(
        motor_state="enabled",
        limit_switch_up=True,
        limit_switch_down=False,
        supports_limit_switches=True,
        supports_homing=True,
    )

    assert states["move-up"] is True
    assert states["move-down"] is False
    assert states["enable-motor"] is True
    assert states["disable-motor"] is False
    assert states["do-homing"] is False


def test_control_buttons_disable_motion_when_limit_switch_state_is_unknown():
    states = control_button_disabled_states(
        motor_state="enabled",
        limit_switch_up=None,
        limit_switch_down=False,
        supports_limit_switches=True,
        supports_homing=False,
    )

    assert states["move-up"] is True
    assert states["move-down"] is False
    assert states["do-homing"] is True


def test_control_buttons_allow_stop_and_disable_in_fault_state():
    states = control_button_disabled_states(
        motor_state="fault",
        limit_switch_up=None,
        limit_switch_down=None,
        supports_limit_switches=True,
        supports_homing=True,
    )

    assert states["move-up"] is True
    assert states["move-down"] is True
    assert states["enable-motor"] is True
    assert states["disable-motor"] is False
    assert states["do-homing"] is True


class FakeMotorControls:
    def __init__(self):
        self.updated = False

    def update_status_widgets(self):
        self.updated = True


class FakeAppState:
    def __init__(self):
        self.motor_state = "enabled"
        self.motor_controls = FakeMotorControls()
        self.motion_controller = FakeFaultController()


class FakeFaultController:
    def __init__(self):
        self.stopped = False
        self.disabled = False

    def stop_motor(self):
        self.stopped = True

    def disable_motor(self):
        self.disabled = True


def test_status_polling_fault_sets_fault_state_and_message_once():
    app_state = FakeAppState()
    status = Status(app_state)

    status.record_polling_error(RuntimeError("driver not responding"))

    assert app_state.motor_state == "fault"
    assert status.status_error == "Status polling failed: driver not responding"
    assert app_state.motor_controls.updated is True
    assert app_state.motion_controller.stopped is True
    assert app_state.motion_controller.disabled is True
