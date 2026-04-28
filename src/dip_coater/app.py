import argparse
import asyncio
import logging
import os
import sys

from textual import on
from textual.app import App, ComposeResult
from textual.widgets import Button, Footer, Header, RichLog, TabbedContent
from textual.binding import Binding

try:
    import TMC_2209
except ModuleNotFoundError:
    import MyTMC_2209 as TMC_2209

    sys.modules["TMC_2209"] = TMC_2209

from dip_coater.app_state import AppState

from dip_coater.logging.motor_logger import MotorLoggerHandler, TempLoggerHandler
from dip_coater.commands.help_command import HelpCommand
from dip_coater.screens.help_screen import HelpScreen

from dip_coater.widgets.tabs.main_tab import MainTab
from dip_coater.widgets.tabs.logs_tab import LogsTab
from dip_coater.widgets.tabs.advanced_settings_tab import AdvancedSettingsTab
from dip_coater.widgets.tabs.coder_tab import CoderTab
from dip_coater.widgets.tabs.diagnostics_tab import DiagnosticsTab
from dip_coater import __version__

from dip_coater.motor_driver.motor_driver_interface import AvailableMotorDrivers
from dip_coater.motor_driver.driver_registry import get_driver_spec
from dip_coater.services import MotionController
from dip_coater.setup_profiles import (
    create_custom_profile,
    get_default_setup_for_driver,
    get_machine_profile,
    list_machine_setups,
)
from dip_coater.setup_profiles.machine_profile import HomeDirection


class DipCoaterApp(App):
    """A Textual App to control a dip coater motor."""

    CSS_PATH = "tui.tcss"
    BINDINGS = [
        Binding("t", "toggle_dark", "Toggle dark mode"),
        Binding("q", "request_quit", "Quit"),
        Binding("h", "show_help", "Help"),
        Binding("w", "move_up", "Move up", show=False),
        Binding("s", "move_down", "Move down", show=False),
        Binding("a", "enable_motor", "Enable the motor", show=False),
        Binding("d", "disable_motor", "Emergency STOP motor", priority=True),
    ]
    COMMANDS = App.COMMANDS | {HelpCommand}

    def __init__(self, app_state):
        super().__init__()
        self.app_state = app_state
        self.app_state.motor_logger_widget = RichLog(markup=True, id="motor-logger")

        temp_handler = self.app_state.motor_logger_handler
        self.app_state.motor_logger_handler = MotorLoggerHandler(app_state)
        self.app_state.motor_driver.remove_log_handler(temp_handler)
        self.app_state.motor_driver.add_log_handler(self.app_state.motor_logger_handler)
        for entry in temp_handler.get_entries():
            self.app_state.motor_logger_handler.emit(entry)

    def on_mount(self):
        # on_mount() is called after compose(), so the RichLog is known
        log = self.query_one("#motor-logger", RichLog)
        log.write("Motor has been initialised.")
        log.write(
            "[cyan]"
            f"[startup] driver={self.app_state.driver_type.value} "
            f"setup={self.app_state.setup_profile.label} "
            f"default_distance={self.app_state.config.DEFAULT_DISTANCE}mm "
            f"default_speed={self.app_state.config.DEFAULT_SPEED}mm/s "
            f"default_accel={self.app_state.config.DEFAULT_ACCELERATION}mm/s² "
            f"default_step_mode={self.app_state.config.DEFAULT_STEP_MODE} "
            f"invert_direction={self.app_state.setup_profile.invert_motor_direction}"
            "[/]"
        )

    def compose(self) -> ComposeResult:
        yield Header(
            show_clock=True,
            id="app-header",
            classes="dummy-mode" if self.app_state.config.USE_DUMMY_DRIVER else "",
        )
        yield Footer()
        with TabbedContent(initial="main-tab", id="tabbed-content"):
            yield MainTab(self.app_state)
            yield LogsTab(self.app_state)
            yield AdvancedSettingsTab(self.app_state)
            yield DiagnosticsTab(self.app_state)
            yield CoderTab(self.app_state)

    @on(Button.Pressed, "#reset-to-defaults-btn")
    def reset_to_defaults(self):
        self.app_state.advanced_settings.reset_settings_to_default()

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark

    def action_request_quit(self) -> None:
        self.app_state.motion_controller.cleanup()
        self.app.exit()

    def action_show_help(self) -> None:
        self.push_screen(HelpScreen())

    async def action_move_up(self) -> None:
        await self.app_state.motor_controls.move_up_action()

    async def action_move_down(self) -> None:
        await self.app_state.motor_controls.move_down_action()

    async def action_enable_motor(self) -> None:
        await self.app_state.motor_controls.enable_motor_action()

    @on(Button.Pressed, "#disable-motor")
    async def action_disable_motor(self) -> None:
        await self.app_state.motor_controls.disable_motor_action()


