from textual.app import ComposeResult
from textual.widgets import TabPane

from dip_coater.widgets.coder import Coder

class CoderTab(TabPane):
    def __init__(self, app_state):
        super().__init__("Coder", id="coder-tab")
        self.app_state = app_state

    def compose(self) -> ComposeResult:
        yield Coder(self.app_state)
