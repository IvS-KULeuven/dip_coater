import asyncio

import pytest

from dip_coater.mechanical.mechanical_setup import MechanicalSetup
from dip_coater.services.motion_controller import MotionController
from dip_coater.setup_profiles import create_custom_profile, get_machine_profile
from dip_coater.setup_profiles.machine_profile import (
    AvailableMachineSetups,
    HomeDirection,
    LimitSwitchPair,
    LimitSwitchPolarity,
    LimitSwitchSetup,
    LimitSwitchSource,
    MachineProfile,
)


class FakeGPIO:
    def __init__(self):
        self.setups = []
        self.events = {}
        self.cleaned = False

    def setup(self, pin, mode, pull_up_down=None, active_state=None):
        self.setups.append((pin, mode, pull_up_down, active_state))

    def input(self, pin):
        return 1

    def add_event_detect(self, pin, edge, callback, bouncetime=None):
        self.events[pin] = (edge, callback, bouncetime)

    def remove_event_detect(self, pin):
        self.events.pop(pin, None)

    def cleanup(self):
        self.cleaned = True


class FakeDriver:
    def __init__(self):
        self.moves = []
        self.last_home = None
        self.last_run_to_position = None
        self.last_position_call = None
        self.cleaned = False
        self.stopped = False

    def enable_motor(self):
        return None

    def disable_motor(self):
        return None

    def stop_motor(self):
        self.stopped = True
        return None

    def wait_for_motor_done(self):
        return None

    async def wait_for_motor_done_async(self):
        return None

    def move_up(self, distance_mm, speed_mm_s, acceleration_mm_s2=None, **kwargs):
        self.moves.append(("up", distance_mm, speed_mm_s, acceleration_mm_s2, kwargs))

    def move_down(self, distance_mm, speed_mm_s, acceleration_mm_s2=None, **kwargs):
        self.moves.append(("down", distance_mm, speed_mm_s, acceleration_mm_s2, kwargs))

    def do_limit_switch_homing(
        self,
        up_pin,
        down_pin,
        distance_mm,
        speed_mm_s,
        switch_up_nc,
        switch_down_nc,
    ):
        self.last_home = (
            up_pin,
            down_pin,
            distance_mm,
            speed_mm_s,
            switch_up_nc,
            switch_down_nc,
        )
        return True

    def run_to_position(
        self, position_mm, speed_mm_s=None, acceleration_mm_s2=None, homed_up=True
    ):
        self.last_run_to_position = (
            position_mm,
            speed_mm_s,
            acceleration_mm_s2,
            homed_up,
        )

    def get_current_position_mm(self, homed_up=True):
        self.last_position_call = homed_up
        return 12.5

    def is_homing_found(self):
        return False

    def cleanup(self):
        self.cleaned = True


class FakeDriverWithoutHomeFlag(FakeDriver):
    def run_to_position(self, position_mm, speed_mm_s=None, acceleration_mm_s2=None):
        self.last_run_to_position = (position_mm, speed_mm_s, acceleration_mm_s2)

    def get_current_position_mm(self):
        self.last_position_call = "no-flag"
        return 7.5


class FakeReferenceSwitchDriver(FakeDriver):
    def __init__(self):
        super().__init__()
        self.left_endstop = False
        self.right_endstop = False

    def get_left_endstop(self):
        return self.left_endstop

    def get_right_endstop(self):
        return self.right_endstop

    async def wait_for_motor_done_async(self):
        while True:
            await asyncio.sleep(1)


def test_custom_profile_can_override_setup_geometry_and_direction():
    base_profile = get_machine_profile(AvailableMachineSetups.SMALL_COATER)

    custom_profile = create_custom_profile(
        base_profile,
        mm_per_revolution=5.5,
        gearbox_ratio=2.0,
        steps_per_revolution=400,
        invert_motor_direction=True,
        home_direction=HomeDirection.DOWN,
    )

    assert custom_profile.key == AvailableMachineSetups.CUSTOM
    assert custom_profile.mechanical_setup.mm_per_revolution == 5.5
    assert custom_profile.mechanical_setup.gearbox_ratio == 2.0
    assert custom_profile.mechanical_setup.steps_per_revolution == 400
    assert custom_profile.invert_motor_direction is True
    assert custom_profile.home_direction == HomeDirection.DOWN
    assert base_profile.invert_motor_direction is False


