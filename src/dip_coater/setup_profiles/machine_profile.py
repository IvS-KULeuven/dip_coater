from dataclasses import dataclass, replace
from enum import Enum

from dip_coater.mechanical.mechanical_setup import MechanicalSetup


class AvailableMachineSetups(str, Enum):
    """Known machine setup profile keys."""

    SMALL_COATER = "small"
    LARGE_COATER = "large"
    CUSTOM = "custom"


class HomeDirection(str, Enum):
    """Direction of the configured home/reference point."""

    UP = "up"
    DOWN = "down"


class LimitSwitchSource(str, Enum):
    """Hardware source used to read a limit switch."""

    GPIO = "gpio"
    DRIVER_REFERENCE = "driver_reference"


class LimitSwitchPolarity(str, Enum):
    """Electrical polarity that represents a triggered limit switch."""

    ACTIVE_HIGH = "active_high"
    ACTIVE_LOW = "active_low"


@dataclass(frozen=True)
class LimitSwitch:
    """Configuration for one physical or driver-reference limit switch.

    :param source: Hardware source used to read the switch.
    :param polarity: Raw electrical state that means the switch is triggered.
    :param pin: GPIO pin number when ``source`` is ``GPIO``.
    """

    source: LimitSwitchSource
    polarity: LimitSwitchPolarity
    pin: int | None = None

    def is_triggered(self, raw_state: bool) -> bool:
        """Interpret a raw switch state using the configured polarity.

        :param raw_state: Raw boolean state read from GPIO or the driver.
        :return: ``True`` when the switch should be treated as triggered.
        """
        if self.polarity == LimitSwitchPolarity.ACTIVE_HIGH:
            return raw_state
        return not raw_state

    @property
    def normally_closed(self) -> bool:
        """Report whether this configuration represents a normally-closed switch.

        :return: ``True`` for the active-high convention used by NC GPIO switches.
        """
        return self.polarity == LimitSwitchPolarity.ACTIVE_HIGH


@dataclass(frozen=True)
class LimitSwitchSetup:
    """Paired up/down limit-switch configuration.

    :param up: Switch used at the upward travel limit.
    :param down: Switch used at the downward travel limit.
    """

    up: LimitSwitch
    down: LimitSwitch

    @classmethod
    def gpio(
        cls,
        *,
        up_pin: int,
        down_pin: int,
        up_nc: bool = True,
        down_nc: bool = True,
    ) -> "LimitSwitchSetup":
        """Create a GPIO-backed limit-switch setup.

        :param up_pin: GPIO pin for the upward limit switch.
        :param down_pin: GPIO pin for the downward limit switch.
        :param up_nc: Whether the upward switch is normally closed.
        :param down_nc: Whether the downward switch is normally closed.
        :return: Configured GPIO limit-switch pair.
        """
        return cls(
            up=LimitSwitch(
                source=LimitSwitchSource.GPIO,
                pin=up_pin,
                polarity=(
                    LimitSwitchPolarity.ACTIVE_HIGH
                    if up_nc
                    else LimitSwitchPolarity.ACTIVE_LOW
                ),
            ),
            down=LimitSwitch(
                source=LimitSwitchSource.GPIO,
                pin=down_pin,
                polarity=(
                    LimitSwitchPolarity.ACTIVE_HIGH
                    if down_nc
                    else LimitSwitchPolarity.ACTIVE_LOW
                ),
            ),
        )

    @classmethod
    def tmc5160_reference(
        cls,
        *,
        up_polarity: LimitSwitchPolarity = LimitSwitchPolarity.ACTIVE_LOW,
        down_polarity: LimitSwitchPolarity = LimitSwitchPolarity.ACTIVE_LOW,
    ) -> "LimitSwitchSetup":
        """Create a TMC5160 reference-input limit-switch setup.

        :param up_polarity: Trigger polarity for the left/up reference input.
        :param down_polarity: Trigger polarity for the right/down reference input.
        :return: Configured driver-reference limit-switch pair.
        """
        return cls(
            up=LimitSwitch(
                source=LimitSwitchSource.DRIVER_REFERENCE,
                polarity=up_polarity,
            ),
            down=LimitSwitch(
                source=LimitSwitchSource.DRIVER_REFERENCE,
                polarity=down_polarity,
            ),
        )

    @property
    def uses_gpio(self) -> bool:
        """Report whether either switch uses a GPIO pin.

        :return: ``True`` when at least one switch is GPIO-backed.
        """
        return (
            self.up.source == LimitSwitchSource.GPIO
            or self.down.source == LimitSwitchSource.GPIO
        )

    @property
    def uses_driver_reference(self) -> bool:
        """Report whether either switch uses a driver reference input.

        :return: ``True`` when at least one switch is driver-reference-backed.
        """
        return (
            self.up.source == LimitSwitchSource.DRIVER_REFERENCE
            or self.down.source == LimitSwitchSource.DRIVER_REFERENCE
        )

    @property
    def up_pin(self) -> int | None:
        """Return the upward GPIO pin, if one is configured.

        :return: Upward GPIO pin number or ``None``.
        """
        return self.up.pin

    @property
    def down_pin(self) -> int | None:
        """Return the downward GPIO pin, if one is configured.

        :return: Downward GPIO pin number or ``None``.
        """
        return self.down.pin

    @property
    def up_nc(self) -> bool:
        """Report whether the upward switch is normally closed.

        :return: ``True`` when the upward switch uses the NC convention.
        """
        return self.up.normally_closed

    @property
    def down_nc(self) -> bool:
        """Report whether the downward switch is normally closed.

        :return: ``True`` when the downward switch uses the NC convention.
        """
        return self.down.normally_closed

    def switch_for(self, direction: HomeDirection) -> LimitSwitch:
        """Select the switch associated with a travel direction.

        :param direction: Direction whose limit switch should be returned.
        :return: Configured switch for that direction.
        """
        return self.up if direction == HomeDirection.UP else self.down


