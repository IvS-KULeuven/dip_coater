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


@dataclass(frozen=True)
class LimitSwitchPair:
    up_pin: int
    down_pin: int
    up_nc: bool = True
    down_nc: bool = True


@dataclass(frozen=True)
class MachineProfile:
    key: AvailableMachineSetups
    label: str
    mechanical_setup: MechanicalSetup
    invert_motor_direction: bool = False
    home_direction: HomeDirection = HomeDirection.UP
    limit_switches: LimitSwitchPair | None = None
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
