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
        self.app_state.status = Status(self.app_state.motor_driver, id="status")
        self.app_state.speed_controls = SpeedControls(self.app_state)
        self.app_state.distance_controls = DistanceControls(self.app_state)
        self.app_state.position_controls = PositionControls(self.app_state)
        self.app_state.motor_controls = MotorControls(self.app_state)

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical(id="left-side"):
                yield self.app_state.speed_controls
                yield self.app_state.distance_controls
                yield self.app_state.position_controls
                yield self.app_state.motor_controls
                yield RichLog(markup=True, id="logger")
            with Vertical(id="right-side"):
                yield self.app_state.status
