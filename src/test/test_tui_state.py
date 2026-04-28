from dip_coater.widgets.motor_controls import (
    control_button_disabled_states,
    is_normal_motor_stop,
)
from dip_coater.widgets.status import Status, motor_state_badge
from dip_coater.widgets.status import limit_switch_state_badge


def test_motor_state_badge_uses_compact_state_label():
    assert motor_state_badge("enabled") == "[green]ENABLED[/]"
    assert motor_state_badge("moving") == "[blue]MOVING[/]"
    assert motor_state_badge("disabled") == "[dark_orange]DISABLED[/]"
    assert motor_state_badge("fault") == "[red]FAULT[/]"
    assert motor_state_badge(None) == "[red]UNKNOWN[/]"


def test_limit_switch_state_badge_colorizes_open_and_triggered():
    assert limit_switch_state_badge(False) == "[green]Open[/]"
    assert limit_switch_state_badge(True) == "[red]Triggered[/]"


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


def test_status_polling_fault_sets_fault_state_and_message_once():
    app_state = FakeAppState()
    status = Status(app_state)

    status.record_polling_error(RuntimeError("driver not responding"))

    assert app_state.motor_state == "fault"
    assert status.status_error == "Status polling failed: driver not responding"
    assert app_state.motor_controls.updated is True
