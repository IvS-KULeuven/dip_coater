from dip_coater.config.config_base import *
from dip_coater.logging.tmc2660_logger import TMC2660LogLevel
from dip_coater.motor.tmc2660 import ChopperMode, VSenseFullScale, StepDirSource

# TMC2660 specific settings

# Logging settings
DEFAULT_LOGGING_LEVEL = TMC2660LogLevel.INFO

# Current settings (in mA)
DEFAULT_CURRENT = 2000
DEFAULT_CURRENT_STANDSTILL = 100
MIN_CURRENT = 74    # Minimum current that can be sensed by the TMC2660 (with 350 mV full scale VSENSE)
MAX_CURRENT = 2000  # Absolute max limit for TMC2660 !

# Other motor settings
INVERT_MOTOR_DIRECTION = False
USE_INTERPOLATION = False
DEFAULT_CHOPPER_MODE = ChopperMode.SPREAD_CYCLE
VSENSE_FULL_SCALE = VSenseFullScale.VSENSE_FULL_SCALE_305mV
DEFAULT_STEP_DIR_SOURCE = StepDirSource.INTERNAL
