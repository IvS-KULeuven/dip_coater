from collections.abc import Callable

from dip_coater.gpio import GpioEdge, GpioMode, GpioPUD, GpioState
from dip_coater.setup_profiles.machine_profile import HomeDirection, MachineProfile


class MotionController:
    def __init__(self, motor_driver, machine_profile: MachineProfile, gpio=None):
        self.motor_driver = motor_driver
        self.machine_profile = machine_profile
        self.gpio = gpio

    @property
    def supports_limit_switches(self) -> bool:
        return self.machine_profile.supports_limit_switches and self.gpio is not None

    @property
    def supports_homing(self) -> bool:
        return self.supports_limit_switches and hasattr(
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

    async def wait_for_motor_done_async(self):
        return await self.motor_driver.wait_for_motor_done_async()

    def move_up(
        self,
        distance_mm: float,
        speed_mm_s: float,
        acceleration_mm_s2: float | None = None,
    ):
        kwargs = {}
        if self.supports_limit_switches:
            kwargs["limit_switch_pins"] = [self.machine_profile.limit_switches.up_pin]
        self.motor_driver.move_up(distance_mm, speed_mm_s, acceleration_mm_s2, **kwargs)

    def move_down(
        self,
        distance_mm: float,
        speed_mm_s: float,
        acceleration_mm_s2: float | None = None,
    ):
        kwargs = {}
        if self.supports_limit_switches:
            kwargs["limit_switch_pins"] = [self.machine_profile.limit_switches.down_pin]
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
        if not self.supports_limit_switches:
            return
        switches = self.machine_profile.limit_switches
        self._setup_limit_switch_io(switches.up_pin)
        self._setup_limit_switch_io(switches.down_pin)

    def _setup_limit_switch_io(self, pin: int):
        self.gpio.setup(pin, GpioMode.IN, pull_up_down=GpioPUD.PUD_UP)

    def bind_limit_switches_to_motor(self):
        if not self.supports_limit_switches or not hasattr(
            self.motor_driver, "bind_limit_switch"
        ):
            return
        switches = self.machine_profile.limit_switches
        self.motor_driver.bind_limit_switch(switches.up_pin, NC=switches.up_nc)
        self.motor_driver.bind_limit_switch(switches.down_pin, NC=switches.down_nc)

    def bind_limit_switch_callback(
        self,
        *,
        direction: HomeDirection,
        callback: Callable,
        bouncetime=None,
    ):
        if not self.supports_limit_switches:
            return
        pin = self._pin_for_direction(direction)
        self.gpio.remove_event_detect(pin)
        self.gpio.add_event_detect(
            pin, GpioEdge.BOTH, callback=callback, bouncetime=bouncetime
        )

    def read_limit_switch(self, direction: HomeDirection) -> bool:
        if not self.supports_limit_switches:
            return False
        pin = self._pin_for_direction(direction)
        normally_closed = self._is_normally_closed(direction)
        value = self.gpio.input(pin)
        return value == GpioState.HIGH if normally_closed else value == GpioState.LOW

    def _pin_for_direction(self, direction: HomeDirection) -> int:
        switches = self.machine_profile.limit_switches
        return switches.up_pin if direction == HomeDirection.UP else switches.down_pin

    def _is_normally_closed(self, direction: HomeDirection) -> bool:
        switches = self.machine_profile.limit_switches
        return switches.up_nc if direction == HomeDirection.UP else switches.down_nc
