"""Internal validation helpers shared by real and simulated motors."""

from __future__ import annotations

import math

from .exceptions import OutOfRangeError


def require_finite(name: str, value: float) -> None:
    """Require a finite, non-boolean numeric command value."""
    try:
        valid = not isinstance(value, bool) and math.isfinite(value)
    except (TypeError, ValueError):
        valid = False
    if not valid:
        raise OutOfRangeError(f"{name} must be finite")


def require_nonnegative_finite(name: str, value: float) -> None:
    """Require a finite numeric command value greater than or equal to zero."""
    require_finite(name, value)
    if value < 0:
        raise OutOfRangeError(f"{name} must be non-negative")


def require_positive_finite(name: str, value: float) -> None:
    """Require a finite numeric command value greater than zero."""
    require_finite(name, value)
    if value <= 0:
        raise OutOfRangeError(f"{name} must be positive")


def require_bool(name: str, value: bool) -> None:
    """Require an actual boolean rather than a truthy substitute."""
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be a boolean")


def require_int_range(
    name: str,
    value: int,
    minimum: int,
    maximum: int,
) -> None:
    """Require a non-boolean integer inside an inclusive hardware range."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be in [{minimum}, {maximum}]")
