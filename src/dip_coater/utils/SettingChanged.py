from textual.message import Message


class SettingChanged(Message):
    def __init__(self, setting_name: str, value: any):
        self.setting_name = setting_name
        self.value = value
        super().__init__()
