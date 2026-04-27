from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual import on
from textual.validation import Number
from textual.widgets import Checkbox, Input, Label, Select, Switch

from dip_coater.motor_driver.tmc2660 import ChopperMode
from dip_coater.utils.SettingChanged import SettingChanged
from dip_coater.widgets.advanced.advanced_settings_base import AdvancedSettingsBase


class AdvancedSettingsTrinamicTMC5160(AdvancedSettingsBase):
    _interpolation: reactive[bool | None] = reactive(None)
    _chopper_mode: reactive[ChopperMode | None] = reactive(None)
    _stealthchop_enabled: reactive[bool | None] = reactive(None)
    _stealthchop_threshold: reactive[float | None] = reactive(None)
    _stallguard_enabled: reactive[bool | None] = reactive(None)
    _stallguard_filter_enabled: reactive[bool | None] = reactive(None)
    _stallguard_threshold: reactive[int | None] = reactive(None)
    _coolstep_enabled: reactive[bool | None] = reactive(None)
    _coolstep_threshold: reactive[int | None] = reactive(None)

    def __init__(self, app_state):
        super().__init__(app_state)
        self.update_interpolation(self.app_state.config.USE_INTERPOLATION)
        self.update_chopper_mode(self.app_state.config.DEFAULT_CHOPPER_MODE)
        self.update_stealthchop_enabled(
            self.app_state.config.DEFAULT_STEALTHCHOP_ENABLED
        )
        self.update_stealthchop_threshold(
            self.app_state.config.DEFAULT_STEALTHCHOP_THRESHOLD_RPS
        )
        self.update_stallguard_enabled(
            self.app_state.config.DEFAULT_STALLGUARD_ENABLED
        )
        self.update_stallguard_filter_enabled(
            self.app_state.config.DEFAULT_STALLGUARD_FILTER_ENABLED
        )
        self.update_stallguard_threshold(
            self.app_state.config.DEFAULT_STALLGUARD_THRESHOLD
        )
        self.update_coolstep_enabled(self.app_state.config.DEFAULT_COOLSTEP_ENABLED)
        self.update_coolstep_threshold(self.app_state.config.DEFAULT_COOLSTEP_THRESHOLD)

    def additional_widgets(self) -> ComposeResult:
        with Horizontal(id="interpolation-container"):
            yield Checkbox(
                "Invert motor direction",
                value=self.app_state.setup_profile.invert_motor_direction,
                id="invert-direction-checkbox",
                classes="checkbox",
            )
            yield Checkbox(
                "Interpolation",
                value=self._interpolation,
                id="interpolation-checkbox",
                classes="checkbox",
            )
            yield Select(
                [(mode.label, mode.label) for mode in ChopperMode],
                id="chopper-mode-select",
                value=self.app_state.config.DEFAULT_CHOPPER_MODE.label,
                allow_blank=False,
                classes="select",
            )

        with Horizontal(id="stealthchop-container"):
            with Vertical():
                yield Label("Enable StealthChop")
                yield Switch(id="stealthchop-switch", value=self._stealthchop_enabled)
            yield Label("StealthChop Threshold")
            yield Input(
                id="stealthchop-threshold",
                type="number",
                value=str(self._stealthchop_threshold),
                classes="input-fields",
                validators=[Number(minimum=0)],
            )
            yield Label("rev/s")

        with Horizontal(id="stallguard-container"):
            with Vertical():
                yield Label("Enable StallGuard")
                yield Switch(id="stallguard-switch", value=self._stallguard_enabled)
            with Vertical():
                yield Label("Enable StallGuard Filter")
                yield Switch(
                    id="stallguard-filter-switch", value=self._stallguard_filter_enabled
                )
            yield Label("StallGuard Threshold")
            yield Input(
                id="stallguard-threshold",
                type="number",
                value=str(self._stallguard_threshold),
                classes="input-fields",
                validators=[Number(minimum=-64, maximum=63)],
            )

        with Horizontal(id="coolstep-container"):
            with Vertical():
                yield Label("Enable CoolStep")
                yield Switch(id="coolstep-switch", value=self._coolstep_enabled)
            yield Label("CoolStep Threshold")
            yield Input(
                id="coolstep-threshold",
                type="number",
                value=str(self._coolstep_threshold),
                classes="input-fields",
                validators=[Number(minimum=0, maximum=(1 << 31) - 1)],
            )

    def reset_settings_to_default(self):
        super().reset_settings_to_default()
        self.update_interpolation(self.app_state.config.USE_INTERPOLATION)
        self.query_one(
            "#interpolation-checkbox", Checkbox
        ).value = self.app_state.config.USE_INTERPOLATION

        default_chopper_mode = self.app_state.config.DEFAULT_CHOPPER_MODE
        self.update_chopper_mode(default_chopper_mode)
        self.query_one(
            "#chopper-mode-select", Select
        ).value = default_chopper_mode.label

        self.update_stealthchop_enabled(
            self.app_state.config.DEFAULT_STEALTHCHOP_ENABLED
        )
        self.query_one(
            "#stealthchop-switch", Switch
        ).value = self.app_state.config.DEFAULT_STEALTHCHOP_ENABLED
        self.update_stealthchop_threshold(
            self.app_state.config.DEFAULT_STEALTHCHOP_THRESHOLD_RPS
        )
        self.query_one("#stealthchop-threshold", Input).value = str(
            self.app_state.config.DEFAULT_STEALTHCHOP_THRESHOLD_RPS
        )
        self.update_stallguard_enabled(
            self.app_state.config.DEFAULT_STALLGUARD_ENABLED
        )
        self.query_one(
            "#stallguard-switch", Switch
        ).value = self.app_state.config.DEFAULT_STALLGUARD_ENABLED
        self.update_stallguard_filter_enabled(
            self.app_state.config.DEFAULT_STALLGUARD_FILTER_ENABLED
        )
        self.query_one(
            "#stallguard-filter-switch", Switch
        ).value = self.app_state.config.DEFAULT_STALLGUARD_FILTER_ENABLED
        self.update_stallguard_threshold(
            self.app_state.config.DEFAULT_STALLGUARD_THRESHOLD
        )
        self.query_one("#stallguard-threshold", Input).value = str(
            self.app_state.config.DEFAULT_STALLGUARD_THRESHOLD
        )
        self.update_coolstep_enabled(self.app_state.config.DEFAULT_COOLSTEP_ENABLED)
        self.query_one(
            "#coolstep-switch", Switch
        ).value = self.app_state.config.DEFAULT_COOLSTEP_ENABLED
        self.update_coolstep_threshold(
            self.app_state.config.DEFAULT_COOLSTEP_THRESHOLD
        )
        self.query_one("#coolstep-threshold", Input).value = str(
            self.app_state.config.DEFAULT_COOLSTEP_THRESHOLD
        )

    @on(Checkbox.Changed, "#interpolation-checkbox")
    def toggle_interpolation(self, event: Checkbox.Changed):
        self.update_interpolation(event.checkbox.value)

    def update_interpolation(self, interpolation: reactive[bool | None]):
        self._interpolation = interpolation

    @on(Select.Changed, "#chopper-mode-select")
    def change_chopper_mode(self, event: Select.Changed):
        chopper_mode = ChopperMode.from_label(event.value)
        self.update_chopper_mode(chopper_mode)

    def update_chopper_mode(self, chopper_mode: reactive[ChopperMode | None]):
        self._chopper_mode = chopper_mode

    @on(Switch.Changed, "#stealthchop-switch")
    def toggle_stealthchop(self, event: Switch.Changed):
        self.update_stealthchop_enabled(event.switch.value)

    def update_stealthchop_enabled(
        self, stealthchop_enabled: reactive[bool | None]
    ):
        self._stealthchop_enabled = stealthchop_enabled

    @on(Input.Submitted, "#stealthchop-threshold")
    def submit_stealthchop_threshold(self, event: Input.Submitted):
        if event.validation_result.is_valid:
            self.update_stealthchop_threshold(float(event.input.value))

    def update_stealthchop_threshold(
        self, stealthchop_threshold: reactive[float | None]
    ):
        self._stealthchop_threshold = stealthchop_threshold

    @on(Switch.Changed, "#stallguard-switch")
    def toggle_stallguard(self, event: Switch.Changed):
        self.update_stallguard_enabled(event.switch.value)

    def update_stallguard_enabled(self, stallguard_enabled: reactive[bool | None]):
        self._stallguard_enabled = stallguard_enabled

    @on(Switch.Changed, "#stallguard-filter-switch")
    def toggle_stallguard_filter(self, event: Switch.Changed):
        self.update_stallguard_filter_enabled(event.switch.value)

    def update_stallguard_filter_enabled(
        self, stallguard_filter_enabled: reactive[bool | None]
    ):
        self._stallguard_filter_enabled = stallguard_filter_enabled

    @on(Input.Submitted, "#stallguard-threshold")
    def submit_stallguard_threshold(self, event: Input.Submitted):
        if event.validation_result.is_valid:
            self.update_stallguard_threshold(int(event.input.value))

    def update_stallguard_threshold(self, stallguard_threshold: reactive[int | None]):
        self._stallguard_threshold = stallguard_threshold

    @on(Switch.Changed, "#coolstep-switch")
    def toggle_coolstep(self, event: Switch.Changed):
        self.update_coolstep_enabled(event.switch.value)

    def update_coolstep_enabled(self, coolstep_enabled: reactive[bool | None]):
        self._coolstep_enabled = coolstep_enabled

    @on(Input.Submitted, "#coolstep-threshold")
    def submit_coolstep_threshold(self, event: Input.Submitted):
        if event.validation_result.is_valid:
            self.update_coolstep_threshold(int(event.input.value))

    def update_coolstep_threshold(self, coolstep_threshold: reactive[int | None]):
        self._coolstep_threshold = coolstep_threshold

    def watch__interpolation(self, interpolation: bool):
        if interpolation is None:
            return
        self.post_message(SettingChanged("interpolation", interpolation))

    def watch__chopper_mode(self, chopper_mode: ChopperMode):
        if chopper_mode is None:
            return
        self.post_message(SettingChanged("chopper_mode", chopper_mode))

    def watch__stealthchop_enabled(self, stealthchop_enabled: bool):
        if stealthchop_enabled is None:
            return
        self.post_message(SettingChanged("stealthchop_enabled", stealthchop_enabled))

    def watch__stealthchop_threshold(self, stealthchop_threshold: float):
        if stealthchop_threshold is None:
            return
        self.post_message(
            SettingChanged("stealthchop_threshold", float(stealthchop_threshold))
        )

    def watch__stallguard_enabled(self, stallguard_enabled: bool):
        if stallguard_enabled is None:
            return
        self.post_message(SettingChanged("stallguard_enabled", stallguard_enabled))

    def watch__stallguard_filter_enabled(self, stallguard_filter_enabled: bool):
        if stallguard_filter_enabled is None:
            return
        self.post_message(
            SettingChanged("stallguard_filter_enabled", stallguard_filter_enabled)
        )

    def watch__stallguard_threshold(self, stallguard_threshold: int):
        if stallguard_threshold is None:
            return
        self.post_message(
            SettingChanged("stallguard_threshold", int(stallguard_threshold))
        )

    def watch__coolstep_enabled(self, coolstep_enabled: bool):
        if coolstep_enabled is None:
            return
        self.post_message(SettingChanged("coolstep_enabled", coolstep_enabled))

    def watch__coolstep_threshold(self, coolstep_threshold: int):
        if coolstep_threshold is None:
            return
        self.post_message(SettingChanged("coolstep_threshold", int(coolstep_threshold)))
