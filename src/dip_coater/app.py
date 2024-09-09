import argparse
import logging
import uvloop
import asyncio

from textual import on
from textual.app import App, ComposeResult
from textual.widgets import Button, Footer, Header, RichLog, TabbedContent
from textual.binding import Binding
from importlib.metadata import version

try:
    import TMC_2209
except ModuleNotFoundError:
    import sys
    import MyTMC_2209 as TMC_2209
    sys.modules["TMC_2209"] = TMC_2209

from TMC_2209._TMC_2209_logger import Loglevel
from dip_coater.app_state import AppState

from dip_coater.logging.motor_logger import MotorLoggerHandler, TempLoggerHandler
from dip_coater.commands.help_command import HelpCommand
from dip_coater.screens.help_screen import HelpScreen

from dip_coater.widgets.tabs.main_tab import MainTab
from dip_coater.widgets.tabs.logs_tab import LogsTab
from dip_coater.widgets.tabs.advanced_settings_tab import AdvancedSettingsTab
from dip_coater.widgets.tabs.coder_tab import CoderTab

from dip_coater.mechanical.mechanical_setup import MechanicalSetup
from dip_coater.mechanical.setup_small_coater import SetupSmallCoater
from dip_coater.mechanical.setup_large_coater import SetupLargeCoater
from dip_coater.motor.motor_driver_interface import MotorDriver
from dip_coater.motor.motor_driver_interface import AvailableMotorDrivers
from dip_coater.motor.tmc2209 import MotorDriverTMC2209
from dip_coater.motor.tmc2660 import MotorDriverTMC2660, TMC2660LogLevel


def create_motor_driver(driver_type: str, app_state,
                        log_level, log_handlers, log_formatter,
                        interface_type="usb_tmcl", port="interactive") -> MotorDriver:
    if driver_type == AvailableMotorDrivers.TMC2209:
        return MotorDriverTMC2209(app_state,
                                  step_mode=app_state.config.STEP_MODES[app_state.config.DEFAULT_STEP_MODE],
                                  current_mA=app_state.config.DEFAULT_CURRENT,
                                  current_standstill_mA=app_state.config.DEFAULT_CURRENT_STANDSTILL,
                                  invert_direction=app_state.config.INVERT_MOTOR_DIRECTION,
                                  interpolation=app_state.config.USE_INTERPOLATION,
                                  spread_cycle=app_state.config.USE_SPREAD_CYCLE,
                                  loglevel=log_level,
                                  log_handlers=log_handlers,
                                  log_formatter=log_formatter)
    elif driver_type == AvailableMotorDrivers.TMC2660:
        if app_state.config.USE_DUMMY_DRIVER:
            interface_type = "dummy_tmcl"
            port = None
        return MotorDriverTMC2660(app_state,
                                  interface_type=interface_type,
                                  port=port,
                                  step_mode=app_state.config.STEP_MODES[app_state.config.DEFAULT_STEP_MODE],
                                  current_mA=app_state.config.DEFAULT_CURRENT,
                                  current_standstill_mA=app_state.config.DEFAULT_CURRENT_STANDSTILL,
                                  chopper_mode=app_state.config.DEFAULT_CHOPPER_MODE,
                                  vsense_full_scale=app_state.config.VSENSE_FULL_SCALE,
                                  step_dir_source=app_state.config.DEFAULT_STEP_DIR_SOURCE,
                                  loglevel=log_level,
                                  log_handlers=log_handlers,
                                  log_formatter=log_formatter)
    else:
        raise ValueError(f"Unsupported driver type: '{driver_type}'")


def get_log_level(driver_type: str, log_level_str: str):
    if driver_type == AvailableMotorDrivers.TMC2209:
        return getattr(Loglevel, log_level_str)
    elif driver_type == AvailableMotorDrivers.TMC2660:
        return getattr(TMC2660LogLevel, log_level_str)
    else:
        raise ValueError(f"Unsupported driver type: {driver_type}")


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
        Binding("d", "disable_motor", "Disable the motor", show=False),
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
        log = self.query_one("#logger", RichLog)
        log.write("Motor has been initialised.")

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Footer()
        with TabbedContent(initial="main-tab", id="tabbed-content"):
            yield MainTab(self.app_state)
            yield LogsTab(self.app_state)
            yield AdvancedSettingsTab(self.app_state)
            yield CoderTab(self.app_state)

    @on(Button.Pressed, "#reset-to-defaults-btn")
    def reset_to_defaults(self):
        self.app_state.advanced_settings.reset_settings_to_default()

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark

    def action_request_quit(self) -> None:
        self.app_state.motor_driver.cleanup()
        self.app.exit()

    def action_show_help(self) -> None:
        self.push_screen(HelpScreen())

    async def action_move_up(self) -> None:
        await self.app_state.motor_controls.move_up_action()

    async def action_move_down(self) -> None:
        await self.app_state.motor_controls.move_down_action()

    async def action_enable_motor(self) -> None:
        await self.app_state.motor_controls.enable_motor_action()

    async def action_disable_motor(self) -> None:
        await self.app_state.motor_controls.disable_motor_action()