def test_motion_controller_homing_uses_machine_profile_direction_and_switch_config():
    profile = MachineProfile(
        key=AvailableMachineSetups.CUSTOM,
        label="Custom",
        mechanical_setup=MechanicalSetup(mm_per_revolution=4.0),
        home_direction=HomeDirection.DOWN,
        limit_switches=LimitSwitchPair(
            up_pin=11, down_pin=12, up_nc=True, down_nc=False
        ),
        homing_max_distance_mm=88.0,
    )
    driver = FakeDriver()
    controller = MotionController(driver, profile, gpio=FakeGPIO())

    homing_found = controller.home(2.5)

    assert homing_found is True
    assert driver.last_home == (11, 12, -88.0, 2.5, True, False)


def test_motion_controller_passes_setup_reference_to_position_calls_when_supported():
    profile = MachineProfile(
        key=AvailableMachineSetups.CUSTOM,
        label="Custom",
        mechanical_setup=MechanicalSetup(mm_per_revolution=4.0),
        home_direction=HomeDirection.DOWN,
    )
    driver = FakeDriver()
    controller = MotionController(driver, profile)

    controller.move_to_position(10.0, 1.0, 2.0)
    position = controller.get_current_position_mm()

    assert driver.last_run_to_position == (10.0, 1.0, 2.0, False)
    assert driver.last_position_call is False
    assert position == 12.5


def test_motion_controller_falls_back_for_drivers_without_setup_reference_argument():
    profile = MachineProfile(
        key=AvailableMachineSetups.CUSTOM,
        label="Custom",
        mechanical_setup=MechanicalSetup(mm_per_revolution=4.0),
        limit_switches=LimitSwitchSetup.tmc5160_reference(),
    )
    driver = FakeDriverWithoutHomeFlag()
    controller = MotionController(driver, profile)

    controller.move_to_position(3.0, 0.5, 1.5)
    position = controller.get_current_position_mm()

    assert driver.last_run_to_position == (3.0, 0.5, 1.5)
    assert driver.last_position_call == "no-flag"
    assert position == 7.5


def test_motion_controller_prefers_driver_reference_switches():
    profile = MachineProfile(
        key=AvailableMachineSetups.CUSTOM,
        label="Custom",
        mechanical_setup=MechanicalSetup(mm_per_revolution=4.0),
        limit_switches=LimitSwitchSetup.tmc5160_reference(),
    )
    driver = FakeReferenceSwitchDriver()
    driver.left_endstop = True
    driver.right_endstop = False
    controller = MotionController(driver, profile, gpio=None)

    assert controller.supports_limit_switches is True
    assert controller.read_limit_switch(HomeDirection.UP) is False
    assert controller.read_limit_switch(HomeDirection.DOWN) is True


def test_motion_controller_refuses_move_toward_triggered_reference_switch():
    profile = MachineProfile(
        key=AvailableMachineSetups.CUSTOM,
        label="Custom",
        mechanical_setup=MechanicalSetup(mm_per_revolution=4.0),
        limit_switches=LimitSwitchSetup.tmc5160_reference(),
    )
    driver = FakeReferenceSwitchDriver()
    driver.left_endstop = False
    controller = MotionController(driver, profile, gpio=None)

    with pytest.raises(ValueError, match="limit switch is triggered"):
        controller.move_up(1.0, 0.5)

    assert driver.moves == []


@pytest.mark.asyncio
async def test_motion_controller_stops_when_active_reference_switch_triggers():
    profile = MachineProfile(
        key=AvailableMachineSetups.CUSTOM,
        label="Custom",
        mechanical_setup=MechanicalSetup(mm_per_revolution=4.0),
        limit_switches=LimitSwitchSetup.tmc5160_reference(),
    )
    driver = FakeReferenceSwitchDriver()
    controller = MotionController(driver, profile, gpio=None)

    async def trigger_limit_switch():
        await asyncio.sleep(0.02)
        driver.left_endstop = False

    driver.left_endstop = True
    trigger_task = asyncio.create_task(trigger_limit_switch())
    result = await asyncio.wait_for(
        controller.wait_for_motor_done_async(active_limit_direction=HomeDirection.UP),
        timeout=1.0,
    )
    await trigger_task

    assert driver.stopped is True
    assert result == "up limit switch triggered"


def test_large_profile_uses_landungsbruecke_reference_switches():
    profile = get_machine_profile(AvailableMachineSetups.LARGE_COATER)

    assert profile.requires_gpio is False
    assert profile.limit_switches.up.source == LimitSwitchSource.DRIVER_REFERENCE
    assert profile.limit_switches.down.source == LimitSwitchSource.DRIVER_REFERENCE
    assert profile.limit_switches.up.polarity == LimitSwitchPolarity.ACTIVE_LOW
    assert profile.limit_switches.down.polarity == LimitSwitchPolarity.ACTIVE_LOW
