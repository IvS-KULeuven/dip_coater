import asyncio
import concurrent.futures
import time
from importlib.util import find_spec
from pathlib import Path

from textual import on, events
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.validation import Function
from textual.widgets import (
    Static,
    Label,
    TextArea,
    Button,
    Input,
    Markdown,
    Collapsible,
    TabbedContent,
    RichLog,
)

from dip_coater.widgets.position_controls import PositionControls
from dip_coater.utils.helpers import (
    config_load_coder_filepath,
    config_save_coder_filepath,
)


class CoderExecutionCancelled(RuntimeError):
    """Raised when a running Coder script is stopped by the operator."""


class Coder(Static):
    code = ""

    def __init__(self, app_state):
        super().__init__()
        self.app_state = app_state
        self._app_loop: asyncio.AbstractEventLoop | None = None
        self._stop_requested = False
        self._is_executing = False

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(
                "Enter your Coder API code below and press 'RUN code' to execute it."
            )
            with Collapsible(
                title="View Coder API", collapsed=True, id="coder-api-collapsible"
            ):
                with open(Path(__file__).parent.parent / "coder_API.md") as text:
                    md = Markdown(
                        text.read(),
                        id="coder-api-markdown",
                    )
                    md.code_dark_theme = "monokai"
                    yield md
            yield self.build_code_editor('print("Hello, World!")')
            with Horizontal(id="run-and-load-code-container"):
                yield Button(
                    "RUN code",
                    id="run-code-btn",
                    variant="success",
                )
                yield Button(
                    "STOP code",
                    id="stop-code-btn",
                    variant="error",
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
                        validators=[
                            Function(
                                self.is_file_path_valid_python,
                                "File path does not point to valid Python (.py) file",
                            )
                        ],
                    )
                    yield Label("", id="coder-path-invalid-reasons")

    def _on_mount(self, event: events.Mount) -> None:
        config_file_path = config_load_coder_filepath(self.app_state)
        self.query_one("#code-file-path-input", Input).value = config_file_path
        self.load_code_from_file(config_file_path)
        self._set_execution_controls_running(False)

    @staticmethod
    def build_code_editor(text: str) -> TextArea:
        editor_kwargs = {
            "theme": "monokai",
            "show_line_numbers": True,
            "tab_behavior": "indent",
            "id": "code-editor",
        }
        if Coder._python_syntax_highlighting_available():
            try:
                return TextArea(text, language="python", **editor_kwargs)
            except Exception:
                pass
        return TextArea(
            text,
            language=None,
            **editor_kwargs,
        )

    @staticmethod
    def _python_syntax_highlighting_available() -> bool:
        if (
            find_spec("tree_sitter") is None
            or find_spec("tree_sitter_python") is None
        ):
            return False

        try:
            return TextArea("pass\n", language="python").is_syntax_aware
        except Exception:
            return False

    @on(Button.Pressed, "#run-code-btn")
    async def run_code(self):
        if self._is_executing:
            self.app.query_one("#logger", RichLog).write(
                "[dark_orange]Coder script is already running.[/]"
            )
            return
        self.code = self.app.query_one("#code-editor", TextArea).text
        tabbed_content = self.app.query_one("#tabbed-content", TabbedContent)
        tabbed_content.active = "main-tab"
        await asyncio.sleep(0.1)
        await self.exec_code_async()

    @on(Button.Pressed, "#stop-code-btn")
    async def stop_code(self):
        self.request_stop()
        log = self.app.query_one("#logger", RichLog)
        log.write("[dark_orange]Stopping Coder script...[/]")
        await self.app_state.motor_controls.disable_motor_action()

    def set_editor_text(self, text: str):
        self.query_one("#code-editor", TextArea).text = text

    @on(Input.Changed)
    def show_invalid_reasons(self, event: Input.Changed) -> None:
        validation_result = event.validation_result
        path_status = self.query_one("#coder-path-invalid-reasons", Label)
        if event.input.value == "":
            path_status.update("[green]Using default code[/]")
        elif validation_result is not None and not validation_result.is_valid:
            path_status.update(f"[red]{validation_result.failure_descriptions}[/]")
        else:
            path_status.update("[green]Valid Python file[/]")

    @staticmethod
    def is_file_path_valid_python(file_path: str) -> bool:
        # Default code is allowed
        if file_path is None or file_path == "":
            return True
        path = Path(file_path).expanduser()
        return path.is_file() and path.suffix == ".py"

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
        try:
            with open(Path(file_path).expanduser()) as text:
                self.set_editor_text(text.read())
        except OSError as e:
            self.query_one("#coder-path-invalid-reasons", Label).update(
                f"[red]Could not load file: {e}[/]"
            )

    def load_default_code(self):
        file_path = Path(__file__).parent.parent / "code_editor_init_content.py"
        self.load_code_into_editor(file_path)

    async def exec_code_async(self):
        log = self.app.query_one("#logger", RichLog)
        self._app_loop = asyncio.get_running_loop()
        self._stop_requested = False
        self._is_executing = True
        self._set_execution_controls_running(True)
        try:
            log.write("[blue]Executing code >>>>>>>>>>>>[/]")
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self.exec_code)
            log.write("[dark_cyan]>>>>>>>>>>>> Code finished.[/]")
        except CoderExecutionCancelled as e:
            log.write(f"[dark_orange]{e}[/]")
        except Exception as e:
            log.write(f"[red]Error executing code: {e}[/]")
            raise e
        finally:
            self._is_executing = False
            self._app_loop = None
            self._set_execution_controls_running(False)

    def exec_code(self):
        self._raise_if_stop_requested()
        namespace = {"self": self}
        exec(self.code, namespace, namespace)
        self._raise_if_stop_requested()

    def _set_execution_controls_running(self, running: bool) -> None:
        for button_id, disabled in (
            ("#run-code-btn", running),
            ("#stop-code-btn", not running),
        ):
            try:
                self.query_one(button_id, Button).disabled = disabled
            except Exception:
                pass

    def request_stop(self) -> None:
        self._stop_requested = True

    def _raise_if_stop_requested(
        self,
        future: concurrent.futures.Future | None = None,
    ) -> None:
        if not self._stop_requested:
            return
        if future is not None:
            future.cancel()
        raise CoderExecutionCancelled("Coder execution stopped.")

    def async_run(self, func, *args):
        self._raise_if_stop_requested()
        if self._app_loop is None:
            asyncio.run(func(*args))
            return

        future = asyncio.run_coroutine_threadsafe(func(*args), self._app_loop)
        while True:
            self._raise_if_stop_requested(future)
            try:
                return future.result(timeout=0.05)
            except concurrent.futures.TimeoutError:
                continue

    def _write_log_from_script(self, message: str) -> None:
        if self._app_loop is None:
            return

        def write() -> None:
            self.app.query_one("#logger", RichLog).write(message)

        self._app_loop.call_soon_threadsafe(write)

    """ ========== API for the code editor ========== """

    def enable_motor(self):
        self.async_run(self.app_state.motor_controls.enable_motor_action)

    def disable_motor(self):
        self.async_run(self.app_state.motor_controls.disable_motor_action)

    def move_up(
        self, distance_mm: float, speed_mm_s: float, acceleration_mm_s2: float = None
    ):
        # NOTE: We are purposely not changing the distance, speed and acceleration settings here,
        # as this may be undesirable in some cases.
        self.async_run(
            self.app_state.motor_controls.move_up,
            distance_mm,
            speed_mm_s,
            acceleration_mm_s2,
        )

    def move_down(
        self, distance_mm: float, speed_mm_s: float, acceleration_mm_s2: float = None
    ):
        # NOTE: We are purposely not changing the distance, speed and acceleration settings here,
        # as this may be undesirable in some cases.
        self.async_run(
            self.app_state.motor_controls.move_down,
            distance_mm,
            speed_mm_s,
            acceleration_mm_s2,
        )

    def home_motor(self, home_up: bool = None):
        self.async_run(self.app_state.motor_controls.perform_homing, home_up)

    def move_to_position(
        self,
        position_mm: float,
        speed_mm_s: float = None,
        acceleration_mm_s2: float = None,
        home_up: bool = None,
    ):
        self.async_run(
            self._move_to_position_async,
            position_mm,
            speed_mm_s,
            acceleration_mm_s2,
            home_up,
        )

    async def _move_to_position_async(
        self,
        position_mm: float,
        speed_mm_s: float,
        acceleration_mm_s2: float = None,
        home_up: bool = None,
    ):
        await self.app.query_one(PositionControls).move_to_position(
            position_mm,
            speed_mm_s,
            acceleration_mm_s2,
            home_up,
        )

    def sleep(self, seconds: float):
        self._raise_if_stop_requested()
        self._write_log_from_script(f"[cyan]...Sleeping for {seconds} seconds...[/]")
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            self._raise_if_stop_requested()
            remaining_s = deadline - time.monotonic()
            if remaining_s <= 0:
                break
            time.sleep(min(0.1, remaining_s))
