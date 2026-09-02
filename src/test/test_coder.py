import asyncio
import inspect
import threading
import time
from types import SimpleNamespace

import pytest
from textual.widgets import TextArea

from dip_coater.widgets import coder as coder_module
from dip_coater.widgets.coder import Coder, CoderExecutionCancelled


class FakeMotorControls:
    def __init__(self):
        self.enabled = False
        self.moves = []
        self.loop = None

    async def enable_motor_action(self):
        self.loop = asyncio.get_running_loop()
        self.enabled = True

    async def disable_motor_action(self):
        self.loop = asyncio.get_running_loop()
        self.enabled = False

    async def move_up(self, distance_mm, speed_mm_s, acceleration_mm_s2=None):
        self.loop = asyncio.get_running_loop()
        self.moves.append(("up", distance_mm, speed_mm_s, acceleration_mm_s2))


@pytest.mark.asyncio
async def test_coder_api_schedules_motor_commands_on_app_loop_from_worker_thread():
    app_loop = asyncio.get_running_loop()
    motor_controls = FakeMotorControls()
    coder = Coder(SimpleNamespace(motor_controls=motor_controls))
    coder._app_loop = app_loop

    await asyncio.to_thread(coder.enable_motor)

    assert motor_controls.enabled is True
    assert motor_controls.loop is app_loop


def test_coder_api_refuses_new_commands_after_stop_request():
    motor_controls = FakeMotorControls()
    coder = Coder(SimpleNamespace(motor_controls=motor_controls))

    coder.request_stop()

    with pytest.raises(CoderExecutionCancelled):
        coder.move_up(1.0, 1.0)

    assert motor_controls.moves == []


def test_coder_stop_interrupts_plain_python_loop_promptly():
    coder = Coder(SimpleNamespace(motor_controls=FakeMotorControls()))
    loop_started = threading.Event()
    coder.loop_started = loop_started
    coder.code = (
        "import time\n"
        "self.loop_started.set()\n"
        "deadline = time.monotonic() + 1.0\n"
        "while time.monotonic() < deadline:\n"
        "    pass\n"
    )
    errors = []

    def execute():
        try:
            coder.exec_code()
        except BaseException as error:
            errors.append(error)

    worker = threading.Thread(target=execute, daemon=True)
    worker.start()
    assert loop_started.wait(timeout=0.5)

    started_stopping = time.monotonic()
    coder.request_stop()
    worker.join(timeout=0.2)

    assert not worker.is_alive()
    assert time.monotonic() - started_stopping < 0.2
    assert len(errors) == 1
    assert isinstance(errors[0], CoderExecutionCancelled)


@pytest.mark.asyncio
async def test_coder_script_error_is_logged_without_escaping_ui_handler():
    messages = []

    def fail_script():
        raise RuntimeError("script failed")

    coder = SimpleNamespace(
        _app_loop=None,
        _stop_requested=False,
        _is_executing=False,
        app=SimpleNamespace(
            query_one=lambda *_args, **_kwargs: SimpleNamespace(
                write=messages.append
            )
        ),
        exec_code=fail_script,
        _set_execution_controls_running=lambda _running: None,
    )

    await Coder.exec_code_async(coder)

    assert coder._is_executing is False
    assert coder._app_loop is None
    assert messages[-1] == "[red]Error executing code: script failed[/]"


def test_coder_move_to_position_allows_default_speed():
    signature = inspect.signature(Coder.move_to_position)

    assert signature.parameters["speed_mm_s"].default is None


@pytest.mark.skipif(
    not Coder._python_syntax_highlighting_available(),
    reason="Python syntax highlighting packages are optional",
)
def test_coder_builds_python_highlighted_editor():
    editor = Coder.build_code_editor('def coat():\n    print("Hello, World!")\n')

    assert isinstance(editor, TextArea)
    assert editor.language == "python"
    assert editor.theme == "monokai"
    assert editor.show_line_numbers is True
    assert editor.tab_behavior == "indent"
    assert getattr(editor, "_highlight_query", None) is not None
    assert editor._highlights


def test_coder_editor_falls_back_to_plain_text_without_syntax_packages(monkeypatch):
    monkeypatch.setattr(
        Coder,
        "_python_syntax_highlighting_available",
        staticmethod(lambda: False),
    )

    editor = Coder.build_code_editor('def coat():\n    print("Hello, World!")\n')

    assert isinstance(editor, TextArea)
    assert editor.language is None
    assert editor.theme == "monokai"
    assert editor.show_line_numbers is True
    assert editor.tab_behavior == "indent"
    assert getattr(editor, "_highlight_query", None) is None


def test_coder_editor_falls_back_to_plain_text_when_syntax_setup_fails(monkeypatch):
    real_text_area = coder_module.TextArea

    def text_area_with_broken_syntax(*args, **kwargs):
        if kwargs.get("language") == "python":
            raise RuntimeError("syntax setup failed")
        return real_text_area(*args, **kwargs)

    monkeypatch.setattr(
        Coder,
        "_python_syntax_highlighting_available",
        staticmethod(lambda: True),
    )
    monkeypatch.setattr(coder_module, "TextArea", text_area_with_broken_syntax)

    editor = Coder.build_code_editor('def coat():\n    print("Hello, World!")\n')

    assert isinstance(editor, TextArea)
    assert editor.language is None
    assert editor.theme == "monokai"
    assert editor.show_line_numbers is True
    assert editor.tab_behavior == "indent"
    assert getattr(editor, "_highlight_query", None) is None
