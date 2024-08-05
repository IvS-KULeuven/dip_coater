from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import TabPane, Label, Select
from textual import on

from TMC_2209._TMC_2209_logger import Loglevel
from dip_coater.logging.tmc2660_logger import TMC2660LogLevel

from dip_coater.motor.motor_driver_interface import AvailableMotorDrivers


class LogsTab(TabPane):
    def __init__(self, app_state):
        super().__init__("Logs", id="logs-tab")
        self.app_state = app_state

    def compose(self) -> ComposeResult:
        with Vertical():
            with Horizontal():
                yield Label("Logging level: ", id="logging-level-label")
                options = self.create_log_level_options()
                yield Select(options,
                             value=self.get_current_log_level(),
                             allow_blank=False,
                             name="Select logging level",
                             id="logging-level-select")
            yield self.app_state.motor_logger_widget

    def create_log_level_options(self) -> list:
        if self.app_state.driver_type == AvailableMotorDrivers.TMC2209:
            return [(level.name, level.name) for level in Loglevel]
        elif self.app_state.driver_type == AvailableMotorDrivers.TMC2660:
            return [(level.name, level.name) for level in TMC2660LogLevel]
        else:
            return []

    def get_current_log_level(self) -> str:
        if self.app_state.driver_type == AvailableMotorDrivers.TMC2209:
            return self.app_state.config.DEFAULT_LOGGING_LEVEL.name
        elif self.app_state.driver_type == AvailableMotorDrivers.TMC2660:
            return self.app_state.config.DEFAULT_LOGGING_LEVEL.name
        else:
            return "INFO"

    @on(Select.Changed, "#logging-level-select")
    def action_set_loglevel(self, event: Select.Changed):
        if self.app_state.driver_type == AvailableMotorDrivers.TMC2209:
            level = Loglevel[event.value]
        elif self.app_state.driver_type == AvailableMotorDrivers.TMC2660:
            level = TMC2660LogLevel[event.value]
        else:
            return
        self.set_loglevel(level)

    def set_loglevel(self, level):
        self.app_state.motor_driver.set_loglevel(level)

    def reset_settings_to_default(self):
        default_level = self.get_current_log_level()
        self.query_one("#logging-level-select", Select).value = default_level
        if self.app_state.driver_type == AvailableMotorDrivers.TMC2209:
            self.set_loglevel(Loglevel[default_level])
        elif self.app_state.driver_type == AvailableMotorDrivers.TMC2660:
            self.set_loglevel(TMC2660LogLevel[default_level])
