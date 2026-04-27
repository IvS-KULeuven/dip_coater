from dip_coater.config.config_base import *  # noqa: F403
from dip_coater.logging.tmc5160_logger import TMC5160LogLevel
from dip_coater.motor_driver.tmc2660 import ChopperMode

# TMC5160 settings

# Logging settings
DEFAULT_LOGGING_LEVEL = TMC5160LogLevel.INFO

# Current settings (in mA)
DEFAULT_CURRENT = 1500
DEFAULT_CURRENT_STANDSTILL = 100
MIN_CURRENT = 50
MAX_CURRENT = 4000  # TMC5160 can go up to 4530, but the motor cannot

# Motion settings
STEP_MODES = {
    "I2": 2,
    "I4": 4,
    "I16": 16,
    "I256": 256,
}
STEP_MODE_LABELS = {
    "I2": "1/2",
    "I4": "1/4",
    "I16": "1/16",
    "I256": "1/256",
}
DEFAULT_STEP_MODE = "I256"
DEFAULT_SPEED = 2
DEFAULT_DISTANCE = 10
DEFAULT_ACCELERATION = 10.0

# Sense resistor (mOhm) — depends on the evaluation board
DEFAULT_RSENSE = 75

USE_INTERPOLATION = True
DEFAULT_CHOPPER_MODE = ChopperMode.SPREAD_CYCLE

# StealthChop, StallGuard & CoolStep settings
DEFAULT_STEALTHCHOP_ENABLED = False
DEFAULT_STEALTHCHOP_THRESHOLD_RPS = 0.0
DEFAULT_STALLGUARD_ENABLED = True
DEFAULT_STALLGUARD_FILTER_ENABLED = True
DEFAULT_STALLGUARD_THRESHOLD = 0
DEFAULT_COOLSTEP_ENABLED = False
DEFAULT_COOLSTEP_THRESHOLD = 0
