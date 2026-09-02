import asyncio
import threading
import time

import pytest

from dip_coater.mechanical.mechanical_setup import MechanicalSetup
from dip_coater.services.motion_controller import MotionController
from dip_coater.setup_profiles import create_custom_profile, get_machine_profile
from dip_coater.setup_profiles.machine_profile import (
    AvailableMachineSetups,
    HomeDirection,
    LimitSwitch,
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


class CapturingSessionLog:
    def __init__(self):
        self.events = []

    def write(self, event, **fields):
        self.events.append((event, fields))


class FakeDriver:
    def __init__(self):
        self.moves = []
        self.last_home = None
        self.last_run_to_position = None
        self.last_position_call = None
        self.cleaned = False
        self.stopped = False
        self.disabled = False
        self.homing_found = False
        self.shutdown_calls = []

    def enable_motor(self):
        return None

    def disable_motor(self):
        self.disabled = True
        self.shutdown_calls.append("disable")
        return None

    def stop_motor(self):
        self.stopped = True
        self.shutdown_calls.append("stop")
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
        return self.homing_found

    def cleanup(self):
        self.cleaned = True
        self.shutdown_calls.append("cleanup")


class PositionedFakeDriver(FakeDriver):
    def __init__(self, position_mm: float | None):
        super().__init__()
        self.position_mm = position_mm

    def get_current_position_mm(self, homed_up=True):
        self.last_position_call = homed_up
        return self.position_mm

    def is_homing_found(self):
        return self.position_mm is not None


class FakeReferenceSwitchDriver(FakeDriver):
    def __init__(self):
        super().__init__()
        self.left_endstop = False
        self.right_endstop = False
        self.reference_stop_calls = []
        self.homed = False
        self.cleared_homing = False

    def get_left_endstop(self):
        return self.left_endstop

    def get_right_endstop(self):
        return self.right_endstop

    def enable_reference_stops(self, *, left=True, right=True):
        self.reference_stop_calls.append((left, right))

    def mark_homed(self):
        self.homed = True
        self.left_endstop = False
        self.right_endstop = False

    def clear_homing(self):
        self.cleared_homing = True
        self.homed = False

    def is_homing_found(self):
        return self.homed

    async def wait_for_motor_done_async(self):
        while True:
            await asyncio.sleep(1)


class HomingReferenceSwitchDriver(FakeReferenceSwitchDriver):
    """Reference-switch driver simulating the home switch closing during a move.

    The TMC5160 reference setup uses ACTIVE_LOW polarity: raw endstop = True means
    the switch is open (not triggered); raw endstop = False means it's pressed.
    """

    def __init__(self, home_direction: HomeDirection):
        super().__init__()
        self._home_direction = home_direction
        self._move_count = 0
        self.left_endstop = True
        self.right_endstop = True

    def move_up(self, distance_mm, speed_mm_s, acceleration_mm_s2=None, **kwargs):
        super().move_up(distance_mm, speed_mm_s, acceleration_mm_s2, **kwargs)
        self._after_move(HomeDirection.UP)

    def move_down(self, distance_mm, speed_mm_s, acceleration_mm_s2=None, **kwargs):
        super().move_down(distance_mm, speed_mm_s, acceleration_mm_s2, **kwargs)
        self._after_move(HomeDirection.DOWN)

    def _after_move(self, direction: HomeDirection):
        self._move_count += 1
        # Simulate switch closing on the homing approach (the first long move toward home).
        if direction == self._home_direction and self._move_count == 1:
            if self._home_direction == HomeDirection.UP:
                self.left_endstop = False
            else:
                self.right_endstop = False

    def mark_homed(self):
        # Homing zeros the position; the back-off move that follows releases the switch.
        self.homed = True


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


@pytest.mark.parametrize(
    ("overrides", "field_name"),
    [
        ({"min_position_mm": float("nan")}, "min_position_mm"),
        ({"max_position_mm": float("inf")}, "max_position_mm"),
        (
            {"min_position_mm": 10.0, "max_position_mm": 5.0},
            "max_position_mm",
        ),
        (
            {"min_position_mm": 10.0, "max_position_mm": 10.0},
            "max_position_mm",
        ),
        ({"homing_max_distance_mm": 0.0}, "homing_max_distance_mm"),
        ({"homing_max_distance_mm": float("nan")}, "homing_max_distance_mm"),
    ],
)
def test_machine_profile_rejects_invalid_safety_limits(overrides, field_name):
    values = {
        "key": AvailableMachineSetups.CUSTOM,
        "label": "Custom",
        "mechanical_setup": MechanicalSetup(mm_per_revolution=4.0),
    }
    values.update(overrides)

    with pytest.raises(ValueError, match=field_name):
        MachineProfile(**values)


@pytest.mark.parametrize(
    ("overrides", "field_name"),
    [
        ({"key": "custom"}, "key"),
        ({"label": "  "}, "label"),
        ({"mechanical_setup": None}, "mechanical_setup"),
        ({"invert_motor_direction": 1}, "invert_motor_direction"),
        ({"home_direction": "up"}, "home_direction"),
        ({"limit_switches": object()}, "limit_switches"),
    ],
)
def test_machine_profile_rejects_invalid_field_types(overrides, field_name):
    values = {
        "key": AvailableMachineSetups.CUSTOM,
        "label": "Custom",
        "mechanical_setup": MechanicalSetup(mm_per_revolution=4.0),
    }
    values.update(overrides)

    with pytest.raises(ValueError, match=field_name):
        MachineProfile(**values)


@pytest.mark.parametrize(
    ("switch_values", "field_name"),
    [
        (
            {
                "source": LimitSwitchSource.GPIO,
                "polarity": LimitSwitchPolarity.ACTIVE_HIGH,
                "pin": None,
            },
            "pin",
        ),
        (
            {
                "source": LimitSwitchSource.GPIO,
                "polarity": LimitSwitchPolarity.ACTIVE_HIGH,
                "pin": -1,
            },
            "pin",
        ),
        (
            {
                "source": LimitSwitchSource.DRIVER_REFERENCE,
                "polarity": LimitSwitchPolarity.ACTIVE_LOW,
                "pin": 19,
            },
            "pin",
        ),
        (
            {
                "source": "gpio",
                "polarity": LimitSwitchPolarity.ACTIVE_HIGH,
                "pin": 19,
            },
            "source",
        ),
        (
            {
                "source": LimitSwitchSource.GPIO,
                "polarity": "active_high",
                "pin": 19,
            },
            "polarity",
        ),
    ],
)
def test_limit_switch_rejects_invalid_wiring(switch_values, field_name):
    with pytest.raises(ValueError, match=field_name):
        LimitSwitch(**switch_values)


def test_limit_switch_setup_rejects_duplicate_gpio_pins():
    with pytest.raises(ValueError, match="different GPIO pins"):
        LimitSwitchSetup.gpio(up_pin=19, down_pin=19)


def test_limit_switch_setup_rejects_mixed_hardware_sources():
    with pytest.raises(ValueError, match="same hardware source"):
        LimitSwitchSetup(
            up=LimitSwitch(
                source=LimitSwitchSource.GPIO,
                polarity=LimitSwitchPolarity.ACTIVE_HIGH,
                pin=19,
            ),
            down=LimitSwitch(
                source=LimitSwitchSource.DRIVER_REFERENCE,
                polarity=LimitSwitchPolarity.ACTIVE_LOW,
            ),
        )


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
    driver.homing_found = True
    controller = MotionController(driver, profile)

    controller.move_to_position(10.0, 1.0, 2.0)
    position = controller.get_current_position_mm()

    assert driver.last_run_to_position == (10.0, 1.0, 2.0, False)
    assert driver.last_position_call is False
    assert position == 12.5


def test_motion_controller_requires_standard_position_contract():
    profile = MachineProfile(
        key=AvailableMachineSetups.CUSTOM,
        label="Custom",
        mechanical_setup=MechanicalSetup(mm_per_revolution=4.0),
        limit_switches=LimitSwitchSetup.tmc5160_reference(),
    )
    driver = FakeDriver()
    driver.homing_found = True
    controller = MotionController(driver, profile)

    controller.move_to_position(3.0, 0.5, 1.5)
    position = controller.get_current_position_mm()

    assert driver.last_run_to_position == (3.0, 0.5, 1.5, True)
    assert driver.last_position_call is True
    assert position == 12.5


def test_motion_controller_records_relative_move_diagnostics():
    profile = MachineProfile(
        key=AvailableMachineSetups.CUSTOM,
        label="Custom",
        mechanical_setup=MechanicalSetup(mm_per_revolution=4.0),
    )
    driver = FakeDriver()
    session_log = CapturingSessionLog()
    controller = MotionController(driver, profile, session_log=session_log)

    controller.move_up(4.0, 2.0, 1.5)

    assert session_log.events == [
        (
            "motion_requested",
            {
                "kind": "relative",
                "direction": "up",
                "distance_mm": 4.0,
                "speed_mm_s": 2.0,
                "acceleration_mm_s2": 1.5,
                "timeout_s": 11.0,
            },
        )
    ]


@pytest.mark.asyncio
async def test_motion_controller_records_motion_completion():
    profile = MachineProfile(
        key=AvailableMachineSetups.CUSTOM,
        label="Custom",
        mechanical_setup=MechanicalSetup(mm_per_revolution=4.0),
    )
    driver = FakeDriver()
    session_log = CapturingSessionLog()
    controller = MotionController(driver, profile, session_log=session_log)

    result = await controller.wait_for_motor_done_async(timeout_s=1.0)

    assert result is None
    assert session_log.events == [("motion_completed", {"result": None})]


@pytest.mark.asyncio
async def test_async_wait_fault_stops_and_disables_motor():
    class FaultingWaitDriver(FakeDriver):
        async def wait_for_motor_done_async(self):
            raise RuntimeError("serial link lost")

    profile = get_machine_profile(AvailableMachineSetups.SMALL_COATER)
    driver = FaultingWaitDriver()
    session_log = CapturingSessionLog()
    controller = MotionController(driver, profile, session_log=session_log)

    with pytest.raises(RuntimeError, match="serial link lost"):
        await controller.wait_for_motor_done_async(timeout_s=1.0)

    assert driver.stopped is True
    assert driver.disabled is True
    assert session_log.events == [("motion_fault", {"error": "serial link lost"})]


def test_blocking_wait_fault_stops_and_disables_motor():
    class FaultingWaitDriver(FakeDriver):
        def wait_for_motor_done(self):
            raise RuntimeError("driver stopped responding")

    profile = get_machine_profile(AvailableMachineSetups.SMALL_COATER)
    driver = FaultingWaitDriver()
    controller = MotionController(driver, profile)

    with pytest.raises(RuntimeError, match="driver stopped responding"):
        controller.wait_for_motor_done()

    assert driver.stopped is True
    assert driver.disabled is True


def test_motion_controller_does_not_retry_typeerror_from_standard_position_contract():
    profile = MachineProfile(
        key=AvailableMachineSetups.CUSTOM,
        label="Custom",
        mechanical_setup=MechanicalSetup(mm_per_revolution=4.0),
    )

    class BuggyDriver(FakeDriver):
        def __init__(self):
            super().__init__()
            self.run_to_position_calls = 0

        def run_to_position(
            self, position_mm, speed_mm_s=None, acceleration_mm_s2=None, homed_up=True
        ):
            self.run_to_position_calls += 1
            raise TypeError("driver contract bug")

    driver = BuggyDriver()
    driver.homing_found = True
    controller = MotionController(driver, profile)

    with pytest.raises(TypeError, match="driver contract bug"):
        controller.move_to_position(3.0, 0.5, 1.5)

    assert driver.run_to_position_calls == 1


def test_motion_controller_rejects_absolute_position_outside_profile_bounds():
    profile = MachineProfile(
        key=AvailableMachineSetups.CUSTOM,
        label="Custom",
        mechanical_setup=MechanicalSetup(mm_per_revolution=4.0),
        min_position_mm=0.0,
        max_position_mm=20.0,
    )
    driver = FakeDriver()
    controller = MotionController(driver, profile)

    with pytest.raises(ValueError, match="outside travel range"):
        controller.move_to_position(21.0, 1.0, 2.0)

    assert driver.last_run_to_position is None


def test_motion_controller_rejects_absolute_move_without_home_reference():
    profile = get_machine_profile(AvailableMachineSetups.SMALL_COATER)
    driver = FakeDriver()
    controller = MotionController(driver, profile)

    with pytest.raises(ValueError, match="must be homed"):
        controller.move_to_position(10.0, 1.0)

    assert driver.last_run_to_position is None


def test_absolute_move_timeout_uses_driver_speed_when_speed_is_omitted():
    class RetainedSpeedDriver(FakeDriver):
        def get_speed_rps(self):
            return 0.25

    profile = MachineProfile(
        key=AvailableMachineSetups.CUSTOM,
        label="Custom",
        mechanical_setup=MechanicalSetup(mm_per_revolution=4.0),
        min_position_mm=0.0,
        max_position_mm=100.0,
    )
    driver = RetainedSpeedDriver()
    driver.homing_found = True
    controller = MotionController(driver, profile)

    controller.move_to_position(32.5, speed_mm_s=None)

    assert controller._last_motion_timeout_s == pytest.approx(65.0)
    assert driver.last_run_to_position[1] is None


def test_absolute_move_without_known_speed_disables_timeout_estimate():
    profile = get_machine_profile(AvailableMachineSetups.SMALL_COATER)
    driver = FakeDriver()
    driver.homing_found = True
    controller = MotionController(driver, profile)

    controller.move_to_position(32.5, speed_mm_s=None)

    assert controller._last_motion_timeout_s is None


def test_motion_controller_rejects_relative_move_that_would_exceed_profile_bounds_when_homed():
    profile = MachineProfile(
        key=AvailableMachineSetups.CUSTOM,
        label="Custom",
        mechanical_setup=MechanicalSetup(mm_per_revolution=4.0),
        home_direction=HomeDirection.DOWN,
        min_position_mm=0.0,
        max_position_mm=20.0,
    )
    driver = PositionedFakeDriver(position_mm=19.0)
    controller = MotionController(driver, profile)

    with pytest.raises(ValueError, match="outside travel range"):
        controller.move_up(2.0, 1.0)

    assert driver.moves == []


@pytest.mark.parametrize("method_name", ["move_up", "move_down"])
@pytest.mark.parametrize("distance_mm", [0.0, -1.0, float("nan"), float("inf")])
def test_motion_controller_rejects_nonpositive_or_nonfinite_distance(
    method_name, distance_mm
):
    profile = get_machine_profile(AvailableMachineSetups.SMALL_COATER)
    driver = FakeDriver()
    controller = MotionController(driver, profile)

    with pytest.raises(ValueError, match="distance_mm must be finite and positive"):
        getattr(controller, method_name)(distance_mm, 1.0)

    assert driver.moves == []


@pytest.mark.parametrize("method_name", ["move_up", "move_down"])
@pytest.mark.parametrize("distance_mm", [True, "1"])
def test_motion_controller_rejects_malformed_distance_without_driver_calls(
    method_name, distance_mm
):
    profile = get_machine_profile(AvailableMachineSetups.SMALL_COATER)
    driver = FakeDriver()
    controller = MotionController(driver, profile)

    with pytest.raises(ValueError, match="distance_mm must be finite and positive"):
        getattr(controller, method_name)(distance_mm, 1.0)

    assert driver.moves == []


@pytest.mark.parametrize("speed_mm_s", [0.0, -1.0, float("nan"), float("inf")])
def test_motion_controller_rejects_nonpositive_or_nonfinite_speed(speed_mm_s):
    profile = get_machine_profile(AvailableMachineSetups.SMALL_COATER)
    driver = FakeDriver()
    controller = MotionController(driver, profile)

    with pytest.raises(ValueError, match="speed_mm_s must be finite and positive"):
        controller.move_up(1.0, speed_mm_s)

    assert driver.moves == []


@pytest.mark.parametrize("acceleration", [0.0, -1.0, float("nan"), float("inf")])
def test_motion_controller_rejects_invalid_optional_acceleration(acceleration):
    profile = get_machine_profile(AvailableMachineSetups.SMALL_COATER)
    driver = FakeDriver()
    controller = MotionController(driver, profile)

    with pytest.raises(
        ValueError, match="acceleration_mm_s2 must be finite and positive"
    ):
        controller.move_up(1.0, 1.0, acceleration)

    assert driver.moves == []


@pytest.mark.parametrize(
    ("position_mm", "speed_mm_s"),
    [(float("nan"), 1.0), (float("inf"), 1.0), (1.0, 0.0)],
)
def test_motion_controller_validates_absolute_motion_inputs(
    position_mm, speed_mm_s
):
    profile = get_machine_profile(AvailableMachineSetups.SMALL_COATER)
    driver = FakeDriver()
    controller = MotionController(driver, profile)

    with pytest.raises(ValueError, match="must be finite"):
        controller.move_to_position(position_mm, speed_mm_s)

    assert driver.last_run_to_position is None


@pytest.mark.parametrize("position_mm", [True, "1"])
def test_motion_controller_rejects_malformed_absolute_positions(position_mm):
    profile = get_machine_profile(AvailableMachineSetups.SMALL_COATER)
    driver = FakeDriver()
    controller = MotionController(driver, profile)

    with pytest.raises(ValueError, match="position_mm must be finite"):
        controller.move_to_position(position_mm, 1.0)

    assert driver.last_run_to_position is None


@pytest.mark.asyncio
@pytest.mark.parametrize("timeout_s", [-1.0, float("nan"), True, "1"])
async def test_motion_controller_rejects_invalid_wait_timeout_before_waiting(
    timeout_s,
):
    profile = get_machine_profile(AvailableMachineSetups.SMALL_COATER)

    class CountingWaitDriver(FakeDriver):
        def __init__(self):
            super().__init__()
            self.wait_calls = 0

        async def wait_for_motor_done_async(self):
            self.wait_calls += 1

    driver = CountingWaitDriver()
    controller = MotionController(driver, profile)

    with pytest.raises(ValueError, match="timeout_s must be finite and non-negative"):
        await controller.wait_for_motor_done_async(timeout_s=timeout_s)

    assert driver.wait_calls == 0


@pytest.mark.asyncio
async def test_motion_controller_rejects_invalid_active_limit_direction():
    profile = MachineProfile(
        key=AvailableMachineSetups.CUSTOM,
        label="Custom",
        mechanical_setup=MechanicalSetup(mm_per_revolution=4.0),
        limit_switches=LimitSwitchSetup.tmc5160_reference(),
    )

    class CountingWaitDriver(FakeReferenceSwitchDriver):
        def __init__(self):
            super().__init__()
            self.wait_calls = 0

        async def wait_for_motor_done_async(self):
            self.wait_calls += 1

    driver = CountingWaitDriver()
    controller = MotionController(driver, profile)

    with pytest.raises(ValueError, match="HomeDirection"):
        await controller.wait_for_motor_done_async(active_limit_direction="up")

    assert driver.wait_calls == 0


@pytest.mark.parametrize("speed_mm_s", [0.0, -1.0, float("nan"), float("inf")])
def test_motion_controller_rejects_invalid_homing_speed(speed_mm_s):
    profile = MachineProfile(
        key=AvailableMachineSetups.CUSTOM,
        label="Custom",
        mechanical_setup=MechanicalSetup(mm_per_revolution=4.0),
        limit_switches=LimitSwitchPair(
            up_pin=11, down_pin=12, up_nc=True, down_nc=True
        ),
    )
    driver = FakeDriver()
    controller = MotionController(driver, profile, gpio=FakeGPIO())

    with pytest.raises(ValueError, match="speed_mm_s must be finite and positive"):
        controller.home(speed_mm_s)

    assert driver.last_home is None


def test_gpio_homing_fault_stops_motor():
    profile = MachineProfile(
        key=AvailableMachineSetups.CUSTOM,
        label="Custom",
        mechanical_setup=MechanicalSetup(mm_per_revolution=4.0),
        limit_switches=LimitSwitchPair(up_pin=11, down_pin=12),
    )

    class FaultingHomingDriver(FakeDriver):
        def do_limit_switch_homing(self, *_args, **_kwargs):
            raise RuntimeError("GPIO homing failed")

    driver = FaultingHomingDriver()
    controller = MotionController(driver, profile, gpio=FakeGPIO())

    with pytest.raises(RuntimeError, match="GPIO homing failed"):
        controller.home(1.0)

    assert driver.stopped is True


@pytest.mark.asyncio
async def test_gpio_homing_cancellation_stops_worker_motion():
    profile = MachineProfile(
        key=AvailableMachineSetups.CUSTOM,
        label="Custom",
        mechanical_setup=MechanicalSetup(mm_per_revolution=4.0),
        limit_switches=LimitSwitchPair(up_pin=11, down_pin=12),
    )

    class BlockingHomingDriver(FakeDriver):
        def __init__(self):
            super().__init__()
            self.homing_started = threading.Event()

        def do_limit_switch_homing(self, *_args, **_kwargs):
            self.homing_started.set()
            deadline = time.monotonic() + 1.0
            while not self.stopped and time.monotonic() < deadline:
                time.sleep(0.005)
            return False

    driver = BlockingHomingDriver()
    controller = MotionController(driver, profile, gpio=FakeGPIO())
    homing_task = asyncio.create_task(controller.home_async(1.0))
    await asyncio.to_thread(driver.homing_started.wait, 0.5)

    homing_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await homing_task

    assert driver.stopped is True


@pytest.mark.asyncio
async def test_motion_controller_times_out_wait_and_stops_motor():
    profile = MachineProfile(
        key=AvailableMachineSetups.CUSTOM,
        label="Custom",
        mechanical_setup=MechanicalSetup(mm_per_revolution=4.0),
    )

    class NeverDoneDriver(FakeDriver):
        async def wait_for_motor_done_async(self):
            while True:
                await asyncio.sleep(1)

    driver = NeverDoneDriver()
    session_log = CapturingSessionLog()
    controller = MotionController(driver, profile, session_log=session_log)

    result = await controller.wait_for_motor_done_async(timeout_s=0.02)

    assert driver.stopped is True
    assert driver.disabled is True
    assert result == "motion timed out after 0.02s"
    assert session_log.events == [("motion_timeout", {"timeout_s": 0.02})]


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


def test_motion_controller_disables_opposite_triggered_reference_stop_before_move():
    profile = MachineProfile(
        key=AvailableMachineSetups.CUSTOM,
        label="Custom",
        mechanical_setup=MechanicalSetup(mm_per_revolution=4.0),
        limit_switches=LimitSwitchSetup.tmc5160_reference(),
    )
    driver = FakeReferenceSwitchDriver()
    driver.left_endstop = False
    driver.right_endstop = True
    controller = MotionController(driver, profile, gpio=None)

    controller.move_down(1.0, 0.5)

    assert driver.reference_stop_calls == [(False, True)]
    assert driver.moves == [("down", 1.0, 0.5, None, {})]


@pytest.mark.asyncio
async def test_motion_controller_stops_when_active_reference_switch_triggers():
    profile = MachineProfile(
        key=AvailableMachineSetups.CUSTOM,
        label="Custom",
        mechanical_setup=MechanicalSetup(mm_per_revolution=4.0),
        limit_switches=LimitSwitchSetup.tmc5160_reference(),
    )
    driver = FakeReferenceSwitchDriver()
    session_log = CapturingSessionLog()
    controller = MotionController(driver, profile, gpio=None, session_log=session_log)

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
    assert driver.reference_stop_calls == [(False, True)]
    assert result == "up limit switch triggered"
    assert session_log.events == [
        (
            "limit_switch_stop",
            {"direction": "up", "source": "driver_reference"},
        )
    ]


def test_motion_controller_reenables_reference_stop_after_switch_clears():
    profile = MachineProfile(
        key=AvailableMachineSetups.CUSTOM,
        label="Custom",
        mechanical_setup=MechanicalSetup(mm_per_revolution=4.0),
        limit_switches=LimitSwitchSetup.tmc5160_reference(),
    )
    driver = FakeReferenceSwitchDriver()
    controller = MotionController(driver, profile, gpio=None)

    controller.disable_driver_reference_stop_until_clear(HomeDirection.UP)
    driver.left_endstop = True

    assert controller.read_limit_switch(HomeDirection.UP) is False
    assert driver.reference_stop_calls == [(False, True), (True, True)]


def test_motion_controller_supports_homing_for_driver_reference_switches():
    profile = MachineProfile(
        key=AvailableMachineSetups.CUSTOM,
        label="Custom",
        mechanical_setup=MechanicalSetup(mm_per_revolution=4.0),
        limit_switches=LimitSwitchSetup.tmc5160_reference(),
        home_direction=HomeDirection.UP,
    )
    driver = FakeReferenceSwitchDriver()
    controller = MotionController(driver, profile, gpio=None)

    assert controller.supports_homing is True


def test_motion_controller_homes_via_driver_reference_switch_up():
    profile = MachineProfile(
        key=AvailableMachineSetups.CUSTOM,
        label="Custom",
        mechanical_setup=MechanicalSetup(mm_per_revolution=4.0),
        limit_switches=LimitSwitchSetup.tmc5160_reference(),
        home_direction=HomeDirection.UP,
        homing_max_distance_mm=80.0,
    )
    driver = HomingReferenceSwitchDriver(HomeDirection.UP)
    controller = MotionController(driver, profile, gpio=None)

    homing_found = controller.home(2.0)

    assert homing_found is True
    assert driver.homed is True
    # First move is the homing approach upward; second is the back-off downward.
    assert driver.moves[0][0] == "up"
    assert driver.moves[0][1] == 80.0
    assert driver.moves[-1][0] == "down"
    assert driver.moves[-1][1] == 5.0
    assert driver.stopped is True


def test_motion_controller_homes_via_driver_reference_switch_down():
    profile = MachineProfile(
        key=AvailableMachineSetups.CUSTOM,
        label="Custom",
        mechanical_setup=MechanicalSetup(mm_per_revolution=4.0),
        limit_switches=LimitSwitchSetup.tmc5160_reference(),
        home_direction=HomeDirection.DOWN,
        homing_max_distance_mm=50.0,
    )
    driver = HomingReferenceSwitchDriver(HomeDirection.DOWN)
    controller = MotionController(driver, profile, gpio=None)

    homing_found = controller.home(1.0)

    assert homing_found is True
    assert driver.homed is True
    assert driver.moves[0][0] == "down"
    assert driver.moves[0][1] == 50.0
    assert driver.moves[-1][0] == "up"
    assert driver.moves[-1][1] == 5.0


def test_reference_homing_stops_motor_when_switch_read_fails():
    profile = MachineProfile(
        key=AvailableMachineSetups.CUSTOM,
        label="Custom",
        mechanical_setup=MechanicalSetup(mm_per_revolution=4.0),
        limit_switches=LimitSwitchSetup.tmc5160_reference(),
        home_direction=HomeDirection.UP,
    )

    class FaultingSwitchDriver(FakeReferenceSwitchDriver):
        def __init__(self):
            super().__init__()
            self.left_endstop = True
            self.right_endstop = True
            self.left_reads = 0

        def get_left_endstop(self):
            self.left_reads += 1
            if self.left_reads > 1:
                raise RuntimeError("reference input failed")
            return self.left_endstop

    driver = FaultingSwitchDriver()
    controller = MotionController(driver, profile)

    with pytest.raises(RuntimeError, match="reference input failed"):
        controller.home(2.0)

    assert driver.moves
    assert driver.stopped is True
    assert driver.homed is False


@pytest.mark.asyncio
async def test_reference_homing_cancellation_stops_initial_backoff():
    profile = MachineProfile(
        key=AvailableMachineSetups.CUSTOM,
        label="Custom",
        mechanical_setup=MechanicalSetup(mm_per_revolution=4.0),
        limit_switches=LimitSwitchSetup.tmc5160_reference(),
        home_direction=HomeDirection.UP,
    )

    class StuckBackoffDriver(FakeReferenceSwitchDriver):
        def __init__(self):
            super().__init__()
            self.left_endstop = False
            self.right_endstop = True

    driver = StuckBackoffDriver()
    controller = MotionController(driver, profile)
    homing_task = asyncio.create_task(controller.home_async(2.0))
    await asyncio.sleep(0.02)

    homing_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await homing_task

    assert driver.moves[0][0] == "down"
    assert driver.stopped is True
    assert driver.homed is False


@pytest.mark.asyncio
async def test_reference_homing_initial_backoff_has_a_motion_timeout(monkeypatch):
    profile = MachineProfile(
        key=AvailableMachineSetups.CUSTOM,
        label="Custom",
        mechanical_setup=MechanicalSetup(mm_per_revolution=4.0),
        limit_switches=LimitSwitchSetup.tmc5160_reference(),
        home_direction=HomeDirection.UP,
    )
    driver = FakeReferenceSwitchDriver()
    driver.left_endstop = False
    driver.right_endstop = True
    controller = MotionController(driver, profile)
    monkeypatch.setattr(
        controller,
        "_estimate_motion_timeout_s",
        lambda *_args: 0.01,
    )

    with pytest.raises(TimeoutError, match="homing backoff timed out"):
        await asyncio.wait_for(controller.home_async(2.0), timeout=0.2)

    assert driver.stopped is True
    assert driver.disabled is True
    assert driver.homed is False


@pytest.mark.asyncio
async def test_reference_homing_final_backoff_timeout_invalidates_home(monkeypatch):
    profile = MachineProfile(
        key=AvailableMachineSetups.CUSTOM,
        label="Custom",
        mechanical_setup=MechanicalSetup(mm_per_revolution=4.0),
        limit_switches=LimitSwitchSetup.tmc5160_reference(),
        home_direction=HomeDirection.UP,
        homing_max_distance_mm=40.0,
    )
    driver = HomingReferenceSwitchDriver(HomeDirection.UP)
    controller = MotionController(driver, profile)
    monkeypatch.setattr(
        controller,
        "_estimate_motion_timeout_s",
        lambda *_args: 0.01,
    )

    with pytest.raises(TimeoutError, match="homing backoff timed out"):
        await asyncio.wait_for(controller.home_async(2.0), timeout=0.2)

    assert driver.stopped is True
    assert driver.disabled is True
    assert driver.homed is False


def test_reference_homing_final_backoff_fault_invalidates_home():
    profile = MachineProfile(
        key=AvailableMachineSetups.CUSTOM,
        label="Custom",
        mechanical_setup=MechanicalSetup(mm_per_revolution=4.0),
        limit_switches=LimitSwitchSetup.tmc5160_reference(),
        home_direction=HomeDirection.UP,
        homing_max_distance_mm=40.0,
    )

    class FaultingFinalBackoffDriver(HomingReferenceSwitchDriver):
        def wait_for_motor_done(self):
            raise RuntimeError("final backoff failed")

    driver = FaultingFinalBackoffDriver(HomeDirection.UP)
    controller = MotionController(driver, profile)

    with pytest.raises(RuntimeError, match="final backoff failed"):
        controller.home(2.0)

    assert driver.stopped is True
    assert driver.homed is False


def test_motion_controller_refuses_homing_when_opposite_switch_is_triggered():
    profile = MachineProfile(
        key=AvailableMachineSetups.CUSTOM,
        label="Custom",
        mechanical_setup=MechanicalSetup(mm_per_revolution=4.0),
        limit_switches=LimitSwitchSetup.tmc5160_reference(),
        home_direction=HomeDirection.UP,
    )
    driver = HomingReferenceSwitchDriver(HomeDirection.UP)
    driver.right_endstop = False  # active-low: pressed
    controller = MotionController(driver, profile, gpio=None)

    with pytest.raises(ValueError, match="opposite"):
        controller.home(1.0)
    assert driver.homed is False


def test_failed_rehome_invalidates_previous_home_reference():
    profile = MachineProfile(
        key=AvailableMachineSetups.CUSTOM,
        label="Custom",
        mechanical_setup=MechanicalSetup(mm_per_revolution=4.0),
        limit_switches=LimitSwitchSetup.tmc5160_reference(),
        home_direction=HomeDirection.UP,
    )
    driver = FakeReferenceSwitchDriver()
    driver.homed = True
    driver.left_endstop = True
    driver.right_endstop = False
    controller = MotionController(driver, profile)

    with pytest.raises(ValueError, match="opposite"):
        controller.home(1.0)

    assert driver.cleared_homing is True
    assert driver.homed is False
    assert driver.moves == []


def test_invalid_homing_direction_preserves_existing_home_reference():
    profile = MachineProfile(
        key=AvailableMachineSetups.CUSTOM,
        label="Custom",
        mechanical_setup=MechanicalSetup(mm_per_revolution=4.0),
        limit_switches=LimitSwitchSetup.tmc5160_reference(),
    )
    driver = FakeReferenceSwitchDriver()
    driver.homed = True
    controller = MotionController(driver, profile)

    with pytest.raises(ValueError, match="HomeDirection"):
        controller.home(1.0, home_direction="up")

    assert driver.cleared_homing is False
    assert driver.homed is True
    assert driver.moves == []


def test_limit_switch_selection_requires_direction_enum():
    switches = LimitSwitchSetup.tmc5160_reference()

    with pytest.raises(ValueError, match="HomeDirection"):
        switches.switch_for("up")


def test_motion_controller_backs_off_home_switch_before_homing():
    profile = MachineProfile(
        key=AvailableMachineSetups.CUSTOM,
        label="Custom",
        mechanical_setup=MechanicalSetup(mm_per_revolution=4.0),
        limit_switches=LimitSwitchSetup.tmc5160_reference(),
        home_direction=HomeDirection.UP,
        homing_max_distance_mm=40.0,
    )

    class StartOnSwitchDriver(HomingReferenceSwitchDriver):
        def _after_move(self, direction):
            if direction == HomeDirection.DOWN and not self.left_endstop:
                # Initial back-off releases the home switch (active-low → True = open).
                self.left_endstop = True
                return
            super()._after_move(direction)

    driver = StartOnSwitchDriver(HomeDirection.UP)
    driver.left_endstop = False  # active-low: home switch initially pressed
    controller = MotionController(driver, profile, gpio=None)

    homing_found = controller.home(1.0)

    assert homing_found is True
    assert driver.homed is True
    # Sequence: down (initial back-off) -> up (approach) -> down (final back-off).
    directions = [move[0] for move in driver.moves]
    assert directions == ["down", "up", "down"]


@pytest.mark.asyncio
async def test_motion_controller_home_async_can_be_cancelled():
    profile = MachineProfile(
        key=AvailableMachineSetups.CUSTOM,
        label="Custom",
        mechanical_setup=MechanicalSetup(mm_per_revolution=4.0),
        limit_switches=LimitSwitchSetup.tmc5160_reference(),
        home_direction=HomeDirection.UP,
        homing_max_distance_mm=80.0,
    )

    class NeverHittingDriver(FakeReferenceSwitchDriver):
        def __init__(self):
            super().__init__()
            self.left_endstop = True
            self.right_endstop = True

        async def wait_for_motor_done_async(self):
            return None

    driver = NeverHittingDriver()
    controller = MotionController(driver, profile, gpio=None)

    homing_task = asyncio.create_task(controller.home_async(2.0))
    await asyncio.sleep(0.05)
    assert not homing_task.done()
    homing_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await homing_task
    assert driver.stopped is True
    assert driver.homed is False


@pytest.mark.asyncio
async def test_motion_controller_simulates_endstop_hit_in_dummy_mode():
    profile = MachineProfile(
        key=AvailableMachineSetups.CUSTOM,
        label="Custom",
        mechanical_setup=MechanicalSetup(mm_per_revolution=4.0),
        limit_switches=LimitSwitchSetup.tmc5160_reference(),
        home_direction=HomeDirection.UP,
        homing_max_distance_mm=80.0,
    )

    class DummyDriver(FakeReferenceSwitchDriver):
        is_dummy = True

        def __init__(self):
            super().__init__()
            self.left_endstop = True
            self.right_endstop = True

        def simulate_dummy_endstops(self, *, left=None, right=None):
            if left is not None:
                self.left_endstop = left
            if right is not None:
                self.right_endstop = right

        async def wait_for_motor_done_async(self):
            return None

    driver = DummyDriver()
    controller = MotionController(driver, profile, gpio=None)

    homing_found = await asyncio.wait_for(controller.home_async(2.0), timeout=2.0)

    assert homing_found is True
    assert driver.homed is True
    assert driver.left_endstop is True  # released after homing
    assert driver.right_endstop is True


def test_large_profile_uses_landungsbruecke_reference_switches():
    profile = get_machine_profile(AvailableMachineSetups.LARGE_COATER)

    assert profile.requires_gpio is False
    assert profile.limit_switches.up.source == LimitSwitchSource.DRIVER_REFERENCE
    assert profile.limit_switches.down.source == LimitSwitchSource.DRIVER_REFERENCE
    assert profile.limit_switches.up.polarity == LimitSwitchPolarity.ACTIVE_LOW
    assert profile.limit_switches.down.polarity == LimitSwitchPolarity.ACTIVE_LOW


def test_motion_controller_cleanup_stops_disables_and_is_idempotent():
    profile = get_machine_profile(AvailableMachineSetups.SMALL_COATER)
    driver = FakeDriver()
    gpio = FakeGPIO()
    session_log = CapturingSessionLog()
    controller = MotionController(driver, profile, gpio=gpio, session_log=session_log)

    controller.cleanup()
    controller.cleanup()

    assert driver.shutdown_calls == ["stop", "disable", "cleanup"]
    assert gpio.cleaned is True
    assert [event for event, _fields in session_log.events] == ["session_cleanup"]


def test_motion_controller_cleanup_attempts_all_safety_steps_after_stop_error():
    class StopFailingDriver(FakeDriver):
        def stop_motor(self):
            super().stop_motor()
            raise RuntimeError("stop failed")

    profile = get_machine_profile(AvailableMachineSetups.SMALL_COATER)
    driver = StopFailingDriver()
    gpio = FakeGPIO()
    controller = MotionController(driver, profile, gpio=gpio)

    with pytest.raises(RuntimeError, match="stop failed"):
        controller.cleanup()

    assert driver.shutdown_calls == ["stop", "disable", "cleanup"]
    assert gpio.cleaned is True
