from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path


def get_version() -> str:
    """Return the project version.

    Prefer installed package metadata so normal CLI use does not depend on
    ``tomllib``/``tomli`` being available. Fall back to the local
    ``pyproject.toml`` only when the package metadata is unavailable.
    """

    try:
        return package_version("dip-coater")
    except PackageNotFoundError:
        pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
        if not pyproject_path.exists():
            return "0.0.0+unknown"

        try:
            import tomllib
        except ModuleNotFoundError:  # pragma: no cover
            try:
                import tomli as tomllib
            except ModuleNotFoundError:  # pragma: no cover
                return "0.0.0+unknown"

        with pyproject_path.open("rb") as pyproject_file:
            pyproject = tomllib.load(pyproject_file)
        return pyproject["tool"]["poetry"]["version"]


__version__ = get_version()
