import asyncio
from collections.abc import Callable

from dip_coater.gpio import GpioEdge, GpioMode, GpioPUD, GpioState
from dip_coater.setup_profiles.machine_profile import (
    HomeDirection,
    LimitSwitchSource,
    MachineProfile,
)


class MotionController:
    def __init__(self, motor_driver, machine_profile: MachineProfile, gpio=None):
        self.motor_driver = motor_driver
        self.machine_profile = machine_profile
        self.gpio = gpio
        self._disabled_driver_reference_stops: set[HomeDirection] = set()

    @property
    def supports_limit_switches(self) -> bool:
        return self.supports_gpio_limit_switches or self.supports_driver_reference_switches

    @property
    def supports_gpio_limit_switches(self) -> bool:
        switches = self.machine_profile.limit_switches
        return switches is not None and switches.uses_gpio and self.gpio is not None

    @property
    def supports_driver_reference_switches(self) -> bool:
        switches = self.machine_profile.limit_switches
        return (
            switches is not None
            and switches.uses_driver_reference
            and hasattr(self.motor_driver, "get_left_endstop")
            and hasattr(self.motor_driver, "get_right_endstop")
        )

    @property
    def supports_homing(self) -> bool:
        return self.supports_gpio_limit_switches and hasattr(
            self.motor_driver, "do_limit_switch_homing"
        )

    def enable_motor(self):
        self.motor_driver.enable_motor()

    def disable_motor(self):
        self.motor_driver.disable_motor()

    def stop_motor(self):
        self.motor_driver.stop_motor()

    def wait_for_motor_done(self):
        return self.motor_driver.wait_for_motor_done()

    async def wait_for_motor_done_async(
        self,
        active_limit_direction: HomeDirection | None = None,
    ):
        if active_limit_direction is None or not self.supports_limit_switches:
            return await self.motor_driver.wait_for_motor_done_async()

        wait_task = asyncio.create_task(self.motor_driver.wait_for_motor_done_async())
        try:
            while not wait_task.done():
                if self.read_limit_switch(active_limit_direction):
                    self.stop_motor()
                    self.disable_driver_reference_stop_until_clear(
                        active_limit_direction
                    )
                    wait_task.cancel()
                    try:
                        await wait_task
                    except asyncio.CancelledError:
                        pass
                    return f"{active_limit_direction.value} limit switch triggered"
                await asyncio.sleep(0.05)
            return await wait_task
        finally:
            if not wait_task.done():
                wait_task.cancel()

    def move_up(
        self,
        distance_mm: float,
        speed_mm_s: float,
        acceleration_mm_s2: float | None = None,
    ):
        self._raise_if_limit_switch_triggered(HomeDirection.UP)
        self._disable_opposite_triggered_driver_reference_stop(HomeDirection.UP)
        kwargs = {}
        switch = self._switch_for_direction(HomeDirection.UP)
        if switch is not None and switch.source == LimitSwitchSource.GPIO:
            kwargs["limit_switch_pins"] = [switch.pin]
        self.motor_driver.move_up(distance_mm, speed_mm_s, acceleration_mm_s2, **kwargs)

    def move_down(
        self,
        distance_mm: float,
        speed_mm_s: float,
        acceleration_mm_s2: float | None = None,
    ):
        self._raise_if_limit_switch_triggered(HomeDirection.DOWN)
        self._disable_opposite_triggered_driver_reference_stop(HomeDirection.DOWN)
        kwargs = {}
        switch = self._switch_for_direction(HomeDirection.DOWN)
        if switch is not None and switch.source == LimitSwitchSource.GPIO:
            kwargs["limit_switch_pins"] = [switch.pin]
        self.motor_driver.move_down(
            distance_mm, speed_mm_s, acceleration_mm_s2, **kwargs
        )

    def move_to_position(
        self,
        position_mm: float,
        speed_mm_s: float | None = None,
        acceleration_mm_s2: float | None = None,
    ):
        try:
            self.motor_driver.run_to_position(
                position_mm,
                speed_mm_s,
                acceleration_mm_s2,
                self.machine_profile.homes_up,
            )
        except TypeError:
            self.motor_driver.run_to_position(
                position_mm, speed_mm_s, acceleration_mm_s2
            )

    def home(
        self,
        speed_mm_s: float,
        *,
        home_direction: HomeDirection | None = None,
    ) -> bool:
        if not self.supports_homing:
            raise ValueError(
                "The current driver/setup combination does not support homing."
            )
        if home_direction is None:
            home_direction = self.machine_profile.home_direction
        distance = (
            self.machine_profile.homing_max_distance_mm
            if home_direction == HomeDirection.UP
            else -self.machine_profile.homing_max_distance_mm
        )
        switches = self.machine_profile.limit_switches
        return self.motor_driver.do_limit_switch_homing(
            switches.up_pin,
            switches.down_pin,
            distance,
            speed_mm_s,
            switches.up_nc,
            switches.down_nc,
        )

    def get_current_position_mm(self):
        try:
            return self.motor_driver.get_current_position_mm(
                self.machine_profile.homes_up
            )
        except TypeError:
            return self.motor_driver.get_current_position_mm()

    def is_homing_found(self) -> bool:
        return self.motor_driver.is_homing_found()

    def cleanup(self):
        self.motor_driver.cleanup()
        if (
            self.gpio is not None
            and getattr(self.motor_driver, "GPIO", None) is not self.gpio
        ):
            self.gpio.cleanup()

    def setup_limit_switches_io(self):
        if not self.supports_gpio_limit_switches:
            return
        switches = self.machine_profile.limit_switches
        for switch in (switches.up, switches.down):
            if switch.source == LimitSwitchSource.GPIO:
                self._setup_limit_switch_io(switch.pin)

    def _setup_limit_switch_io(self, pin: int):
        self.gpio.setup(pin, GpioMode.IN, pull_up_down=GpioPUD.PUD_UP)

    def bind_limit_switches_to_motor(self):
        if not self.supports_gpio_limit_switches or not hasattr(
            self.motor_driver, "bind_limit_switch"
        ):
            return
        switches = self.machine_profile.limit_switches
        if switches.up.source == LimitSwitchSource.GPIO:
            self.motor_driver.bind_limit_switch(switches.up_pin, NC=switches.up_nc)
        if switches.down.source == LimitSwitchSource.GPIO:
            self.motor_driver.bind_limit_switch(
                switches.down_pin, NC=switches.down_nc
            )

    def bind_limit_switch_callback(
        self,
        *,
        direction: HomeDirection,
        callback: Callable,
        bouncetime=None,
    ):
        switch = self._switch_for_direction(direction)
        if (
            not self.supports_gpio_limit_switches
            or switch is None
            or switch.source != LimitSwitchSource.GPIO
        ):
            return
        pin = switch.pin
        self.gpio.remove_event_detect(pin)
        self.gpio.add_event_detect(
            pin, GpioEdge.BOTH, callback=callback, bouncetime=bouncetime
        )

    def read_limit_switch(self, direction: HomeDirection) -> bool:
        switch = self._switch_for_direction(direction)
        if switch is None:
            return False
        if switch.source == LimitSwitchSource.DRIVER_REFERENCE:
            if not self.supports_driver_reference_switches:
                return False
            raw_state = (
                self.motor_driver.get_left_endstop()
                if direction == HomeDirection.UP
                else self.motor_driver.get_right_endstop()
            )
            triggered = switch.is_triggered(raw_state)
            if not triggered:
                self._reenable_driver_reference_stop(direction)
            return triggered
        if switch.source == LimitSwitchSource.GPIO:
            if not self.supports_gpio_limit_switches:
                return False
            return switch.is_triggered(self.gpio.input(switch.pin) == GpioState.HIGH)
        return False

    def disable_driver_reference_stop_until_clear(
        self, direction: HomeDirection
    ) -> None:
        switch = self._switch_for_direction(direction)
        if (
            switch is None
            or switch.source != LimitSwitchSource.DRIVER_REFERENCE
            or not self.supports_driver_reference_switches
            or not hasattr(self.motor_driver, "enable_reference_stops")
        ):
            return
        self._disabled_driver_reference_stops.add(direction)
        self._apply_driver_reference_stop_state()

    def _switch_for_direction(self, direction: HomeDirection):
        switches = self.machine_profile.limit_switches
        if switches is None:
            return None
        return switches.switch_for(direction)

    def _reenable_driver_reference_stop(self, direction: HomeDirection) -> None:
        if direction not in self._disabled_driver_reference_stops:
            return
        self._disabled_driver_reference_stops.remove(direction)
        self._apply_driver_reference_stop_state()

    def _disable_opposite_triggered_driver_reference_stop(
        self, direction: HomeDirection
    ) -> None:
        opposite_direction = (
            HomeDirection.DOWN if direction == HomeDirection.UP else HomeDirection.UP
        )
        switch = self._switch_for_direction(opposite_direction)
        if switch is None or switch.source != LimitSwitchSource.DRIVER_REFERENCE:
            return
        if self.read_limit_switch(opposite_direction):
            self.disable_driver_reference_stop_until_clear(opposite_direction)

    def _apply_driver_reference_stop_state(self) -> None:
        if not hasattr(self.motor_driver, "enable_reference_stops"):
            return
        self.motor_driver.enable_reference_stops(
            left=HomeDirection.UP not in self._disabled_driver_reference_stops,
            right=HomeDirection.DOWN not in self._disabled_driver_reference_stops,
        )

    def _raise_if_limit_switch_triggered(self, direction: HomeDirection) -> None:
        if not self.supports_limit_switches:
            return
        if not self.read_limit_switch(direction):
            return
        raise ValueError(
            f"Cannot move {direction.value}: "
            f"{direction.value} limit switch is triggered."
        )
