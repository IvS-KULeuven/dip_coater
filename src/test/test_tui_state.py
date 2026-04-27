from dip_coater.widgets.motor_controls import control_button_disabled_states
from dip_coater.widgets.status import motor_state_badge


def test_motor_state_badge_uses_compact_state_label():
    assert motor_state_badge("enabled") == "[green]ENABLED[/]"
    assert motor_state_badge("moving") == "[blue]MOVING[/]"
    assert motor_state_badge("fault") == "[red]FAULT[/]"
    assert motor_state_badge(None) == "[red]UNKNOWN[/]"


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
