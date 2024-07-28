from textual.app import ComposeResult
from textual.widgets import TabPane

from dip_coater.widgets.coder import Coder

class CoderTab(TabPane):
    def __init__(self):
        super().__init__("Coder", id="coder-tab")

    def compose(self) -> ComposeResult:
        yield Coder()
