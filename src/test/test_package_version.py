import importlib
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib


def test_get_version_prefers_local_pyproject(monkeypatch):
    module = importlib.import_module("dip_coater")
    pyproject_path = Path(__file__).parents[2] / "pyproject.toml"
    pyproject = tomllib.loads(pyproject_path.read_text())

    monkeypatch.setattr(module, "package_version", lambda _: "9.9.9")

    assert module.get_version() == pyproject["project"]["version"]


def test_pyproject_packages_include_runtime_packages():
    pyproject_path = Path(__file__).parents[2] / "pyproject.toml"
    pyproject = tomllib.loads(pyproject_path.read_text())

    package_finder = pyproject["tool"]["setuptools"]["packages"]["find"]
    assert package_finder["where"] == ["src"]
    assert "dip_coater*" in package_finder["include"]
    assert "trinamic_wrapper*" in package_finder["include"]


def test_rpi_extra_includes_all_gpio_backends():
    pyproject_path = Path(__file__).parents[2] / "pyproject.toml"
    pyproject = tomllib.loads(pyproject_path.read_text())

    rpi_dependencies = pyproject["project"]["optional-dependencies"]["rpi"]

    assert any(dependency.startswith("RPi.GPIO") for dependency in rpi_dependencies)
    assert any(dependency.startswith("gpiozero") for dependency in rpi_dependencies)
    assert any(dependency.startswith("lgpio") for dependency in rpi_dependencies)


def test_tree_sitter_dependencies_are_optional_for_syntax_highlighting():
    pyproject_path = Path(__file__).parents[2] / "pyproject.toml"
    pyproject = tomllib.loads(pyproject_path.read_text())

    dependencies = pyproject["project"]["dependencies"]
    syntax_dependencies = pyproject["project"]["optional-dependencies"]["syntax"]

    assert not any(dependency.startswith("tree-sitter") for dependency in dependencies)
    assert "tree-sitter>=0.23.0,<0.24.0" in syntax_dependencies
    assert "tree-sitter-python>=0.23.0,<0.24.0" in syntax_dependencies