def configure_event_loop_policy() -> None:
    if sys.platform == "win32":
        try:
            import winloop
        except ModuleNotFoundError:
            logging.getLogger(__name__).warning(
                "winloop is not installed; using default asyncio event loop."
            )
            return
        asyncio.set_event_loop_policy(winloop.EventLoopPolicy())
        return

    try:
        import uvloop
    except ModuleNotFoundError:
        logging.getLogger(__name__).warning(
            "uvloop is not installed; using default asyncio event loop."
        )
        return
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


def main():
    # Handle command line arguments
    parser = argparse.ArgumentParser(
        description="Process logging level and motor driver type."
    )
    parser.add_argument(
        "-l",
        "--log-level",
        type=str,
        default=os.environ.get("DIP_COATER_LOG_LEVEL", "INFO"),
        choices=["NONE", "ERROR", "INFO", "DEBUG", "MOVEMENT", "ALL"],
        help="Set the logging level (env: DIP_COATER_LOG_LEVEL)",
    )
    parser.add_argument(
        "-d",
        "--driver",
        type=AvailableMotorDrivers,
        default=AvailableMotorDrivers(os.environ["DIP_COATER_DRIVER"])
        if "DIP_COATER_DRIVER" in os.environ
        else AvailableMotorDrivers.TMC2209,
        choices=[
            AvailableMotorDrivers.TMC2209,
            AvailableMotorDrivers.TMC2660,
            AvailableMotorDrivers.TMC5160,
        ],
        help="Set the motor driver type (env: DIP_COATER_DRIVER)",
    )
    parser.add_argument(
        "-s",
        "--setup",
        type=str,
        default=os.environ.get("DIP_COATER_SETUP"),
        choices=[setup.value for setup in list_machine_setups()],
        help="Set the machine setup profile independently from the motor driver (env: DIP_COATER_SETUP)",
    )
    parser.add_argument(
        "-i",
        "--interface",
        type=str,
        default=os.environ.get("DIP_COATER_INTERFACE", "usb_tmcl"),
        choices=[
            "usb_tmcl",
            "dummy_tmcl",
            "kvaser_tmcl",
            "pcan_tmcl",
            "slcan_tmcl",
            "socketcan_tmcl",
            "serial_tmcl",
            "uart_ic",
            "ixxat_tmcl",
        ],
        help="Set the PyTrinamic interface type for supported drivers (env: DIP_COATER_INTERFACE)",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=str,
        default=os.environ.get("DIP_COATER_PORT", "/dev/ttyACM0"),
        help="Set the PyTrinamic interface port. Use 'interactive' for interactive port selection (env: DIP_COATER_PORT)",
    )
    parser.add_argument(
        "--mm-per-revolution",
        type=float,
        default=float(os.environ["DIP_COATER_MM_PER_REVOLUTION"])
        if "DIP_COATER_MM_PER_REVOLUTION" in os.environ
        else None,
        help="Distance in mm the platform moves for one full revolution (env: DIP_COATER_MM_PER_REVOLUTION)",
    )
    parser.add_argument(
        "--gearbox-ratio",
        type=float,
        default=float(os.environ["DIP_COATER_GEARBOX_RATIO"])
        if "DIP_COATER_GEARBOX_RATIO" in os.environ
        else None,
        help="Gearbox ratio, if any (env: DIP_COATER_GEARBOX_RATIO)",
    )
    parser.add_argument(
        "--steps-per-rev",
        type=int,
        default=int(os.environ["DIP_COATER_STEPS_PER_REV"])
        if "DIP_COATER_STEPS_PER_REV" in os.environ
        else None,
        help="Number of full steps per revolution (env: DIP_COATER_STEPS_PER_REV)",
    )
    parser.add_argument(
        "--use-dummy-driver",
        action="store_true",
        default=os.environ.get("DIP_COATER_USE_DUMMY_DRIVER", "").lower()
        in ("1", "true", "yes"),
        help="Use a dummy driver instead of the real motor driver (env: DIP_COATER_USE_DUMMY_DRIVER)",
    )
    parser.add_argument(
        "--invert-direction",
        action="store_true",
        default=os.environ.get("DIP_COATER_INVERT_DIRECTION", "").lower()
        in ("1", "true", "yes"),
        help="Invert the motor direction for this run (env: DIP_COATER_INVERT_DIRECTION)",
    )
    parser.add_argument(
        "--home-direction",
        type=str,
        default=os.environ.get("DIP_COATER_HOME_DIRECTION"),
        choices=[direction.value for direction in HomeDirection],
        help="Override the setup homing direction for this run (env: DIP_COATER_HOME_DIRECTION)",
    )
    args = parser.parse_args()

    driver_spec = get_driver_spec(args.driver)
    setup_key = (
        args.setup
        if args.setup is not None
        else get_default_setup_for_driver(args.driver)
    )
    base_profile = get_machine_profile(setup_key)

    custom_setup_requested = (
        any(
            value is not None
            for value in (
                args.mm_per_revolution,
                args.gearbox_ratio,
                args.steps_per_rev,
                args.home_direction,
            )
        )
        or args.invert_direction
    )
    if custom_setup_requested:
        setup_profile = create_custom_profile(
            base_profile,
            mm_per_revolution=args.mm_per_revolution,
            gearbox_ratio=args.gearbox_ratio,
            steps_per_revolution=args.steps_per_rev,
            invert_motor_direction=True if args.invert_direction else None,
            home_direction=HomeDirection(args.home_direction)
            if args.home_direction
            else None,
        )
    else:
        setup_profile = base_profile

    # Build the application state
    app_state = AppState(
        args.driver,
        setup_profile,
        gpio_required=(driver_spec.requires_gpio or setup_profile.requires_gpio),
    )
    app_state.config.USE_DUMMY_DRIVER = args.use_dummy_driver

    # Build the motor driver
    app_state.motor_logger_handler = TempLoggerHandler()
    logging_format = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s", "%Y%m%d %H:%M:%S"
    )
    log_level = driver_spec.log_level_from_name(args.log_level)
    driver = driver_spec.driver_factory(
        app_state=app_state,
        log_level=log_level,
        log_handlers=[app_state.motor_logger_handler],
        log_formatter=logging_format,
        interface_type=args.interface,
        port=args.port,
    )
    app_state.motor_driver = driver
    app_state.motion_controller = MotionController(
        driver,
        app_state.setup_profile,
        gpio=app_state.gpio,
    )

    # Build and start the application
    print(
        f"Starting Dip Coater v{__version__}, driver: {args.driver}, "
        f"setup: {app_state.setup_profile.label}, log level: {log_level}"
    )
    app = DipCoaterApp(app_state)
    suffix = " (dummy)" if app_state.config.USE_DUMMY_DRIVER else ""
    app.title = f"Dip Coater v{__version__}{suffix}"
    app.run()


if __name__ == "__main__":
    configure_event_loop_policy()
    main()
