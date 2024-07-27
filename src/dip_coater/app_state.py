class AppState:
    """
    This class is used to store a shared state of the application.
    """
    def __init__(self):
        self.motor_driver = None
        self.motor_state = "disabled"
        self.homing_found = False

app_state = AppState()