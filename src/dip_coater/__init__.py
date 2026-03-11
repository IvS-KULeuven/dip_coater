from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib


def get_version() -> str:
    """Return the project version, preferring the local pyproject in a source checkout."""
    pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
    if pyproject_path.exists():
        with pyproject_path.open("rb") as pyproject_file:
            pyproject = tomllib.load(pyproject_file)
        return pyproject["tool"]["poetry"]["version"]

    try:
        return package_version("dip-coater")
    except PackageNotFoundError:
        return "0.0.0+unknown"


__version__ = get_version()
