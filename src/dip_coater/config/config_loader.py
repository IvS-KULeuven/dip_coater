import importlib


class ConfigLoader:
    """Load driver-specific configuration modules."""

    @staticmethod
    def load_config(driver_type: str):
        """Load the configuration module for a motor-driver type.

        :param driver_type: Driver type name, such as ``TMC2209``.
        :return: Imported driver-specific configuration module.
        """
        try:
            config_module = importlib.import_module(
                f"dip_coater.config.config_{driver_type.lower()}"
            )
            return config_module
        except ImportError as e:
            raise ValueError(
                f"No configuration found for driver type: '{driver_type}'"
            ) from e


class Config:
    """Proxy object exposing settings from one driver-specific config module."""

    def __init__(self, driver_type):
        """Load configuration for a driver type.

        :param driver_type: Driver type name or enum value.
        """
        self._config = ConfigLoader.load_config(driver_type)

    def __getattr__(self, name):
        """Read a setting from the loaded driver-specific config module.

        :param name: Setting name to resolve.
        :return: Value from the loaded config module.
        """
        return getattr(self._config, name)
