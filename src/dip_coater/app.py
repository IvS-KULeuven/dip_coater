import argparse
import logging

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Footer, Header, RichLog, TabPane, TabbedContent
from textual.binding import Binding
from importlib.metadata import version

try:
    import TMC_2209
except ModuleNotFoundError:
    import sys
    import MyTMC_2209 as TMC_2209
    sys.modules["TMC_2209"] = TMC_2209

from TMC_2209._TMC_2209_logger import Loglevel
from dip_coater.motor.tmc2209 import TMC2209_MotorDriver
from dip_coater.app_state import app_state
from dip_coater.gpio import get_gpio_instance

from dip_coater.widgets.advanced_settings import AdvancedSettings
from dip_coater.widgets.coder import Coder
from dip_coater.widgets.distance_controls import DistanceControls
from dip_coater.widgets.motor_controls import MotorControls
from dip_coater.widgets.position_controls import PositionControls
from dip_coater.widgets.speed_controls import SpeedControls
from dip_coater.widgets.status import Status
from dip_coater.widgets.status_advanced import StatusAdvanced
from dip_coater.logging.motor_logger import MotorLoggerHandler
from dip_coater.commands.help_command import HelpCommand
from dip_coater.screens.help_screen import HelpScreen
from dip_coater.constants import (
    STEP_MODES, DEFAULT_STEP_MODE, DEFAULT_CURRENT, INVERT_MOTOR_DIRECTION, USE_INTERPOLATION, USE_SPREAD_CYCLE,
    DEFAULT_LOGGING_LEVEL
)


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

    def __init__(self, log_level: Loglevel = Loglevel.INFO):
        super().__init__()
        self.GPIO = get_gpio_instance()
        self.motor_logger_widget = RichLog(markup=True, id="motor-logger")
        motor_logger_handler = MotorLoggerHandler(self.motor_logger_widget)
        logging_format = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", "%Y%m%d %H:%M:%S")
        app_state.motor_driver = TMC2209_MotorDriver(self.GPIO, stepmode=STEP_MODES[DEFAULT_STEP_MODE],
                                                current=DEFAULT_CURRENT,
                                                invert_direction=INVERT_MOTOR_DIRECTION,
                                                interpolation=USE_INTERPOLATION,
                                                spread_cycle=USE_SPREAD_CYCLE,
                                                loglevel=log_level,
                                                log_handlers=[motor_logger_handler],
                                                log_formatter=logging_format)

    def on_mount(self):
        # on_mount() is called after compose(), so the RichLog is known
        log = self.query_one("#logger", RichLog)
        log.write("Motor has been initialised.")

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Footer()
        with TabbedContent(initial="main-tab", id="tabbed-content"):
            with TabPane("Main", id="main-tab"):
                with Horizontal():
                    with Vertical(id="left-side"):
                        yield SpeedControls()
                        yield DistanceControls()
                        yield PositionControls(app_state.motor_driver)
                        yield MotorControls(self.GPIO, app_state.motor_driver)
                        yield RichLog(markup=True, id="logger")
                    with Vertical(id="right-side"):
                        yield Status(app_state.motor_driver, id="status")
            with TabPane("Advanced", id="advanced-tab"):
                with Horizontal():
                    with Vertical(id="left-side-advanced"):
                        yield AdvancedSettings(app_state.motor_driver)
                        yield self.motor_logger_widget
                    with Vertical(id="right-side-advanced"):
                        yield StatusAdvanced(id="status-advanced")
                        yield Button("Reset to defaults", id="reset-to-defaults-btn", variant="error")
            with TabPane("Coder", id="coder-tab"):
                yield Coder()

    @on(Button.Pressed, "#reset-to-defaults-btn")
    def reset_to_defaults(self):
        self.query_one(AdvancedSettings).reset_settings_to_default()

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark

    def action_request_quit(self) -> None:
        app_state.motor_driver.cleanup()
        self.app.exit()

    def action_show_help(self) -> None:
        self.push_screen(HelpScreen())

    async def action_move_up(self) -> None:
        await self.query_one(MotorControls).move_up_action()

    async def action_move_down(self) -> None:
        await self.query_one(MotorControls).move_down_action()

    async def action_enable_motor(self) -> None:
        await self.query_one(MotorControls).enable_motor_action()

    async def action_disable_motor(self) -> None:
        await self.query_one(MotorControls).disable_motor_action()


def main():
    parser = argparse.ArgumentParser(description='Process logging level.')
    parser.add_argument('-l', '--log-level', type=str, default=DEFAULT_LOGGING_LEVEL.name,
                        choices=['NONE', 'ERROR', 'INFO', 'DEBUG', 'MOVEMENT', 'ALL'],
                        help='Set the logging level')
    args = parser.parse_args()

    # Convert string level to the appropriate value in your Loglevel enum
    log_level = getattr(Loglevel, args.log_level)

    app = DipCoaterApp(log_level)
    package_version = version("dip-coater")
    app.title = f"Dip Coater v{package_version}"
    app.run()


if __name__ == '__main__':
    main()
