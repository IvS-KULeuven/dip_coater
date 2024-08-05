from dip_coater.widgets.advanced.status_advanced_base import StatusAdvancedBase


class StatusAdvancedTMC2660(StatusAdvancedBase):
    def __init__(self, app_state, *args, **kwargs):
        super().__init__(app_state, *args, **kwargs)
