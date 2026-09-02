import importlib

import pytest

from dip_coater.config.config_loader import ConfigLoader


def test_missing_driver_configuration_has_friendly_error():
    with pytest.raises(ValueError, match="No configuration found"):
        ConfigLoader.load_config("not_a_driver")


def test_dependency_import_failure_inside_config_is_not_masked(monkeypatch):
    dependency_error = ModuleNotFoundError(
        "No module named 'broken_dependency'",
        name="broken_dependency",
    )

    def fail_import(_module_name):
        raise dependency_error

    monkeypatch.setattr(importlib, "import_module", fail_import)

    with pytest.raises(ModuleNotFoundError) as error_info:
        ConfigLoader.load_config("tmc5160")

    assert error_info.value is dependency_error
