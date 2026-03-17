from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import TabPane, Label, Select
from textual import on

from dip_coater.motor_driver.driver_registry import get_driver_spec


class LogsTab(TabPane):
    def __init__(self, app_state):
        super().__init__("Logs", id="logs-tab")
        self.app_state = app_state
        self.driver_spec = get_driver_spec(self.app_state.driver_type)

    def compose(self) -> ComposeResult:
        with Vertical():
            with Horizontal():
                yield Label("Logging level: ", id="logging-level-label")
                options = self.create_log_level_options()
                yield Select(
                    options,
                    value=self.get_current_log_level(),
                    allow_blank=False,
                    name="Select logging level",
                    id="logging-level-select",
                )
            yield self.app_state.motor_logger_widget

    def create_log_level_options(self) -> list:
        return self.driver_spec.log_level_options()

    def get_current_log_level(self) -> str:
        return self.app_state.config.DEFAULT_LOGGING_LEVEL.name

    @on(Select.Changed, "#logging-level-select")
    def action_set_loglevel(self, event: Select.Changed):
        level = self.driver_spec.log_level_from_name(event.value)
        self.set_loglevel(level)

    def set_loglevel(self, level):
        self.app_state.motor_driver.set_loglevel(level)

    def reset_settings_to_default(self):
        default_level = self.get_current_log_level()
        self.query_one("#logging-level-select", Select).value = default_level
        self.set_loglevel(self.driver_spec.log_level_from_name(default_level))
