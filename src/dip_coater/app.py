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

from dip_coater.logging.motor_logger import MotorLoggerHandler
from dip_coater.commands.help_command import HelpCommand
from dip_coater.screens.help_screen import HelpScreen

from dip_coater.widgets.tabs.main_tab import MainTab
from dip_coater.widgets.tabs.logs_tab import LogsTab
from dip_coater.widgets.tabs.advanced_settings_tab import AdvancedSettingsTab
from dip_coater.widgets.tabs.coder_tab import CoderTab

from dip_coater.motor.mechanical_setup import MechanicalSetup
from dip_coater.motor.motor_driver_interface import MotorDriver
from dip_coater.motor.motor_driver_interface import AvailableMotorDrivers
from dip_coater.motor.tmc2209 import MotorDriverTMC2209
from dip_coater.motor.tmc2660 import MotorDriverTMC2660


def create_motor_driver(driver_type: str, app_state, log_level: Loglevel, log_handlers,
                        log_formatter,
                        interface_type="usb_tmcl", port="interactive") -> MotorDriver:
    if driver_type == AvailableMotorDrivers.TMC2209:
        return MotorDriverTMC2209(app_state,
                                  step_mode=app_state.config.STEP_MODES[
                                       app_state.config.DEFAULT_STEP_MODE],
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
                                  loglevel=log_level,
                                  log_handlers=log_handlers,
                                  log_formatter=log_formatter)
    else:
        raise ValueError(f"Unsupported driver type: '{driver_type}'")


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

    def __init__(self, driver_type: str, mechanical_setup: MechanicalSetup,
                 log_level: Loglevel = Loglevel.INFO, use_dummy_driver: bool = None):
        super().__init__()
        self.app_state = AppState(driver_type)
        if use_dummy_driver is not None:
            self.app_state.config.USE_DUMMY_DRIVER = use_dummy_driver
        self.app_state.motor_logger_widget = RichLog(markup=True, id="motor-logger")
        self.app_state.mechanical_setup = mechanical_setup
        motor_logger_handler = MotorLoggerHandler(self.app_state)
        logging_format = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s",
                                           "%Y%m%d %H:%M:%S")
        self.app_state.motor_driver = create_motor_driver(driver_type, self.app_state, log_level,
                                                     [motor_logger_handler], logging_format)

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
    parser = argparse.ArgumentParser(description='Process logging level and motor driver type.')
    parser.add_argument('-l', '--log-level', type=str,
                        default=Loglevel.INFO.name,
                        choices=['NONE', 'ERROR', 'INFO', 'DEBUG', 'MOVEMENT', 'ALL'],
                        help='Set the logging level')
    parser.add_argument('-d', '--driver', type=str, default=AvailableMotorDrivers.TMC2660,
                        choices=['TMC2209', 'TMC2660'],
                        help='Set the motor driver type')
    parser.add_argument('--mm-per-revolution', type=float, default=4.0,
                        help='Distance in mm the platform moves for one full revolution')
    parser.add_argument('--gearbox-ratio', type=float, default=1.0,
                        help='Gearbox ratio, if any')
    parser.add_argument('--use-dummy-driver', action='store_true',
                        help='Use a dummy driver instead of the real motor driver')

    args = parser.parse_args()

    mechanical_setup = MechanicalSetup(
        mm_per_revolution=args.mm_per_revolution,
        gearbox_ratio=args.gearbox_ratio
    )

    # Convert string level to the appropriate value in your Loglevel enum
    log_level = getattr(Loglevel, args.log_level)

    package_version = version("dip-coater")
    print(f"Starting Dip Coater v{package_version}, driver: {args.driver}, log level: {log_level}")
    use_dummy_driver = True if args.use_dummy_driver else False
    app = DipCoaterApp(args.driver, mechanical_setup, log_level, use_dummy_driver=use_dummy_driver)
    app.title = f"Dip Coater v{package_version}"
    app.run()


if __name__ == '__main__':
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    main()