def LimitSwitchPair(
    up_pin: int,
    down_pin: int,
    up_nc: bool = True,
    down_nc: bool = True,
) -> LimitSwitchSetup:
    """Create a GPIO limit-switch pair.

    :param up_pin: GPIO pin for the upward limit switch.
    :param down_pin: GPIO pin for the downward limit switch.
    :param up_nc: Whether the upward switch is normally closed.
    :param down_nc: Whether the downward switch is normally closed.
    :return: GPIO-backed limit-switch setup.
    """
    return LimitSwitchSetup.gpio(
        up_pin=up_pin,
        down_pin=down_pin,
        up_nc=up_nc,
        down_nc=down_nc,
    )


@dataclass(frozen=True)
class MachineProfile:
    """Complete mechanical and safety profile for one dip-coater setup.

    :param key: Stable profile key.
    :param label: Human-readable profile label.
    :param mechanical_setup: Mechanical conversion constants for the lift.
    :param invert_motor_direction: Whether physical motor direction is inverted.
    :param home_direction: Direction of the home/reference point.
    :param limit_switches: Optional paired limit-switch configuration.
    :param min_position_mm: Minimum allowed absolute position in millimeters.
    :param max_position_mm: Maximum allowed absolute position in millimeters.
    :param homing_max_distance_mm: Maximum homing search distance in millimeters.
    """

    key: AvailableMachineSetups
    label: str
    mechanical_setup: MechanicalSetup
    invert_motor_direction: bool = False
    home_direction: HomeDirection = HomeDirection.UP
    limit_switches: LimitSwitchSetup | None = None
    min_position_mm: float = 0.0
    max_position_mm: float = 100.0
    homing_max_distance_mm: float = 100.0

    @property
    def homes_up(self) -> bool:
        """Report whether the profile homes at the upward travel limit.

        :return: ``True`` when ``home_direction`` is ``UP``.
        """
        return self.home_direction == HomeDirection.UP

    @property
    def supports_limit_switches(self) -> bool:
        """Report whether this setup has configured limit switches.

        :return: ``True`` when a limit-switch setup is present.
        """
        return self.limit_switches is not None

    @property
    def requires_gpio(self) -> bool:
        """Report whether this setup needs GPIO access.

        :return: ``True`` when configured limit switches use GPIO pins.
        """
        return self.limit_switches is not None and self.limit_switches.uses_gpio

    @property
    def travel_span_mm(self) -> float:
        """Calculate the allowed absolute travel span.

        :return: Non-negative travel span in millimeters.
        """
        return max(0.0, self.max_position_mm - self.min_position_mm)

    def with_overrides(
        self,
        *,
        mechanical_setup: MechanicalSetup | None = None,
        invert_motor_direction: bool | None = None,
        home_direction: HomeDirection | None = None,
        min_position_mm: float | None = None,
        max_position_mm: float | None = None,
        homing_max_distance_mm: float | None = None,
    ) -> "MachineProfile":
        """Create a copy of this profile with selected values replaced.

        :param mechanical_setup: Replacement mechanical setup, or ``None`` to keep the current value.
        :param invert_motor_direction: Replacement direction-inversion flag, or ``None`` to keep the current value.
        :param home_direction: Replacement home direction, or ``None`` to keep the current value.
        :param min_position_mm: Replacement minimum position, or ``None`` to keep the current value.
        :param max_position_mm: Replacement maximum position, or ``None`` to keep the current value.
        :param homing_max_distance_mm: Replacement homing distance, or ``None`` to keep the current value.
        :return: New machine profile with the requested overrides.
        """
        return replace(
            self,
            mechanical_setup=self.mechanical_setup
            if mechanical_setup is None
            else mechanical_setup,
            invert_motor_direction=(
                self.invert_motor_direction
                if invert_motor_direction is None
                else invert_motor_direction
            ),
            home_direction=self.home_direction
            if home_direction is None
            else home_direction,
            min_position_mm=self.min_position_mm
            if min_position_mm is None
            else min_position_mm,
            max_position_mm=self.max_position_mm
            if max_position_mm is None
            else max_position_mm,
            homing_max_distance_mm=(
                self.homing_max_distance_mm
                if homing_max_distance_mm is None
                else homing_max_distance_mm
            ),
        )
