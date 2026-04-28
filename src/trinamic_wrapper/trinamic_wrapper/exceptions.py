"""Custom exceptions for the wrapper."""


class TrinamicWrapperError(Exception):
    """Base exception for all wrapper errors."""


class OutOfRangeError(TrinamicWrapperError, ValueError):
    """Raised when a requested value cannot be represented by the hardware."""


class UnsupportedFeatureError(TrinamicWrapperError, NotImplementedError):
    """Raised when a feature is not available on the current chip."""
