"""Factory for constructing the correct motor wrapper for a given chip."""

from __future__ import annotations

from typing import Any, Literal

from pytrinamic.evalboards import TMC2660_eval, TMC5160_eval

from .config import Chip, MotorConfig
from .interface import StepperMotor
from .motors.tmc2660_motor import TMC2660Motor
from .motors.tmc5160_motor import TMC5160Motor


ChipName = Literal["TMC5160", "TMC2660"]
ChipLike = Chip | ChipName


# Default sense-resistor values on the respective ADI eval boards. Users
# with custom hardware should pass an explicit MotorConfig.
_DEFAULT_RSENSE = {
    "TMC5160": 0.075,
    "TMC2660": 0.1,
}


def create_motor(
    chip: ChipLike,
    connection: Any,
    *,
    config: MotorConfig | None = None,
    module_id: int = 1,
    axis: int = 0,
) -> StepperMotor:
    """Create the correct motor wrapper for the given chip.

    :param chip: Either ``Chip.TMC5160`` / ``Chip.TMC2660`` or the
        equivalent string value.
    :param connection: A ``pytrinamic`` connection as returned by
        ``ConnectionManager().connect()``.
    :param config: Mechanical/electrical configuration. If ``None``, a
        default ``MotorConfig`` with sense resistor matching the ADI eval
        board for the chosen chip is used.
    :param module_id: TMCL module ID (default 1 for Landungsbrücke).
    :param axis: Motor axis index on the eval board (always 0 for these
        single-axis boards).
    :returns: A :class:`StepperMotor`-compatible object.
    """
    chip_name = chip.value if isinstance(chip, Chip) else chip

    if chip_name == "TMC5160":
        cfg = config or MotorConfig(sense_resistor_ohms=_DEFAULT_RSENSE["TMC5160"])
        eval_board = TMC5160_eval(connection, module_id=module_id)
        return TMC5160Motor(eval_board, cfg, axis=axis)
    elif chip_name == "TMC2660":
        cfg = config or MotorConfig(sense_resistor_ohms=_DEFAULT_RSENSE["TMC2660"])
        eval_board = TMC2660_eval(connection, module_id=module_id)
        return TMC2660Motor(eval_board, cfg, axis=axis)
    else:
        raise ValueError(
            f"unknown chip {chip!r}; expected Chip.TMC5160 / Chip.TMC2660 "
            "or the equivalent string"
        )
