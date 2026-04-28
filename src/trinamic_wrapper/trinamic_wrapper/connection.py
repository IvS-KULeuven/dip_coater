"""Helpers for opening a connection to the Landungsbrücke.

The ADI Landungsbrücke shows up as a USB CDC serial device. On Linux/macOS
it typically appears as one of:

    /dev/ttyACM0                    (Linux, generic CDC name)
    /dev/tty.usbmodemTMCEVAL1       (macOS, named after the device)
    /dev/serial/by-id/usb-…         (Linux, stable-path alternative)

On Windows it appears as ``COMx``.

This module wraps the PyTrinamic :class:`ConnectionManager` so you don't
have to remember the argparse-style argument vector.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from pytrinamic.connections import ConnectionManager


def open_connection(
    port: str | None = None,
    *,
    interface: str = "usb_tmcl",
    datarate: int | None = None,
):
    """Return a :class:`ConnectionManager` configured for the given port.

    Prefer the :func:`connection` context manager below — it closes the
    connection automatically even on exception.

    :param port: Port string. Examples:

        - ``"/dev/tty.usbmodemTMCEVAL1"`` (macOS)
        - ``"/dev/ttyACM0"`` (Linux)
        - ``"COM7"`` (Windows)
        - ``"any"`` — take the first available (default when ``None``)
        - ``"interactive"`` — prompt for selection
        - a digit string like ``"0"`` — the n-th port from the list

    :param interface: ``"usb_tmcl"`` (default, covers the Landungsbrücke),
        ``"serial_tmcl"``, ``"pcan_tmcl"``, etc. See the pytrinamic docs for
        the full list.
    :param datarate: Optional baud / CAN rate override. The default for
        ``usb_tmcl`` is 115200.
    """
    args = ["--interface", interface]
    if port is not None:
        args += ["--port", port]
    if datarate is not None:
        args += ["--data-rate", str(datarate)]
    return ConnectionManager(args)


@contextmanager
def connection(
    port: str | None = None,
    *,
    interface: str = "usb_tmcl",
    datarate: int | None = None,
) -> Iterator:
    """Context manager yielding an open TMCL connection.

    Usage::

        from trinamic_wrapper import connection, create_motor

        with connection("/dev/tty.usbmodemTMCEVAL1") as conn:
            motor = create_motor("TMC5160", conn)
            motor.enable()
            ...

    The connection is closed automatically when the block exits.
    """
    mgr = open_connection(port, interface=interface, datarate=datarate)
    with mgr.connect() as conn:
        yield conn
