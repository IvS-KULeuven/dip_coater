from textual.reactive import reactive
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.validation import Number
from textual import on, events
from textual.widgets import Label, Button, Checkbox, Rule, Input, RichLog, Switch

from dip_coater.widgets.advanced.advanced_settings_base import AdvancedSettingsBase
from dip_coater.utils.helpers import clamp
from dip_coater.utils.SettingChanged import SettingChanged


class AdvancedSettingsTMC2209(AdvancedSettingsBase):
    _interpolation: reactive[bool | None] = reactive(None)
    _spread_cycle: reactive[bool | None] = reactive(None)
    _threshold_speed: reactive[float | None] = reactive(None)
    _threshold_speed_enabled: reactive[bool | None] = reactive(None)

    _homing_revs: reactive[float | None] = reactive(None)
    _homing_threshold: reactive[float | None] = reactive(None)
    _homing_speed: reactive[float | None] = reactive(None)
    
    def __init__(self, app_state):
        super().__init__(app_state)

    # --------------- UI INIT ---------------

    def additional_widgets(self) -> ComposeResult:
        with Horizontal(id="interpolation-container"):
            yield Checkbox("Invert motor direction",
                           value=self.app_state.config.INVERT_MOTOR_DIRECTION,
                           id="invert-direction-checkbox", classes="checkbox")
            yield Checkbox("Interpolation", value=self._interpolation,
                           id="interpolation-checkbox", classes="checkbox")
            yield Checkbox("Spread Cycle (T)/Stealth Chop (F)", value=self._spread_cycle,
                           id="spread-cycle-checkbox", classes="checkbox")
        with Horizontal(id="threshold-speed-container"):
            yield Label("Enable Threshold Speed: ", id="threshold-speed-switch-label")
            yield Switch(value=self._threshold_speed_enabled, id="threshold-speed-switch")
            yield Label("Threshold Speed: ", id="threshold-speed-label")
            yield Input(
                value=f"{self._threshold_speed}",
                type="number",
                placeholder="Threshold Speed (mm/s)",
                id="threshold-speed-input",
                validate_on=["submitted"],
                validators=[Number(minimum=self.app_state.config.MIN_THRESHOLD_SPEED,
                                   maximum=self.app_state.config.MAX_THRESHOLD_SPEED)],
                classes="input-fields",
            )
            yield Label("mm/s", id="threshold-speed-unit")

        yield Rule(classes="rule")

        with Horizontal(id="homing-container"):
            with Horizontal():
                yield Label("Homing revolutions: ", id="homing-revolutions-label")
                yield Input(
                    value=f"{self._homing_revs}",
                    type="number",
                    placeholder="Homing revolutions",
                    id="homing-revolutions-input",
                    validate_on=["submitted"],
                    validators=[Number(minimum=self.app_state.config.HOMING_MIN_REVOLUTIONS,
                                       maximum=self.app_state.config.HOMING_MAX_REVOLUTIONS)],
                    classes="input-fields",
                )
            with Horizontal():
                yield Label("Homing threshold: ", id="homing-threshold-label")
                yield Input(
                    value=f"{self._homing_threshold}",
                    type="number",
                    placeholder="Homing threshold",
                    id="homing-threshold-input",
                    validate_on=["submitted"],
                    validators=[Number(minimum=self.app_state.config.HOMING_MIN_THRESHOLD,
                                       maximum=self.app_state.config.HOMING_MAX_THRESHOLD)],
                    classes="input-fields",
                )
            with Horizontal():
                yield Label("Homing speed: ", id="homing-speed-label")
                yield Input(
                    value=f"{self._homing_speed}",
                    type="number",
                    placeholder="Homing speed (RPM)",
                    id="homing-speed-input",
                    validate_on=["submitted"],
                    validators=[Number(minimum=self.app_state.config.HOMING_MIN_SPEED,
                                       maximum=self.app_state.config.HOMING_MAX_SPEED)],
                    classes="input-fields",
                )
                yield Label("RPM", id="homing-speed-unit")
        yield Button("Test StallGuard Threshold", id="test-stallguard-threshold-btn")

    def _on_mount(self, event: events.Mount) -> None:
        super()._on_mount(event)

        # Attach watchers to reactives from other widgets
        self.watch(self.app_state.speed_controls, "speed", self.update_control_mode_widgets_value)

        self.reset_settings_to_default()

    def reset_settings_to_default(self):
        super().reset_settings_to_default()

        self.update_interpolation(self.app_state.config.USE_INTERPOLATION)
        self.query_one("#interpolation-checkbox", Checkbox).value = (
            self.app_state.config.USE_INTERPOLATION)
        self.update_spread_cycle(self.app_state.config.USE_SPREAD_CYCLE)
        self.query_one("#spread-cycle-checkbox", Checkbox).value = (
            self.app_state.config.USE_SPREAD_CYCLE)

        self.update_threshold_speed(self.app_state.config.DEFAULT_THRESHOLD_SPEED)
        self.query_one("#threshold-speed-input", Input).value = \
            f"{self.app_state.config.DEFAULT_THRESHOLD_SPEED}"
        self.update_threshold_speed_enabled(self.app_state.config.THRESHOLD_SPEED_ENABLED)
        self.query_one("#threshold-speed-switch", Switch).value = (
            self.app_state.config.THRESHOLD_SPEED_ENABLED)

        self.update_homing_revs(self.app_state.config.HOMING_REVOLUTIONS)
        self.query_one("#homing-revolutions-input", Input).value = \
            f"{self.app_state.config.HOMING_REVOLUTIONS}"
        self.update_homing_threshold(self.app_state.config.HOMING_THRESHOLD)
        self.query_one("#homing-threshold-input", Input).value = \
            f"{self.app_state.config.HOMING_THRESHOLD}"
        self.update_homing_speed(self.app_state.config.HOMING_SPEED_MM_S)
        self.query_one("#homing-speed-input", Input).value = \
            f"{self.app_state.config.HOMING_SPEED_MM_S}"

    # --------------- WIDGET INTERACTIONS ---------------

    @on(Checkbox.Changed, "#interpolation-checkbox")
    def toggle_interpolation(self, event: Checkbox.Changed):
        interpolation = event.checkbox.value
        self.update_interpolation(interpolation)

    def update_interpolation(self, interpolation: reactive[bool | None]):
        self._interpolation = interpolation

    @on(Checkbox.Changed, "#spread-cycle-checkbox")
    def toggle_spread_cycle(self, event: Checkbox.Changed):
        spread_cycle = event.checkbox.value
        self.update_spread_cycle(spread_cycle)

    def update_spread_cycle(self, spread_cycle: reactive[bool | None]):
        self._spread_cycle = spread_cycle

    @on(Input.Submitted, "#threshold-speed-input")
    def submit_threshold_speed_input(self):
        threshold_speed_input = self.query_one("#threshold-speed-input", Input)
        threshold_speed = float(threshold_speed_input.value)
        threshold_speed_validated = clamp(threshold_speed,
                                          self.app_state.config.MIN_THRESHOLD_SPEED,
                                          self.app_state.config.MAX_THRESHOLD_SPEED)
        threshold_speed_input.value = f"{threshold_speed_validated}"
        self.update_threshold_speed(threshold_speed_validated)

    def update_threshold_speed(self, threshold_speed: reactive[float | None]):
        self._threshold_speed = round(threshold_speed, 2)

    @on(Switch.Changed, "#threshold-speed-switch")
    def toggle_threshold_speed(self, event: Switch.Changed):
        enabled = event.switch.value
        self.update_threshold_speed_enabled(enabled)

    def update_threshold_speed_enabled(self, enabled: reactive[bool | None]):
        self._threshold_speed_enabled = enabled

    def update_control_mode_widgets_value(self):
        if not self._threshold_speed_enabled:
            return
        self.app_state.status_advanced.update_speed_mode(self._threshold_speed_enabled, self._threshold_speed)

        interpolation_checkbox = self.query_one("#interpolation-checkbox", Checkbox)
        spread_cycle_checkbox = self.query_one("#spread-cycle-checkbox", Checkbox)

        interpolation_checkbox.value = self._interpolation
        spread_cycle_checkbox.value = self._spread_cycle

    def update_motor_configuration(self):
        if self._threshold_speed_enabled and self.app_state.speed_controls.speed >= self._threshold_speed:
            # High-speed configuration
            self.app_state.step_mode.update_microsteps(self.app_state.config.HIGH_SPEED_STEP_MODE)
            self.watch__interpolation(self.app_state.config.HIGH_SPEED_INTERPOLATION)
            self.watch__spread_cycle(self.app_state.config.HIGH_SPEED_SPREAD_CYCLE)
        else:
            # Low-speed configuration
            self.app_state.step_mode.update_microsteps(self.app_state.config.LOW_SPEED_STEP_MODE)
            self.watch__interpolation(self.app_state.config.LOW_SPEED_INTERPOLATION)
            self.watch__spread_cycle(self.app_state.config.LOW_SPEED_SPREAD_CYCLE)
        self.update_control_mode_widgets_value()

    def update_control_mode_widgets_state(self):
        interpolation_checkbox = self.query_one("#interpolation-checkbox", Checkbox)
        spread_cycle_checkbox = self.query_one("#spread-cycle-checkbox", Checkbox)

        disabled = self._threshold_speed_enabled
        self.app_state.step_mode.disabled = disabled
        interpolation_checkbox.disabled = disabled
        spread_cycle_checkbox.disabled = disabled

    @on(Input.Submitted, "#homing-revolutions-input")
    def submit_homing_revs_input(self):
        homing_revs_input = self.query_one("#homing-revolutions-input", Input)
        homing_revs = int(homing_revs_input.value)
        homing_revs_validated = clamp(homing_revs, self.app_state.config.HOMING_MIN_REVOLUTIONS,
                                      self.app_state.config.HOMING_MAX_REVOLUTIONS)
        homing_revs_input.value = f"{homing_revs_validated}"
        self.update_homing_revs(homing_revs_validated)

    def update_homing_revs(self, homing_revs: reactive[int | None]):
        self._homing_revs = homing_revs

    @on(Input.Submitted, "#homing-threshold-input")
    def submit_homing_threshold_input(self):
        homing_threshold_input = self.query_one("#homing-threshold-input", Input)
        homing_threshold = int(homing_threshold_input.value)
        homing_threshold_validated = clamp(homing_threshold,
                                           self.app_state.config.HOMING_MIN_THRESHOLD,
                                           self.app_state.config.HOMING_MAX_THRESHOLD)
        homing_threshold_input.value = f"{homing_threshold_validated}"
        self.update_homing_threshold(homing_threshold_validated)

    def update_homing_threshold(self, homing_threshold: reactive[int | None]):
        self._homing_threshold = homing_threshold

    @on(Input.Submitted, "#homing-speed-input")
    def submit_homing_speed_input(self):
        homing_speed_input = self.query_one("#homing-speed-input", Input)
        homing_speed = float(homing_speed_input.value)
        homing_speed_validated = clamp(homing_speed, self.app_state.config.HOMING_MIN_SPEED,
                                       self.app_state.config.HOMING_MAX_SPEED)
        homing_speed_input.value = f"{homing_speed_validated}"
        self.update_homing_speed(homing_speed_validated)

    def update_homing_speed(self, homing_speed: reactive[float | None]):
        self._homing_speed = homing_speed

    @on(Button.Pressed, "#test-stallguard-threshold-btn")
    async def test_stallguard_threshold(self):
        log = self.app.query_one("#logger", RichLog)
        log.write("[cyan]Testing StallGuard threshold...[/]")
        self.app_state.motor_driver.test_stallguard_threshold()
        log.write("[cyan]-> Finished testing StallGuard threshold.[/]")

    # --------------- WATCHERS (called automatically when reactive has changed) ---------------

    def watch__interpolation(self, interpolation: bool):
        if interpolation is None:
            return
        self.post_message(SettingChanged("interpolation", interpolation))

    def watch__spread_cycle(self, spread_cycle: bool):
        if spread_cycle is None:
            return 
        self.post_message(SettingChanged("spread_cycle", spread_cycle))

    def watch__threshold_speed(self, threshold_speed: float):
        if threshold_speed is None:
            return 
        self.post_message(SettingChanged("threshold_speed", threshold_speed))

    def watch__threshold_speed_enabled(self, enabled: bool):
        if enabled is None:
            return
        self.post_message(SettingChanged("threshold_speed_enabled", enabled))

    def watch__homing_revs(self, homing_revs: int):
        if homing_revs is None:
            return
        self.post_message(SettingChanged("homing_revs", homing_revs))

    def watch__homing_threshold(self, homing_threshold: int):
        if homing_threshold is None:
            return
        self.post_message(SettingChanged("homing_threshold", homing_threshold))

    def watch__homing_speed(self, homing_speed: float):
        if homing_speed is None:
            return 
        self.post_message(SettingChanged("homing_speed", homing_speed))
    
    # --------------- GETTERS/SETTERS ---------------

    def get_threshold_speed(self):
        return self._threshold_speed
    
    def get_threshold_speed_enabled(self):
        return self._threshold_speed_enabled
    
    def get_homing_speed(self):
        return self._homing_speed
