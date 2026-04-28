from collections.abc import Callable

from rich.markup import escape
from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Button, Static, TabPane

from dip_coater.setup_profiles.machine_profile import HomeDirection


def build_diagnostics_rows(app_state) -> list[tuple[str, str]]:
    rows = [
        ("Driver", _driver_label(app_state)),
        ("Setup", app_state.setup_profile.label),
        ("Motor state", app_state.motor_state),
        ("Homed", _yes_no(app_state.homing_found)),
        ("Position", _read_value(lambda: f"{_position(app_state):.1f} mm")),
        (
            "Limit switch support",
            _yes_no(app_state.motion_controller.supports_limit_switches),
        ),
        ("Homing support", _yes_no(app_state.motion_controller.supports_homing)),
    ]
    rows.extend(_limit_switch_rows(app_state))
    rows.extend(_driver_reference_rows(app_state))
    return rows


def _driver_label(app_state) -> str:
    label = app_state.driver_type.name
    if getattr(app_state.motor_driver, "is_dummy", False):
        label += " (dummy)"
    return label


def _position(app_state) -> float:
    return app_state.motion_controller.get_current_position_mm()


def _limit_switch_rows(app_state) -> list[tuple[str, str]]:
    rows = []
    switches = app_state.setup_profile.limit_switches
    if switches is None:
        rows.extend(
            [
                ("UP limit switch", "not configured"),
                ("DOWN limit switch", "not configured"),
            ]
        )
        return rows

    for direction in (HomeDirection.UP, HomeDirection.DOWN):
        switch = switches.switch_for(direction)
        label_prefix = direction.value.upper()
        rows.append(
            (
                f"{label_prefix} limit switch",
                _read_value(
                    lambda direction=direction: _triggered_state(
                        app_state.motion_controller.read_limit_switch(direction)
                    )
                ),
            )
        )
        rows.append(
            (
                f"{label_prefix} limit config",
                _limit_switch_config(switch),
            )
        )
    return rows


def _limit_switch_config(switch) -> str:
    parts = [switch.source.value, switch.polarity.value]
    if switch.pin is not None:
        parts.append(f"pin {switch.pin}")
    return ", ".join(parts)


def _driver_reference_rows(app_state) -> list[tuple[str, str]]:
    driver = app_state.motor_driver
    rows = []
    if hasattr(driver, "get_left_endstop"):
        rows.append(
            ("TMC L reference raw", _read_value(lambda: _high_low(driver.get_left_endstop())))
        )
    if hasattr(driver, "get_right_endstop"):
        rows.append(
            (
                "TMC R reference raw",
                _read_value(lambda: _high_low(driver.get_right_endstop())),
            )
        )
    return rows


def _read_value(reader: Callable[[], str]) -> str:
    try:
        return reader()
    except Exception as error:
        return f"error: {error}"


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _triggered_state(value: bool) -> str:
    return "triggered" if value else "open"


def _high_low(value: bool) -> str:
    return "high" if value else "low"


def format_diagnostics_rows(rows: list[tuple[str, str]]) -> str:
    label_width = max((len(label) for label, _value in rows), default=0)
    lines = [
        f"[b]{escape(label):<{label_width}}[/b]  {_format_diagnostics_value(label, value)}"
        for label, value in rows
    ]
    return "\n".join(lines)


def _format_diagnostics_value(label: str, value: str) -> str:
    if label == "Motor state":
        return _colorize_motor_state(value)
    if label.endswith("limit switch"):
        return _colorize_limit_switch_state(value)
    return escape(value)


def _colorize_motor_state(value: str) -> str:
    colors = {
        "enabled": "green",
        "disabled": "dark_orange",
        "homing": "cyan",
        "moving": "blue",
    }
    color = colors.get(value, "red")
    return f"[{color}]{escape(value)}[/]"


def _colorize_limit_switch_state(value: str) -> str:
    if value == "open":
        return "[green]open[/]"
    if value == "triggered":
        return "[red]triggered[/]"
    return escape(value)


class DiagnosticsTab(TabPane):
    def __init__(self, app_state):
        super().__init__("Diagnostics", id="diagnostics-tab")
        self.app_state = app_state

    def compose(self) -> ComposeResult:
        with Vertical(id="diagnostics-container"):
            yield Button("Refresh diagnostics", id="refresh-diagnostics")
            yield Static(id="diagnostics-panel")

    def _on_mount(self) -> None:
        self.refresh_diagnostics()

    @on(Button.Pressed, "#refresh-diagnostics")
    def refresh_diagnostics(self):
        rows = build_diagnostics_rows(self.app_state)
        self.query_one("#diagnostics-panel", Static).update(
            format_diagnostics_rows(rows)
        )
