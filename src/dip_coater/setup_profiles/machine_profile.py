from dataclasses import dataclass, replace
from enum import Enum

from dip_coater.mechanical.mechanical_setup import MechanicalSetup


class AvailableMachineSetups(str, Enum):
    SMALL_COATER = "small"
    LARGE_COATER = "large"
    CUSTOM = "custom"


class HomeDirection(str, Enum):
    UP = "up"
    DOWN = "down"


class LimitSwitchSource(str, Enum):
    GPIO = "gpio"
    DRIVER_REFERENCE = "driver_reference"


class LimitSwitchPolarity(str, Enum):
    ACTIVE_HIGH = "active_high"
    ACTIVE_LOW = "active_low"


@dataclass(frozen=True)
class LimitSwitch:
    source: LimitSwitchSource
    polarity: LimitSwitchPolarity
    pin: int | None = None

    def is_triggered(self, raw_state: bool) -> bool:
        if self.polarity == LimitSwitchPolarity.ACTIVE_HIGH:
            return raw_state
        return not raw_state

    @property
    def normally_closed(self) -> bool:
        return self.polarity == LimitSwitchPolarity.ACTIVE_HIGH


@dataclass(frozen=True)
class LimitSwitchSetup:
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
        return (
            self.up.source == LimitSwitchSource.GPIO
            or self.down.source == LimitSwitchSource.GPIO
        )

    @property
    def uses_driver_reference(self) -> bool:
        return (
            self.up.source == LimitSwitchSource.DRIVER_REFERENCE
            or self.down.source == LimitSwitchSource.DRIVER_REFERENCE
        )

    @property
    def up_pin(self) -> int | None:
        return self.up.pin

    @property
    def down_pin(self) -> int | None:
        return self.down.pin

    @property
    def up_nc(self) -> bool:
        return self.up.normally_closed

    @property
    def down_nc(self) -> bool:
        return self.down.normally_closed

    def switch_for(self, direction: HomeDirection) -> LimitSwitch:
        return self.up if direction == HomeDirection.UP else self.down


def LimitSwitchPair(
    up_pin: int,
    down_pin: int,
    up_nc: bool = True,
    down_nc: bool = True,
) -> LimitSwitchSetup:
    return LimitSwitchSetup.gpio(
        up_pin=up_pin,
        down_pin=down_pin,
        up_nc=up_nc,
        down_nc=down_nc,
    )


@dataclass(frozen=True)
class MachineProfile:
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
        return self.home_direction == HomeDirection.UP

    @property
    def supports_limit_switches(self) -> bool:
        return self.limit_switches is not None

    @property
    def requires_gpio(self) -> bool:
        return self.limit_switches is not None and self.limit_switches.uses_gpio

    @property
    def travel_span_mm(self) -> float:
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
