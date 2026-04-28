"""
trinamic_wrapper - a clean, chip-agnostic wrapper around PyTrinamic for the
TMC5160 and TMC2660 evaluation boards driven by the Landungsbrücke.

Typical usage:

    from trinamic_wrapper import (
        connection, create_motor, MotorConfig, Direction, StepMode,
    )

    with connection("/dev/tty.usbmodemTMCEVAL1") as conn:
        motor = create_motor(
            chip="TMC5160",
            connection=conn,
            config=MotorConfig(full_steps_per_rev=200, sense_resistor_ohms=0.075),
        )
        motor.set_run_current_mA(1200)
        motor.set_standstill_current_mA(300)
        motor.set_step_mode(StepMode.USTEP_256)
        motor.set_acceleration_rps2(5.0)
        motor.enable()
        motor.rotate(speed_rps=1.0, direction=Direction.CW)
        ...
        motor.stop()
        motor.disable()
"""

from .config import Chip, MotorConfig, StepMode, Direction, RampMode
from .connection import connection, open_connection
from .interface import StepperMotor
from .exceptions import (
    TrinamicWrapperError,
    OutOfRangeError,
    UnsupportedFeatureError,
)
from .factory import create_motor
from .motors.dummy_motor import DummyStepperMotor
from .motors.tmc5160_motor import TMC5160Motor
from .motors.tmc2660_motor import TMC2660Motor

__all__ = [
    "MotorConfig",
    "Chip",
    "StepMode",
    "Direction",
    "RampMode",
    "StepperMotor",
    "TrinamicWrapperError",
    "OutOfRangeError",
    "UnsupportedFeatureError",
    "create_motor",
    "connection",
    "open_connection",
    "DummyStepperMotor",
    "TMC5160Motor",
    "TMC2660Motor",
]
