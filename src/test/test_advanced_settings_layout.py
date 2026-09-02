from types import SimpleNamespace

from dip_coater.utils.SettingChanged import SettingChanged
from dip_coater.widgets.advanced.advanced_settings_base import (
    COMMON_ADVANCED_GROUP_TITLE,
)
from dip_coater.widgets.advanced.advanced_settings_tmc2209 import (
    TMC2209_ADVANCED_GROUP_TITLES,
)
from dip_coater.widgets.advanced.advanced_settings_tmc2660 import (
    TMC2660_ADVANCED_GROUP_TITLES,
)
from dip_coater.widgets.advanced.advanced_settings_trinamic_tmc5160 import (
    TMC5160_ADVANCED_GROUP_TITLES,
)
from dip_coater.widgets.step_mode import StepMode
from dip_coater.widgets.tabs.advanced_settings_tab import AdvancedSettingsTab


def test_advanced_settings_expose_group_titles():
    assert COMMON_ADVANCED_GROUP_TITLE == "Motion and current"
    assert TMC2209_ADVANCED_GROUP_TITLES == (
        "Driver mode",
        "Threshold speed",
        "Homing",
    )
    assert TMC2660_ADVANCED_GROUP_TITLES == (
        "Driver mode",
        "StallGuard",
        "CoolStep",
    )
    assert TMC5160_ADVANCED_GROUP_TITLES == (
        "Driver mode",
        "StealthChop",
        "StallGuard",
        "CoolStep",
    )


def test_advanced_setting_events_are_ignored_during_motion():
    calls = []
    app_state = SimpleNamespace(
        motor_state="moving",
        motor_driver=SimpleNamespace(set_current=lambda value: calls.append(value)),
        status_advanced=SimpleNamespace(update_current=lambda value: calls.append(value)),
    )
    tab = SimpleNamespace(app_state=app_state)

    AdvancedSettingsTab.on_setting_changed(tab, SettingChanged("current", 500))

    assert calls == []


def test_step_mode_changes_are_ignored_during_motion():
    calls = []
    step_mode = SimpleNamespace(
        app_state=SimpleNamespace(
            motor_state="homing",
            motor_driver=SimpleNamespace(
                set_microsteps=lambda value: calls.append(value)
            ),
        )
    )

    StepMode.set_microsteps(step_mode, 16, "1/16")

    assert calls == []
