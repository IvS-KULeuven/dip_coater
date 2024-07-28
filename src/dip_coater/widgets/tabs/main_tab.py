from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import RichLog, TabPane

from dip_coater.widgets.distance_controls import DistanceControls
from dip_coater.widgets.position_controls import PositionControls
from dip_coater.widgets.speed_controls import SpeedControls
from dip_coater.widgets.status import Status
from dip_coater.widgets.motor_controls import MotorControls


class MainTab(TabPane):
    def __init__(self, app_state):
        super().__init__("Main", id="main-tab")
        self.app_state = app_state


    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical(id="left-side"):
                yield SpeedControls()
                yield DistanceControls()
                yield PositionControls(self.app_state.motor_driver)
                yield MotorControls(self.app_state.gpio, self.app_state.motor_driver)
                yield RichLog(markup=True, id="logger")
            with Vertical(id="right-side"):
                yield Status(self.app_state.motor_driver, id="status")
