"""Hardware test fixtures and conftest.

These tests require a real Landungsbrücke + TMC5160-EVAL or TMC2660-EVAL
and a connected stepper motor. They are **skipped by default** so normal
``pytest`` runs don't try to talk to USB.

To run them, pass the port on the command line:

    pytest tests/hardware/ --hw-port=/dev/tty.usbmodemTMCEVAL1 --hw-chip=TMC5160

Options (with defaults):

    --hw-port=PORT              USB port of the Landungsbrücke (required)
    --hw-chip={TMC5160,TMC2660} which chip is on the Eselsbrücke
    --hw-rsense=0.075           sense-resistor value (0.075 or 0.1 typically)
    --hw-fullsteps=200          motor full-steps per rev
    --hw-current-mA=500         run current for the tests
    --hw-standstill-mA=100      standstill current for the tests
    --hw-max-mA=1000            max allowed current (safety cap)

All tests call ``motor.disable()`` in teardown even on failure.
"""

from __future__ import annotations

import logging
import os

import pytest

from trinamic_wrapper import (
    MotorConfig,
    StepMode,
    connection,
    create_motor,
)

logger = logging.getLogger(__name__)


def pytest_addoption(parser):
    group = parser.getgroup("trinamic hardware")
    group.addoption(
        "--hw-port",
        default=os.environ.get("TRINAMIC_HW_PORT"),
        help="USB port of the Landungsbrücke (e.g. /dev/tty.usbmodemTMCEVAL1). "
             "If omitted, all hardware tests are skipped.",
    )
    group.addoption(
        "--hw-chip",
        default=os.environ.get("TRINAMIC_HW_CHIP", "TMC5160"),
        choices=["TMC5160", "TMC2660"],
        help="Which chip is on the eval board.",
    )
    group.addoption(
        "--hw-rsense",
        type=float,
        default=float(os.environ.get("TRINAMIC_HW_RSENSE", "0.075")),
        help="Sense resistor value in ohms (0.075 for 5160-EVAL, 0.1 for 2660-EVAL).",
    )
    group.addoption(
        "--hw-fullsteps",
        type=int,
        default=int(os.environ.get("TRINAMIC_HW_FULLSTEPS", "200")),
        help="Full steps per revolution of the attached motor.",
    )
    group.addoption(
        "--hw-current-mA",
        type=float,
        default=float(os.environ.get("TRINAMIC_HW_CURRENT", "500")),
        help="Run current used for hardware tests, in mA RMS.",
    )
    group.addoption(
        "--hw-standstill-mA",
        type=float,
        default=float(os.environ.get("TRINAMIC_HW_STANDSTILL", "100")),
        help="Standstill current used for hardware tests, in mA RMS.",
    )
    group.addoption(
        "--hw-max-mA",
        type=float,
        default=float(os.environ.get("TRINAMIC_HW_MAX", "1000")),
        help="Hard safety cap on current (mA). Tests that would exceed this fail.",
    )


@pytest.fixture(scope="session")
def hw_port(request):
    port = request.config.getoption("--hw-port")
    if not port:
        pytest.skip(
            "Hardware tests skipped; pass --hw-port=/dev/tty.usbmodemTMCEVAL1 "
            "(or set TRINAMIC_HW_PORT) to run them."
        )
    return port


@pytest.fixture(scope="session")
def hw_chip(request):
    return request.config.getoption("--hw-chip")


@pytest.fixture(scope="session")
def hw_config(request):
    return MotorConfig(
        full_steps_per_rev=request.config.getoption("--hw-fullsteps"),
        sense_resistor_ohms=request.config.getoption("--hw-rsense"),
        max_current_mA_limit=request.config.getoption("--hw-max-mA"),
        default_microsteps=StepMode.USTEP_256,
    )


@pytest.fixture(scope="session")
def hw_currents(request):
    return (
        request.config.getoption("--hw-current-mA"),
        request.config.getoption("--hw-standstill-mA"),
    )


@pytest.fixture
def hw_motor(hw_port, hw_chip, hw_config):
    """A fresh motor per test, safely disabled on teardown.

    Scope is *function*, not session, so tests can't leak state into each
    other (e.g. leaving StealthChop on, or the motor energised).
    """
    with connection(hw_port) as conn:
        motor = create_motor(hw_chip, conn, config=hw_config)
        try:
            yield motor
        finally:
            # Always disable, even if the test raised
            try:
                motor.stop()
            except Exception:  # pragma: no cover
                logger.exception("stop() failed during teardown")
            try:
                motor.disable()
            except Exception:  # pragma: no cover
                logger.exception("disable() failed during teardown")
