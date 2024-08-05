import importlib


class ConfigLoader:
    @staticmethod
    def load_config(driver_type: str):
        try:
            print(f"dip_coater.config.config_{driver_type.lower()}")
            config_module = importlib.import_module(f"dip_coater.config.config_{driver_type.lower()}")
            return config_module
        except ImportError as e:
            print(f"Import error: {e}")  # Add this line for debugging
            raise ValueError(f"No configuration found for driver type: '{driver_type}'")


class Config:
    def __init__(self, driver_type):
        self._config = ConfigLoader.load_config(driver_type)

    def __getattr__(self, name):
        return getattr(self._config, name)
