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
