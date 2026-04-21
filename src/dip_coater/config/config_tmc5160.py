from dip_coater.config.config_base import *
from dip_coater.logging.tmc5160_logger import TMC5160LogLevel

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

# GLOBAL_SCALER (0 = full scale/256, or 32-256)
DEFAULT_GLOBAL_SCALER = 0

# Sense resistor (mOhm) — depends on the evaluation board
DEFAULT_RSENSE = 75

# Chopper settings
DEFAULT_CHOPPER_MODE = "SpreadCycle"
USE_INTERPOLATION = True

# StallGuard / CoolStep defaults
DEFAULT_STALLGUARD_ENABLED = False
DEFAULT_STALLGUARD_FILTER_ENABLED = False
DEFAULT_STALLGUARD_THRESHOLD = 0
DEFAULT_COOLSTEP_ENABLED = False
DEFAULT_COOLSTEP_THRESHOLD = 0

# S-curve ramp defaults (TMC5160 internal units)
# These match the PyTrinamic TMC5160 demo values.
# Velocity: v_internal = v_Hz * 2^24 / fCLK  (fCLK = 12 MHz)
# Acceleration: a_internal = a_Hz_per_s * 2^41 / fCLK^2
DEFAULT_RAMP_VSTART = 0
DEFAULT_RAMP_A1 = 1000
DEFAULT_RAMP_V1 = 50000
DEFAULT_RAMP_AMAX = 1000
DEFAULT_RAMP_VMAX = 200000
DEFAULT_RAMP_DMAX = 700
DEFAULT_RAMP_D1 = 1400
DEFAULT_RAMP_VSTOP = 10
DEFAULT_RAMP_TZEROWAIT = 0
