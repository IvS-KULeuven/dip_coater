from TMC_2209._TMC_2209_logger import Loglevel

# Dummy driver settings
USE_DUMMY_DRIVER = False

# Logging settings
STEP_MODE_WRITE_TO_LOG = False
DEFAULT_LOGGING_LEVEL = Loglevel.INFO  # NONE, ERROR, INFO, DEBUG, MOVEMENT, ALL

# Speed settings (mm/s)
DEFAULT_SPEED = 5
SPEED_STEP_COARSE = 1
SPEED_STEP_FINE = 0.1
MAX_SPEED = 20
MIN_SPEED = 0.01

# Distance settings (mm)
DEFAULT_DISTANCE = 10
DISTANCE_STEP_COARSE = 5
DISTANCE_STEP_FINE = 1
MAX_DISTANCE = 100
MIN_DISTANCE = 0

# Position settings (mm)
DEFAULT_POSITION = 10
POSITION_STEP_COARSE = 5
POSITION_STEP_FINE = 1
MAX_POSITION = 100
MIN_POSITION = 0

# Acceleration settings (mm/s^2)
DEFAULT_ACCELERATION = 30
MIN_ACCELERATION = 0.5
MAX_ACCELERATION = 50

# Step mode settings
STEP_MODES = {
    "I1": 1,
    "I2": 2,
    "I4": 4,
    "I8": 8,
    "I16": 16,
    "I32": 32,
    "I64": 64,
    "I128": 128,
    "I256": 256,
}
STEP_MODE_LABELS = {
    "I1": "1",
    "I2": "1/2",
    "I4": "1/4",
    "I8": "1/8",
    "I16": "1/16",
    "I32": "1/32",
    "I64": "1/64",
    "I128": "1/128",
    "I256": "1/256",
}
DEFAULT_STEP_MODE = "I8"

# Current settings (in mA)
DEFAULT_CURRENT = 600
MIN_CURRENT = 31    # Minimum current that can be sensed by the TMC2209
MAX_CURRENT = 2000  # Absolute max limit for TMC2209!

# Limit switch settings
LIMIT_SWITCH_UP_PIN = 19
LIMIT_SWITCH_UP_NC = True       # Normally closed (NC) or normally open (NO)
LIMIT_SWITCH_DOWN_PIN = 26
LIMIT_SWITCH_DOWN_NC = True     # Normally closed (NC) or normally open (NO)

# Homing settings
#HOMING_REVOLUTIONS = 25
HOMING_REVOLUTIONS = 5  # For testing
HOMING_MAX_DISTANCE = 100   # mm
HOMING_MIN_REVOLUTIONS = 1
HOMING_MAX_REVOLUTIONS = 100
HOMING_THRESHOLD = 100
HOMING_MIN_THRESHOLD = 1
HOMING_MAX_THRESHOLD = 255
HOMING_SPEED_MM_S = 2
HOMING_MIN_SPEED = 0.2
HOMING_MAX_SPEED = 5
HOME_UP = True      # Home the motor upwards (True) or downwards (False)

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

# Application config file
CONFIG_FILE = "dip_coater_config.json"