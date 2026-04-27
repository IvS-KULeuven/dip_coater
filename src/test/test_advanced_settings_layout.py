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
