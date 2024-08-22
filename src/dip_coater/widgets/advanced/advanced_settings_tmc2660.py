from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual import on
from textual.widgets import Checkbox, Select

from dip_coater.widgets.advanced.advanced_settings_base import AdvancedSettingsBase
from dip_coater.utils.SettingChanged import SettingChanged
from dip_coater.motor.tmc2660 import ChopperMode


class AdvancedSettingsTMC2660(AdvancedSettingsBase):
    _interpolation: reactive[bool | None] = reactive(None)
    _chopper_mode: reactive[ChopperMode | None] = reactive(None)

    def __init__(self, app_state):
        super().__init__(app_state)

    def additional_widgets(self) -> ComposeResult:
        with Horizontal(id="interpolation-container"):
            yield Checkbox("Invert motor direction",
                           value=self.app_state.config.INVERT_MOTOR_DIRECTION,
                           id="invert-direction-checkbox", classes="checkbox")
            yield Checkbox("Interpolation", value=self._interpolation,
                           id="interpolation-checkbox", classes="checkbox")
            yield Select(
                [(mode.label, mode.label) for mode in ChopperMode],
                id="chopper-mode-select",
                value=ChopperMode.from_int(self.app_state.config.DEFAULT_CHOPPER_MODE.value).label,
                allow_blank=False,
                classes="select"
            )

    def reset_settings_to_default(self):
        super().reset_settings_to_default()

        self.update_interpolation(self.app_state.config.USE_INTERPOLATION)
        self.query_one("#interpolation-checkbox", Checkbox).value = (
            self.app_state.config.USE_INTERPOLATION)

        default_chopper_mode = self.app_state.config.DEFAULT_CHOPPER_MODE
        self.update_chopper_mode(default_chopper_mode)
        self.query_one("#chopper-mode-select", Select).value = default_chopper_mode.label

    # --------------- WIDGET INTERACTIONS ---------------

    @on(Checkbox.Changed, "#interpolation-checkbox")
    def toggle_interpolation(self, event: Checkbox.Changed):
        interpolation = event.checkbox.value
        self.update_interpolation(interpolation)

    def update_interpolation(self, interpolation: reactive[bool | None]):
        self._interpolation = interpolation

    @on(Select.Changed, "#chopper-mode-select")
    def change_chopper_mode(self, event: Select.Changed):
        chopper_mode = ChopperMode.from_label(event.value)
        self.update_chopper_mode(chopper_mode)

    def update_chopper_mode(self, chopper_mode: reactive[ChopperMode | None]):
        self._chopper_mode = chopper_mode

    # --------------- WATCHERS (called automatically when reactive has changed) ---------------

    def watch__interpolation(self, interpolation: bool):
        if interpolation is None:
            return
        self.post_message(SettingChanged("interpolation", interpolation))

    def watch__chopper_mode(self, chopper_mode: ChopperMode):
        if chopper_mode is None:
            return
        self.post_message(SettingChanged("chopper_mode", chopper_mode))
