from dip_coater.gpio import get_gpio_instance
from dip_coater.config.config_loader import Config
from dip_coater.motor.motor_driver_interface import AvailableMotorDrivers


class AppState:
    """
    This class is used to store a shared state of the application.
    """
    def __init__(self, driver_type: AvailableMotorDrivers = AvailableMotorDrivers.TMC2209):
        self.driver_type = driver_type
        self.config = Config(driver_type)
        # GPIO is only needed for the TMC2209 path (limit switches and pin control).
        self.gpio = get_gpio_instance() if driver_type == AvailableMotorDrivers.TMC2209 else None
        self.motor_driver = None
        self.motor_state = "disabled"
        self.homing_found = False
        self.motor_logger_handler = None
        self.motor_logger_widget = None
        self.status = None
        self.advanced_settings = None
        self.status_advanced = None
        self.motor_controls = None
        self.speed_controls = None
        self.position_controls = None
        self.distance_controls = None
        self.step_mode = None
        self.mechanical_setup = None
