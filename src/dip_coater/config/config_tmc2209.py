from dip_coater.config.config_base import *
from TMC_2209._TMC_2209_logger import Loglevel

# TMC2209 specific settings

# Logging settings
DEFAULT_LOGGING_LEVEL = Loglevel.INFO  # NONE, ERROR, INFO, DEBUG, MOVEMENT, ALL

# Current settings (in mA)
DEFAULT_CURRENT = 600
DEFAULT_CURRENT_STANDSTILL = 100
MIN_CURRENT = 31    # Minimum current that can be sensed by the TMC2209
MAX_CURRENT = 2475  # Absolute max limit for TMC2209 !

# Other motor settings
INVERT_MOTOR_DIRECTION = False
USE_SPREAD_CYCLE = False
USE_INTERPOLATION = True

# Threshold speed settings
DEFAULT_THRESHOLD_SPEED = 8.0  # mm/s
MIN_THRESHOLD_SPEED = 0.1  # mm/s
MAX_THRESHOLD_SPEED = 20.0  # mm/s
THRESHOLD_SPEED_ENABLED = True

# Low-speed configuration
LOW_SPEED_STEP_MODE = "I8"
LOW_SPEED_INTERPOLATION = True
LOW_SPEED_SPREAD_CYCLE = False

# High-speed configuration
HIGH_SPEED_STEP_MODE = "I2"
HIGH_SPEED_INTERPOLATION = False
HIGH_SPEED_SPREAD_CYCLE = True