def main():
    # Handle command line arguments
    parser = argparse.ArgumentParser(description='Process logging level and motor driver type.')
    parser.add_argument('-l', '--log-level', type=str,
                        default=Loglevel.INFO.name,
                        choices=['NONE', 'ERROR', 'INFO', 'DEBUG', 'MOVEMENT', 'ALL'],
                        help='Set the logging level')
    parser.add_argument('-d', '--driver', type=AvailableMotorDrivers, default=AvailableMotorDrivers.TMC2209,
                        choices=[AvailableMotorDrivers.TMC2209, AvailableMotorDrivers.TMC2660],
                        help='Set the motor driver type')
    parser.add_argument('-i', '--interface', type=str, default='usb_tmcl',
                        choices=['usb_tmcl', 'dummy_tmcl', 'kvaser_tmcl', 'pcan_tmcl', 'slcan_tmcl', 'socketcan_tmcl',
                                 'serial_tmcl', 'uart_ic', 'ixxat_tmcl'],
                        help='Set the TMC2660 interface type')
    parser.add_argument('-p', '--port', type=str, default='/dev/ttyACM0',
                        help='Set the TMC2660 interface port. User \'interactive\' for interactive port selection')
    parser.add_argument('--mm-per-revolution', type=float,
                        help='Distance in mm the platform moves for one full revolution')
    parser.add_argument('--gearbox-ratio', type=float,
                        help='Gearbox ratio, if any')
    parser.add_argument('--steps-per-rev', type=int,
                        help='Number of full steps per revolution')
    parser.add_argument('--use-dummy-driver', action='store_true',
                        help='Use a dummy driver instead of the real motor driver')
    args = parser.parse_args()

    # Build the application state
    app_state = AppState(args.driver)
    if args.use_dummy_driver is not None:
        app_state.config.USE_DUMMY_DRIVER = args.use_dummy_driver

    # Build the mechanical setup based on driver type and command line arguments
    if args.mm_per_revolution is not None or args.gearbox_ratio is not None:
        # Use custom setup if either mm_per_revolution or gearbox_ratio is provided
        mechanical_setup = MechanicalSetup(
            mm_per_revolution=args.mm_per_revolution if args.mm_per_revolution is not None else 3.0,
            gearbox_ratio=args.gearbox_ratio if args.gearbox_ratio is not None else 1.0,
            steps_per_revolution=args.steps_per_rev if args.steps_per_rev is not None else 200,
        )
    else:
        # Use predefined setups based on driver type
        if args.driver == AvailableMotorDrivers.TMC2209:
            mechanical_setup = SetupSmallCoater()
        elif args.driver == AvailableMotorDrivers.TMC2660:
            mechanical_setup = SetupLargeCoater()
        else:
            raise ValueError(f"Unsupported driver type: {args.driver}")

    app_state.mechanical_setup = mechanical_setup

    # Build the motor driver
    app_state.motor_logger_handler = TempLoggerHandler()
    logging_format = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s",
                                       "%Y%m%d %H:%M:%S")
    log_level = get_log_level(args.driver, args.log_level)
    driver = create_motor_driver(
        driver_type=args.driver,
        app_state=app_state,
        log_level=log_level,
        log_handlers=[app_state.motor_logger_handler],
        log_formatter=logging_format,
        interface_type=args.interface,
        port=args.port
    )
    app_state.motor_driver = driver

    # Build and start the application
    package_version = version("dip-coater")
    print(f"Starting Dip Coater v{package_version}, driver: {args.driver}, log level: {log_level}")
    app = DipCoaterApp(app_state)
    app.title = f"Dip Coater v{package_version}"
    app.run()


if __name__ == '__main__':
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    main()
