import asyncio
import time
from collections.abc import Callable

from dip_coater.gpio import GpioEdge, GpioMode, GpioPUD, GpioState
from dip_coater.logging.session_log import NullSessionLog
from dip_coater.setup_profiles.machine_profile import (
    HomeDirection,
    LimitSwitchSource,
    MachineProfile,
)


_REFERENCE_HOMING_BACKOFF_MM = 5.0
_MOTION_TIMEOUT_MIN_S = 10.0
_MOTION_TIMEOUT_SETTLE_S = 5.0
_MOTION_TIMEOUT_SCALE = 3.0


class MotionController:
    """Coordinate motor-driver motion, homing, limits, and session logging.

    This class is the main Python API for moving a configured dip-coater lift.
    It keeps machine-profile safety rules separate from concrete motor-driver
    implementations.
    """

    def __init__(
        self,
        motor_driver,
        machine_profile: MachineProfile,
        gpio=None,
        session_log=None,
    ):
        """Create a motion controller for one motor driver and machine profile.

        :param motor_driver: Driver object implementing the dip-coater motor API.
        :param machine_profile: Machine profile that defines mechanics and limits.
        :param gpio: Optional GPIO adapter used for GPIO-backed limit switches.
        :param session_log: Optional session log writer.
        """
        self.motor_driver = motor_driver
        self.machine_profile = machine_profile
        self.gpio = gpio
        self.session_log = session_log or NullSessionLog()
        self._disabled_driver_reference_stops: set[HomeDirection] = set()
        self._last_motion_timeout_s: float | None = None

    @property
    def supports_limit_switches(self) -> bool:
        """Report whether any configured limit-switch source is usable.

        :return: ``True`` when GPIO or driver-reference switches are available.
        """
        return self.supports_gpio_limit_switches or self.supports_driver_reference_switches

    @property
    def supports_gpio_limit_switches(self) -> bool:
        """Report whether GPIO-backed limit switches are configured and usable.

        :return: ``True`` when GPIO limit switches can be read.
        """
        switches = self.machine_profile.limit_switches
        return switches is not None and switches.uses_gpio and self.gpio is not None

    @property
    def supports_driver_reference_switches(self) -> bool:
        """Report whether driver-reference limit switches are configured and usable.

        :return: ``True`` when the driver exposes reference-switch reads.
        """
        switches = self.machine_profile.limit_switches
        return (
            switches is not None
            and switches.uses_driver_reference
            and hasattr(self.motor_driver, "get_left_endstop")
            and hasattr(self.motor_driver, "get_right_endstop")
        )

    @property
    def supports_homing(self) -> bool:
        """Report whether this driver/setup pair supports homing.

        :return: ``True`` when a supported homing method is available.
        """
        if self.supports_gpio_limit_switches and hasattr(
            self.motor_driver, "do_limit_switch_homing"
        ):
            return True
        if self.supports_driver_reference_switches and hasattr(
            self.motor_driver, "mark_homed"
        ):
            return True
        return False

    def enable_motor(self):
        """Enable the motor through the underlying driver."""
        self.motor_driver.enable_motor()

    def disable_motor(self):
        """Disable the motor through the underlying driver."""
        self.motor_driver.disable_motor()

    def stop_motor(self):
        """Request an immediate stop through the underlying driver."""
        self.motor_driver.stop_motor()

    def wait_for_motor_done(self):
        """Block until the active motor command is complete.

        :return: Driver-specific completion result.
        """
        result = self.motor_driver.wait_for_motor_done()
        self._record_motion_completed(result)
        return result

    async def wait_for_motor_done_async(
        self,
        active_limit_direction: HomeDirection | None = None,
        timeout_s: float | None = None,
    ):
        """Wait asynchronously for motion completion, timeout, or a limit switch.

        :param active_limit_direction: Direction whose limit switch should stop the move.
        :param timeout_s: Optional timeout in seconds, or ``None`` to use the last motion estimate.
        :return: Driver-specific completion result or a status string.
        """
        timeout_s = self._last_motion_timeout_s if timeout_s is None else timeout_s
        if active_limit_direction is None or not self.supports_limit_switches:
            return await self._wait_for_driver_done_with_timeout(timeout_s)

        wait_task = asyncio.create_task(self.motor_driver.wait_for_motor_done_async())
        try:
            loop = asyncio.get_running_loop()
            deadline = None if timeout_s is None else loop.time() + timeout_s
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
                    self._record_limit_switch_stop(active_limit_direction)
                    return f"{active_limit_direction.value} limit switch triggered"
                if deadline is not None and loop.time() >= deadline:
                    return await self._timeout_wait_task(wait_task, timeout_s)
                await asyncio.sleep(0.05)
            result = await wait_task
            self._record_motion_completed(result)
            return result
        finally:
            if not wait_task.done():
                wait_task.cancel()

    async def _wait_for_driver_done_with_timeout(self, timeout_s: float | None):
        if timeout_s is None:
            result = await self.motor_driver.wait_for_motor_done_async()
            self._record_motion_completed(result)
            return result
        wait_task = asyncio.create_task(self.motor_driver.wait_for_motor_done_async())
        try:
            result = await asyncio.wait_for(wait_task, timeout=timeout_s)
            self._record_motion_completed(result)
            return result
        except asyncio.TimeoutError:
            return await self._timeout_wait_task(wait_task, timeout_s)

    async def _timeout_wait_task(self, wait_task: asyncio.Task, timeout_s: float) -> str:
        self.stop_motor()
        self.session_log.write("motion_timeout", timeout_s=timeout_s)
        wait_task.cancel()
        try:
            await wait_task
        except asyncio.CancelledError:
            pass
        return f"motion timed out after {timeout_s:g}s"

    def move_up(
        self,
        distance_mm: float,
        speed_mm_s: float,
        acceleration_mm_s2: float | None = None,
    ):
        """Move the lift upward by a relative distance.

        :param distance_mm: Relative distance in millimeters.
        :param speed_mm_s: Speed in millimeters per second.
        :param acceleration_mm_s2: Optional acceleration in millimeters per second squared.
        """
        self._raise_if_limit_switch_triggered(HomeDirection.UP)
        self._raise_if_relative_move_outside_travel(HomeDirection.UP, distance_mm)
        self._last_motion_timeout_s = self._estimate_motion_timeout_s(
            distance_mm, speed_mm_s
        )
        self.session_log.write(
            "motion_requested",
            kind="relative",
            direction=HomeDirection.UP.value,
            distance_mm=distance_mm,
            speed_mm_s=speed_mm_s,
            acceleration_mm_s2=acceleration_mm_s2,
            timeout_s=self._last_motion_timeout_s,
        )
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
        """Move the lift downward by a relative distance.

        :param distance_mm: Relative distance in millimeters.
        :param speed_mm_s: Speed in millimeters per second.
        :param acceleration_mm_s2: Optional acceleration in millimeters per second squared.
        """
        self._raise_if_limit_switch_triggered(HomeDirection.DOWN)
        self._raise_if_relative_move_outside_travel(HomeDirection.DOWN, distance_mm)
        self._last_motion_timeout_s = self._estimate_motion_timeout_s(
            distance_mm, speed_mm_s
        )
        self.session_log.write(
            "motion_requested",
            kind="relative",
            direction=HomeDirection.DOWN.value,
            distance_mm=distance_mm,
            speed_mm_s=speed_mm_s,
            acceleration_mm_s2=acceleration_mm_s2,
            timeout_s=self._last_motion_timeout_s,
        )
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
        """Move the lift to an absolute position in the homed coordinate system.

        :param position_mm: Target absolute position in millimeters.
        :param speed_mm_s: Optional speed in millimeters per second.
        :param acceleration_mm_s2: Optional acceleration in millimeters per second squared.
        """
        self._raise_if_position_outside_travel(position_mm)
        current_position_mm = self.get_current_position_mm()
        travel_distance_mm = (
            self.machine_profile.travel_span_mm
            if current_position_mm is None
            else abs(position_mm - current_position_mm)
        )
        self._last_motion_timeout_s = self._estimate_motion_timeout_s(
            travel_distance_mm, speed_mm_s
        )
        self.session_log.write(
            "motion_requested",
            kind="absolute",
            position_mm=position_mm,
            travel_distance_mm=travel_distance_mm,
            speed_mm_s=speed_mm_s,
            acceleration_mm_s2=acceleration_mm_s2,
            timeout_s=self._last_motion_timeout_s,
        )
        self.motor_driver.run_to_position(
            position_mm,
            speed_mm_s,
            acceleration_mm_s2,
            self.machine_profile.homes_up,
        )

    def home(
        self,
        speed_mm_s: float,
        *,
        home_direction: HomeDirection | None = None,
    ) -> bool:
        """Run a blocking homing sequence.

        :param speed_mm_s: Homing speed in millimeters per second.
        :param home_direction: Direction to home toward, or ``None`` to use the profile default.
        :return: ``True`` when the home reference was found.
        """
        if not self.supports_homing:
            raise ValueError(
                "The current driver/setup combination does not support homing."
            )
        if home_direction is None:
            home_direction = self.machine_profile.home_direction
        self.session_log.write(
            "homing_requested",
            direction=home_direction.value,
            speed_mm_s=speed_mm_s,
        )
        if self.supports_gpio_limit_switches and hasattr(
            self.motor_driver, "do_limit_switch_homing"
        ):
            homing_found = self._home_via_gpio_switches(speed_mm_s, home_direction)
        else:
            homing_found = self._home_via_driver_reference(speed_mm_s, home_direction)
        self.session_log.write(
            "homing_completed",
            direction=home_direction.value,
            speed_mm_s=speed_mm_s,
            homing_found=homing_found,
        )
        return homing_found

    async def home_async(
        self,
        speed_mm_s: float,
        *,
        home_direction: HomeDirection | None = None,
    ) -> bool:
        """Run an asynchronous homing sequence.

        :param speed_mm_s: Homing speed in millimeters per second.
        :param home_direction: Direction to home toward, or ``None`` to use the profile default.
        :return: ``True`` when the home reference was found.
        """
        if not self.supports_homing:
            raise ValueError(
                "The current driver/setup combination does not support homing."
            )
        if home_direction is None:
            home_direction = self.machine_profile.home_direction
        self.session_log.write(
            "homing_requested",
            direction=home_direction.value,
            speed_mm_s=speed_mm_s,
        )
        if self.supports_gpio_limit_switches and hasattr(
            self.motor_driver, "do_limit_switch_homing"
        ):
            homing_found = await asyncio.to_thread(
                self._home_via_gpio_switches, speed_mm_s, home_direction
            )
        else:
            homing_found = await self._home_via_driver_reference_async(
                speed_mm_s, home_direction
            )
        self.session_log.write(
            "homing_completed",
            direction=home_direction.value,
            speed_mm_s=speed_mm_s,
            homing_found=homing_found,
        )
        return homing_found

    def _home_via_gpio_switches(
        self, speed_mm_s: float, home_direction: HomeDirection
    ) -> bool:
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

    def _home_via_driver_reference(
        self, speed_mm_s: float, home_direction: HomeDirection
    ) -> bool:
        opposite_direction = (
            HomeDirection.DOWN if home_direction == HomeDirection.UP else HomeDirection.UP
        )
        if self.read_limit_switch(opposite_direction):
            raise ValueError(
                f"Cannot home {home_direction.value}: opposite "
                f"({opposite_direction.value}) limit switch is triggered."
            )

        backoff_speed = max(speed_mm_s, 1.0)

        if self.read_limit_switch(home_direction):
            self.disable_driver_reference_stop_until_clear(home_direction)
            self._move_motor_in_direction(
                opposite_direction, _REFERENCE_HOMING_BACKOFF_MM, backoff_speed
            )
            self.motor_driver.wait_for_motor_done()
            if self.read_limit_switch(home_direction):
                raise ValueError(
                    "Home switch still triggered after backing off; "
                    "please check the limit switches."
                )

        distance_mm = self.machine_profile.homing_max_distance_mm
        timeout_s = max(60.0, (distance_mm / max(speed_mm_s, 0.1)) * 2.0)
        self._move_motor_in_direction(home_direction, distance_mm, speed_mm_s)

        triggered = False
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            if self.read_limit_switch(home_direction):
                triggered = True
                break
            time.sleep(0.02)
        self.motor_driver.stop_motor()

        if not triggered:
            return False

        self.motor_driver.mark_homed()

        self.disable_driver_reference_stop_until_clear(home_direction)
        self._move_motor_in_direction(
            opposite_direction, _REFERENCE_HOMING_BACKOFF_MM, backoff_speed
        )
        self.motor_driver.wait_for_motor_done()
        return True

    def _move_motor_in_direction(
        self, direction: HomeDirection, distance_mm: float, speed_mm_s: float
    ) -> None:
        if direction == HomeDirection.UP:
            self.motor_driver.move_up(distance_mm, speed_mm_s)
        else:
            self.motor_driver.move_down(distance_mm, speed_mm_s)

    async def _home_via_driver_reference_async(
        self, speed_mm_s: float, home_direction: HomeDirection
    ) -> bool:
        opposite_direction = (
            HomeDirection.DOWN if home_direction == HomeDirection.UP else HomeDirection.UP
        )
        if self.read_limit_switch(opposite_direction):
            raise ValueError(
                f"Cannot home {home_direction.value}: opposite "
                f"({opposite_direction.value}) limit switch is triggered."
            )

        backoff_speed = max(speed_mm_s, 1.0)

        if self.read_limit_switch(home_direction):
            self.disable_driver_reference_stop_until_clear(home_direction)
            self._move_motor_in_direction(
                opposite_direction, _REFERENCE_HOMING_BACKOFF_MM, backoff_speed
            )
            await self.motor_driver.wait_for_motor_done_async()
            if self.read_limit_switch(home_direction):
                raise ValueError(
                    "Home switch still triggered after backing off; "
                    "please check the limit switches."
                )

        distance_mm = self.machine_profile.homing_max_distance_mm
        timeout_s = max(60.0, (distance_mm / max(speed_mm_s, 0.1)) * 2.0)
        self._move_motor_in_direction(home_direction, distance_mm, speed_mm_s)

        dummy_hit_task = self._schedule_dummy_endstop_hit(home_direction)
        try:
            triggered = False
            loop = asyncio.get_event_loop()
            deadline = loop.time() + timeout_s
            try:
                while loop.time() < deadline:
                    if self.read_limit_switch(home_direction):
                        triggered = True
                        break
                    await asyncio.sleep(0.02)
            finally:
                self.motor_driver.stop_motor()
        finally:
            if dummy_hit_task is not None and not dummy_hit_task.done():
                dummy_hit_task.cancel()

        if not triggered:
            return False

        self.motor_driver.mark_homed()
        self._release_dummy_endstops()

        self.disable_driver_reference_stop_until_clear(home_direction)
        self._move_motor_in_direction(
            opposite_direction, _REFERENCE_HOMING_BACKOFF_MM, backoff_speed
        )
        await self.motor_driver.wait_for_motor_done_async()
        return True

    def _schedule_dummy_endstop_hit(
        self, home_direction: HomeDirection
    ) -> asyncio.Task | None:
        if not getattr(self.motor_driver, "is_dummy", False):
            return None
        if not hasattr(self.motor_driver, "simulate_dummy_endstops"):
            return None

        async def trip_after_delay() -> None:
            await asyncio.sleep(0.5)
            polarity_raw_triggered = False  # ACTIVE_LOW reference-switch convention
            if home_direction == HomeDirection.UP:
                self.motor_driver.simulate_dummy_endstops(left=polarity_raw_triggered)
            else:
                self.motor_driver.simulate_dummy_endstops(right=polarity_raw_triggered)

        return asyncio.create_task(trip_after_delay())

    def _release_dummy_endstops(self) -> None:
        if not getattr(self.motor_driver, "is_dummy", False):
            return
        if not hasattr(self.motor_driver, "simulate_dummy_endstops"):
            return
        self.motor_driver.simulate_dummy_endstops(left=True, right=True)

    def get_current_position_mm(self):
        """Return the current absolute lift position.

        :return: Current position in millimeters, or ``None`` when unknown.
        """
        return self.motor_driver.get_current_position_mm(self.machine_profile.homes_up)

    def is_homing_found(self) -> bool:
        """Report whether the lift has a known home reference.

        :return: ``True`` when homing has completed successfully.
        """
        return self.motor_driver.is_homing_found()

    def cleanup(self):
        """Release motor-driver and GPIO resources."""
        self.session_log.write("session_cleanup")
        self.motor_driver.cleanup()
        if (
            self.gpio is not None
            and getattr(self.motor_driver, "GPIO", None) is not self.gpio
        ):
            self.gpio.cleanup()

    def setup_limit_switches_io(self):
        """Configure GPIO input pins for GPIO-backed limit switches."""
        if not self.supports_gpio_limit_switches:
            return
        switches = self.machine_profile.limit_switches
        for switch in (switches.up, switches.down):
            if switch.source == LimitSwitchSource.GPIO:
                self._setup_limit_switch_io(switch.pin)

    def _setup_limit_switch_io(self, pin: int):
        self.gpio.setup(pin, GpioMode.IN, pull_up_down=GpioPUD.PUD_UP)

    def bind_limit_switches_to_motor(self):
        """Bind GPIO limit switches directly to drivers that support callbacks."""
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
        """Bind a callback to a GPIO-backed limit switch.

        :param direction: Direction whose limit switch should be watched.
        :param callback: Callback called by the GPIO adapter.
        :param bouncetime: Optional debounce time passed to the GPIO adapter.
        """
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
        """Read and interpret a configured limit switch.

        :param direction: Direction whose limit switch should be read.
        :return: ``True`` when the switch is triggered.
        """
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
        """Temporarily disable a triggered driver-reference stop.

        :param direction: Direction whose reference stop should be disabled until clear.
        """
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

    def _raise_if_relative_move_outside_travel(
        self, direction: HomeDirection, distance_mm: float
    ) -> None:
        if not self.is_homing_found():
            return
        current_position_mm = self.get_current_position_mm()
        if current_position_mm is None:
            return
        projected_position_mm = current_position_mm + self._position_delta_for_move(
            direction, distance_mm
        )
        self._raise_if_position_outside_travel(projected_position_mm)

    def _position_delta_for_move(
        self, direction: HomeDirection, distance_mm: float
    ) -> float:
        if direction == self.machine_profile.home_direction:
            return -distance_mm
        return distance_mm

    def _raise_if_position_outside_travel(self, position_mm: float) -> None:
        if (
            self.machine_profile.min_position_mm
            <= position_mm
            <= self.machine_profile.max_position_mm
        ):
            return
        raise ValueError(
            f"Requested position {position_mm:.1f} mm is outside travel range "
            f"{self.machine_profile.min_position_mm:.1f}.."
            f"{self.machine_profile.max_position_mm:.1f} mm."
        )

    @staticmethod
    def _estimate_motion_timeout_s(
        distance_mm: float,
        speed_mm_s: float | None,
    ) -> float:
        if speed_mm_s is None or speed_mm_s <= 0:
            return _MOTION_TIMEOUT_MIN_S
        expected_duration_s = abs(distance_mm) / speed_mm_s
        return max(
            _MOTION_TIMEOUT_MIN_S,
            expected_duration_s * _MOTION_TIMEOUT_SCALE + _MOTION_TIMEOUT_SETTLE_S,
        )

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

    def _record_limit_switch_stop(self, direction: HomeDirection) -> None:
        switch = self._switch_for_direction(direction)
        self.session_log.write(
            "limit_switch_stop",
            direction=direction.value,
            source=switch.source.value if switch is not None else None,
        )

    def _record_motion_completed(self, result) -> None:
        self.session_log.write("motion_completed", result=result)

    def _raise_if_limit_switch_triggered(self, direction: HomeDirection) -> None:
        if not self.supports_limit_switches:
            return
        if not self.read_limit_switch(direction):
            return
        raise ValueError(
            f"Cannot move {direction.value}: "
            f"{direction.value} limit switch is triggered."
        )
