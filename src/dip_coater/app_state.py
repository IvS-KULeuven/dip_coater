from dip_coater.gpio import get_gpio_instance
from dip_coater.config.config_loader import Config
from dip_coater.logging.session_log import NullSessionLog
from dip_coater.motor_driver.motor_driver_interface import AvailableMotorDrivers
from dip_coater.setup_profiles.machine_profile import MachineProfile


class AppState:
    """Shared runtime state for the dip-coater application.

    The TUI, examples, and controller setup code use this object to keep the
    selected driver, configuration module, hardware access objects, and widgets
    connected.
    """

    def __init__(
        self,
        driver_type: AvailableMotorDrivers = AvailableMotorDrivers.TMC2209,
        setup_profile: MachineProfile | None = None,
        *,
        gpio_required: bool = False,
    ):
        """Create application state for one driver/setup combination.

        :param driver_type: Motor driver type to configure.
        :param setup_profile: Machine profile selected for this run.
        :param gpio_required: Whether GPIO access should be initialized.
        """
        self.driver_type = driver_type
        self.config = Config(driver_type)
        self.setup_profile = setup_profile
        self.mechanical_setup = (
            setup_profile.mechanical_setup if setup_profile is not None else None
        )
        self.gpio = get_gpio_instance() if gpio_required else None
        self.motor_driver = None
        self.motion_controller = None
        self.session_log = NullSessionLog()
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
