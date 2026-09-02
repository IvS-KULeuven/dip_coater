import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from dip_coater import __version__
from dip_coater import app as app_module
from dip_coater.app import DipCoaterApp, main


def test_cli_version_prints_package_version(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["dip-coater", "--version"])

    with pytest.raises(SystemExit) as exit_info:
        main()

    assert exit_info.value.code == 0
    assert capsys.readouterr().out == f"{__version__}\n"


class FakeMotionController:
    def __init__(self):
        self.cleanup_calls = 0

    def cleanup(self):
        self.cleanup_calls += 1


class QuitActionHarness:
    action_request_quit = DipCoaterApp.action_request_quit
    action_quit = DipCoaterApp.action_quit

    def __init__(self):
        self.app_state = SimpleNamespace(motion_controller=FakeMotionController())
        self.exit_calls = 0

    def exit(self):
        self.exit_calls += 1


@pytest.mark.parametrize("action_name", ["action_request_quit", "action_quit"])
def test_all_quit_actions_cleanup_before_exit(action_name):
    app = QuitActionHarness()

    getattr(app, action_name)()

    assert app.app_state.motion_controller.cleanup_calls == 1
    assert app.exit_calls == 1


def test_run_app_cleans_up_when_textual_app_raises(monkeypatch):
    controller = FakeMotionController()
    app_state = SimpleNamespace(
        motion_controller=controller,
        config=SimpleNamespace(USE_DUMMY_DRIVER=False),
    )

    class FailingApp:
        def __init__(self, _app_state):
            self.title = ""

        def run(self):
            raise RuntimeError("UI failed")

    monkeypatch.setattr(app_module, "DipCoaterApp", FailingApp)

    with pytest.raises(RuntimeError, match="UI failed"):
        app_module.run_app(app_state)

    assert controller.cleanup_calls == 1


def test_installed_cli_configures_event_loop_before_main(monkeypatch):
    calls = []
    monkeypatch.setattr(
        app_module, "configure_event_loop_policy", lambda: calls.append("policy")
    )
    monkeypatch.setattr(app_module, "main", lambda: calls.append("main"))

    app_module.run()

    assert calls == ["policy", "main"]


def test_project_script_uses_event_loop_configuring_entrypoint():
    pyproject = Path(__file__).parents[2] / "pyproject.toml"

    with pyproject.open(encoding="utf-8") as project_file:
        assert 'dip-coater = "dip_coater.app:run"' in project_file.read()
