import asyncio
from types import SimpleNamespace

import pytest
from textual.widgets import TextArea

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


def test_coder_builds_python_highlighted_editor():
    editor = Coder.build_code_editor('def coat():\n    print("Hello, World!")\n')

    assert isinstance(editor, TextArea)
    assert editor.language == "python"
    assert editor.theme == "monokai"
    assert editor.show_line_numbers is True
    assert editor.tab_behavior == "indent"
    assert getattr(editor, "_highlight_query", None) is not None
    assert editor._highlights
