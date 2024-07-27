from pathlib import Path

from textual import on
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Container
from textual.widgets import MarkdownViewer, Button

class HelpScreen(ModalScreen[None]):
    BINDINGS = [("escape", "app.pop_screen", "Close")]

    def compose(self) -> ComposeResult:
        with Container(id="help-container"):
            yield Button("Close", id="close-help", classes="btn-small", variant="primary")
            with open(Path(__file__).parent.parent / "help.md") as text:
                yield MarkdownViewer(text.read(), show_table_of_contents=False)

    @on(Button.Pressed, "#close-help")
    def close_help(self):
        self.app.pop_screen()

    def action_app_pop_screen(self):
        self.app.pop_screen()
