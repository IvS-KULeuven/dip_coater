import asyncio
from pathlib import Path

from textual import on, events
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.validation import Function
from textual.widgets import Static, Label, TextArea, Button, Input, Markdown, Collapsible, TabbedContent, RichLog

from dip_coater.widgets.position_controls import PositionControls
from dip_coater.utils.helpers import config_load_coder_filepath, config_save_coder_filepath


class Coder(Static):
    code = ""

    def __init__(self, app_state):
        super().__init__()
        self.app_state = app_state

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Enter your Coder API code below and press 'RUN code' to execute it.")
            with Collapsible(title="View Coder API", collapsed=True, id="coder-api-collapsible"):
                with open(Path(__file__).parent.parent / "coder_API.md") as text:
                    md = Markdown(
                        text.read(),
                        id="coder-api-markdown",
                    )
                    md.code_dark_theme = "monokai"
                    yield md
            yield TextArea(
                "print(\"Hello, World!\")",
                language="python",
                show_line_numbers=True,
                id="code-editor",
            )
            with Horizontal(id="run-and-load-code-container"):
                yield Button(
                    "RUN code",
                    id="run-code-btn",
                    variant="success",
                )
                yield Button(
                    "LOAD code from file",
                    id="load-code-btn",
                )
                with Vertical(id="coder-path-input-container"):
                    yield Input(
                        value="<dummy input>",
                        type="text",
                        placeholder="Input file path to python code, or empty for default code",
                        id="code-file-path-input",
                        validate_on=["changed"],
                        validators=[Function(self.is_file_path_valid_python,
                                             "File path does not point to valid Python (.py) file")],
                    )
                    yield Label("", id="coder-path-invalid-reasons")

    def _on_mount(self, event: events.Mount) -> None:
        config_file_path = config_load_coder_filepath(self.app_state)
        self.query_one("#code-file-path-input", Input).value = config_file_path
        self.load_code_from_file(config_file_path)

    @on(Button.Pressed, "#run-code-btn")
    async def run_code(self):
        self.code = self.app.query_one("#code-editor", TextArea).text
        tabbed_content = self.app.query_one("#tabbed-content", TabbedContent)
        tabbed_content.active = "main-tab"
        await asyncio.sleep(0.1)
        await self.exec_code_async()

    def set_editor_text(self, text: str):
        self.query_one("#code-editor", TextArea).text = text

    @on(Input.Changed)
    def show_invalid_reasons(self, event: Input.Changed) -> None:
        # Updating the UI to show the reasons why validation failed
        if not event.validation_result.is_valid:
            (self.query_one("#coder-path-invalid-reasons", Label)
                .update(f"[red]{event.validation_result.failure_descriptions}[/]"))
        else:
            (self.query_one("#coder-path-invalid-reasons", Label)
                .update("[green]Valid file path[/]"))

    @staticmethod
    def is_file_path_valid_python(file_path: str) -> bool:
        # Default code is allowed
        if file_path is None or file_path == "":
            return True
        return Path(file_path).suffix == ".py"

    @on(Input.Submitted, "#code-file-path-input")
    @on(Button.Pressed, "#load-code-btn")
    def submit_speed_input(self):
        file_path_input = self.query_one("#code-file-path-input", Input)
        file_path = file_path_input.value

        if not self.is_file_path_valid_python(file_path):
            return

        self.load_code_from_file(file_path)
        config_save_coder_filepath(self.app_state, file_path)

    def load_code_from_file(self, file_path: str):
        if file_path is None or file_path == "":
            self.load_default_code()
        else:
            self.load_code_into_editor(file_path)

    def load_code_into_editor(self, file_path):
        with open(file_path) as text:
            self.set_editor_text(text.read())

    def load_default_code(self):
        file_path = Path(__file__).parent.parent / "code_editor_init_content.py"
        self.load_code_into_editor(file_path)

    async def exec_code_async(self):
        log = self.app.query_one("#logger", RichLog)
        try:
            log.write("[blue]Executing code >>>>>>>>>>>>[/]")
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self.exec_code)
            log.write("[dark_cyan]>>>>>>>>>>>> Code finished.[/]")
        except Exception as e:
            log.write(f"[red]Error executing code: {e}[/]")
            raise e

    def exec_code(self):
        exec(self.code)

    @staticmethod
    def async_run(func, *args):
        async def run():
            await func(*args)
        asyncio.run(run())

    ''' ========== API for the code editor ========== '''

    def enable_motor(self):
        self.async_run(self.app_state.motor_controls.enable_motor_action)

    def disable_motor(self):
        self.async_run(self.app_state.motor_controls.disable_motor_action)

    def move_up(self, distance_mm: float, speed_mm_s: float, acceleration_mm_s2: float = None):
        # NOTE: We are purposely not changing the distance, speed and acceleration settings here,
        # as this may be undesirable in some cases.
        self.async_run(self.app_state.motor_controls.move_up, distance_mm, speed_mm_s,
                       acceleration_mm_s2)

    def move_down(self, distance_mm: float, speed_mm_s: float, acceleration_mm_s2: float = None):
        # NOTE: We are purposely not changing the distance, speed and acceleration settings here,
        # as this may be undesirable in some cases.
        self.async_run(self.app_state.motor_controls.move_down, distance_mm, speed_mm_s,
                       acceleration_mm_s2)

    def home_motor(self, home_up: bool = None):
        if home_up is None:
            home_up = self.app_state.config.HOME_UP
        self.async_run(self.app_state.motor_controls.perform_homing, home_up)

    def move_to_position(self, position_mm: float, speed_mm_s: float,
                         acceleration_mm_s2: float = None, home_up: bool = None):
        if home_up is None:
            home_up = self.app_state.config.HOME_UP
        self.async_run(self.app.query_one(PositionControls).move_to_position, position_mm,
                       speed_mm_s, acceleration_mm_s2, home_up)

    def sleep(self, seconds: float):
        log = self.app.query_one("#logger", RichLog)
        log.write(f"[cyan]...Sleeping for {seconds} seconds...[/]")
        self.async_run(asyncio.sleep, seconds)
