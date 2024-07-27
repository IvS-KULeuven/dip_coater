from pathlib import Path

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Container
from textual.widgets import MarkdownViewer

class HelpScreen(ModalScreen[None]):
    BINDINGS = [("escape", "pop_screen", "Close the help screen")]

    def compose(self) -> ComposeResult:
        with Container(id="help-container"):
            with open(Path(__file__).parent / "help.md") as text:
                yield MarkdownViewer(text.read(), show_table_of_contents=False)
