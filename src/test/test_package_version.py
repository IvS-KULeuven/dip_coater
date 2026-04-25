import importlib
from pathlib import Path


def test_get_version_prefers_installed_package_metadata(monkeypatch):
    module = importlib.import_module("dip_coater")

    monkeypatch.setattr(module, "package_version", lambda _: "9.9.9")

    assert module.get_version() == "9.9.9"


def test_pyproject_packages_include_dip_coater_and_trinamic_wrapper():
    pyproject_path = Path(__file__).parents[2] / "pyproject.toml"
    pyproject = pyproject_path.read_text()

    assert '{include = "dip_coater", from = "src"}' in pyproject
    assert '{include = "trinamic_wrapper", from = "src/trinamic_wrapper"}' in pyproject
