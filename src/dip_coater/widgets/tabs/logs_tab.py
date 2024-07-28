from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import TabPane, Label, Select
from textual import on

from TMC_2209._TMC_2209_logger import Loglevel
from dip_coater.constants import DEFAULT_LOGGING_LEVEL

class LogsTab(TabPane):
    def __init__(self, app_state, motor_logger_widget):
        super().__init__("Logs", id="logs-tab")
        self.app_state = app_state
        self.motor_logger_widget = motor_logger_widget

    def compose(self) -> ComposeResult:
        with Vertical():
            with Horizontal():
                yield Label("Logging level: ", id="logging-level-label")
                options = self.create_log_level_options()
                yield Select(options,
                             value=DEFAULT_LOGGING_LEVEL.value,
                             allow_blank=False,
                             name="Select logging level",
                             id="logging-level-select")
            yield self.motor_logger_widget

    @staticmethod
    def create_log_level_options() -> list:
        options = []
        for level in Loglevel:
            options.append((level.name, level.value))
        return options

    @on(Select.Changed, "#logging-level-select")
    def action_set_loglevel(self, event: Select.Changed):
        level = Loglevel(event.value)
        self.set_loglevel(level)

    def set_loglevel(self, level: Loglevel):
        self.app_state.motor_driver.set_loglevel(level)

    def reset_settings_to_default(self):
        self.query_one("#logging-level-select", Select).value = DEFAULT_LOGGING_LEVEL.value
