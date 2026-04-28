from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path


def get_version() -> str:
    """Return the project version.

    Prefer the local ``pyproject.toml`` when running from a source checkout so
    the TUI and CLI startup line follow the project version directly. Fall back
    to installed package metadata for packaged installs.
    """

    pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
    if pyproject_path.exists():
        try:
            import tomllib
        except ModuleNotFoundError:  # pragma: no cover
            try:
                import tomli as tomllib
            except ModuleNotFoundError:  # pragma: no cover
                tomllib = None

        if tomllib is not None:
            with pyproject_path.open("rb") as pyproject_file:
                pyproject = tomllib.load(pyproject_file)
            return pyproject["project"]["version"]

    try:
        return package_version("dip-coater")
    except PackageNotFoundError:
        return "0.0.0+unknown"


__version__ = get_version()
