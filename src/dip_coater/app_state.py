from dip_coater.gpio import get_gpio_instance

class AppState:
    """
    This class is used to store a shared state of the application.
    """
    def __init__(self):
        self.gpio = get_gpio_instance()
        self.motor_driver = None
        self.motor_state = "disabled"
        self.homing_found = False
        self.motor_logger_widget = None

app_state = AppState()