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
from dip_coater.app_state import app_state

from dip_coater.logging.motor_logger import MotorLoggerHandler
from dip_coater.commands.help_command import HelpCommand
from dip_coater.screens.help_screen import HelpScreen
from dip_coater.constants import (
    STEP_MODES, DEFAULT_STEP_MODE, DEFAULT_CURRENT, INVERT_MOTOR_DIRECTION, USE_INTERPOLATION,
    USE_SPREAD_CYCLE, DEFAULT_LOGGING_LEVEL, USE_DUMMY_DRIVER
)

from dip_coater.widgets.tabs.main_tab import MainTab
from dip_coater.widgets.tabs.logs_tab import LogsTab
from dip_coater.widgets.tabs.advanced_settings_tab import AdvancedSettingsTab
from dip_coater.widgets.tabs.coder_tab import CoderTab

from dip_coater.motor.mechanical_setup import MechanicalSetup
from dip_coater.motor.motor_driver_interface import MotorDriver
from dip_coater.motor.tmc2209 import TMC2209_MotorDriver
from dip_coater.motor.tmc2660 import TMC2660_MotorDriver


def create_motor_driver(driver_type: str, app_state, log_level: Loglevel, log_handlers,
                        log_formatter,
                        interface_type="usb_tmcl", port="interactive") -> MotorDriver:
    if driver_type == "TMC2209":
        return TMC2209_MotorDriver(app_state, step_mode=STEP_MODES[DEFAULT_STEP_MODE],
                                   current_ma=DEFAULT_CURRENT,
                                   invert_direction=INVERT_MOTOR_DIRECTION,
                                   interpolation=USE_INTERPOLATION,
                                   spread_cycle=USE_SPREAD_CYCLE,
                                   loglevel=log_level,
                                   log_handlers=log_handlers,
                                   log_formatter=log_formatter)
    elif driver_type == "TMC2660":
        if USE_DUMMY_DRIVER:
            interface_type = "dummy_tmcl"
            port = None
        return TMC2660_MotorDriver(app_state,
                                   interface_type=interface_type,
                                   port=port,
                                   loglevel=log_level,
                                   log_handlers=log_handlers,
                                   log_formatter=log_formatter)
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

    def __init__(self, driver_type: str, mechanical_setup: MechanicalSetup,
                 log_level: Loglevel = Loglevel.INFO):
        super().__init__()
        app_state.motor_logger_widget = RichLog(markup=True, id="motor-logger")
        app_state.mechanical_setup = mechanical_setup
        motor_logger_handler = MotorLoggerHandler(app_state)
        logging_format = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s",
                                           "%Y%m%d %H:%M:%S")
        app_state.motor_driver = create_motor_driver(driver_type, app_state, log_level,
                                                     [motor_logger_handler], logging_format)

    def on_mount(self):
        # on_mount() is called after compose(), so the RichLog is known
        log = self.query_one("#logger", RichLog)
        log.write("Motor has been initialised.")

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Footer()
        with TabbedContent(initial="main-tab", id="tabbed-content"):
            yield MainTab(app_state)
            yield LogsTab(app_state)
            yield AdvancedSettingsTab(app_state)
            yield CoderTab(app_state)

    @on(Button.Pressed, "#reset-to-defaults-btn")
    def reset_to_defaults(self):
        app_state.advanced_settings.reset_settings_to_default()

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark

    def action_request_quit(self) -> None:
        app_state.motor_driver.cleanup()
        self.app.exit()

    def action_show_help(self) -> None:
        self.push_screen(HelpScreen())

    async def action_move_up(self) -> None:
        await app_state.motor_controls.move_up_action()

    async def action_move_down(self) -> None:
        await app_state.motor_controls.move_down_action()

    async def action_enable_motor(self) -> None:
        await app_state.motor_controls.enable_motor_action()

    async def action_disable_motor(self) -> None:
        await app_state.motor_controls.disable_motor_action()


def main():
    parser = argparse.ArgumentParser(description='Process logging level and motor driver type.')
    parser.add_argument('-l', '--log-level', type=str,
                        default=DEFAULT_LOGGING_LEVEL.name,
                        choices=['NONE', 'ERROR', 'INFO', 'DEBUG', 'MOVEMENT', 'ALL'],
                        help='Set the logging level')
    parser.add_argument('-d', '--driver', type=str, default="TMC2209",
                        choices=['TMC2209', 'TMC2660'],
                        help='Set the motor driver type')
    parser.add_argument('--mm-per-revolution', type=float, default=4.0,
                        help='Distance in mm the platform moves for one full revolution')
    parser.add_argument('--gearbox-ratio', type=float, default=1.0,
                        help='Gearbox ratio, if any')

    args = parser.parse_args()

    mechanical_setup = MechanicalSetup(
        mm_per_revolution=args.mm_per_revolution,
        gearbox_ratio=args.gearbox_ratio
    )

    # Convert string level to the appropriate value in your Loglevel enum
    log_level = getattr(Loglevel, args.log_level)

    package_version = version("dip-coater")
    print(f"Starting Dip Coater v{package_version}, driver: {args.driver}, log level: {log_level}")
    app = DipCoaterApp(args.driver, mechanical_setup, log_level)
    app.title = f"Dip Coater v{package_version}"
    app.run()


if __name__ == '__main__':
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    main()
