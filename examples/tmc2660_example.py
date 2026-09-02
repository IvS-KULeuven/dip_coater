#!/usr/bin/env python3
"""TMC2660 example for the large dip-coater setup.

What this script shows:
- how to select the TMC2660 driver
- how to select the large setup profile
- how to build the AppState, motor driver, and MotionController in Python
- how to run a simple down/up motion test

Safe dummy run:
    uv run python examples/tmc2660_example.py

The bundled ``large`` profile uses TMC5160 reference inputs. The legacy
TMC2660 backend cannot read those switches, so ``--real-hardware`` is rejected
until a verified GPIO-backed profile is selected in code.
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from dip_coater.app_state import AppState
from dip_coater.logging.motor_logger import TempLoggerHandler
from dip_coater.motor_driver.driver_registry import (
    get_driver_spec,
    validate_driver_setup_compatibility,
)
from dip_coater.motor_driver.motor_driver_interface import AvailableMotorDrivers
from dip_coater.services import MotionController
from dip_coater.setup_profiles import get_machine_profile
from dip_coater.setup_profiles.machine_profile import (
    AvailableMachineSetups,
    HomeDirection,
)


DRIVER = AvailableMotorDrivers.TMC2660
SETUP = AvailableMachineSetups.LARGE_COATER


def build_controller(
    *,
    use_dummy_driver: bool,
    interface: str,
    port: str,
) -> MotionController:
    """Create a motion controller for the TMC2660 large-coater setup."""
    driver_spec = get_driver_spec(DRIVER)
    setup_profile = driver_spec.adjust_setup_profile(get_machine_profile(SETUP))
    validate_driver_setup_compatibility(
        DRIVER,
        setup_profile,
        use_dummy_driver=use_dummy_driver,
    )

    app_state = AppState(
        DRIVER,
        setup_profile,
        gpio_required=(driver_spec.requires_gpio or setup_profile.requires_gpio),
    )
    app_state.config.USE_DUMMY_DRIVER = use_dummy_driver

    log_handler = TempLoggerHandler()
    motor_driver = driver_spec.driver_factory(
        app_state=app_state,
        log_level=driver_spec.log_level_from_name("INFO"),
        log_handlers=[log_handler],
        log_formatter=logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"),
        interface_type=interface,
        port=port,
    )

    controller = MotionController(motor_driver, setup_profile, gpio=app_state.gpio)
    controller.setup_limit_switches_io()
    controller.bind_limit_switches_to_motor()
    return controller


async def run_down_up_test(
    controller: MotionController,
    *,
    distance_mm: float,
    speed_mm_s: float,
    acceleration_mm_s2: float,
) -> None:
    """Enable the lift, move down once, move back up, and disable the motor."""
    controller.enable_motor()
    try:
        print(f"Moving down {distance_mm:g} mm at {speed_mm_s:g} mm/s")
        controller.move_down(distance_mm, speed_mm_s, acceleration_mm_s2)
        await controller.wait_for_motor_done_async(
            active_limit_direction=HomeDirection.DOWN
        )

        print(f"Moving up {distance_mm:g} mm at {speed_mm_s:g} mm/s")
        controller.move_up(distance_mm, speed_mm_s, acceleration_mm_s2)
        await controller.wait_for_motor_done_async(
            active_limit_direction=HomeDirection.UP
        )
    finally:
        controller.disable_motor()


def parse_args() -> argparse.Namespace:
    """Read command-line options for hardware selection and test motion."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--real-hardware", action="store_true")
    parser.add_argument("--interface", default="usb_tmcl")
    parser.add_argument("--port", default="interactive")
    parser.add_argument("--distance-mm", type=float, default=2.0)
    parser.add_argument("--speed-mm-s", type=float, default=1.0)
    parser.add_argument("--acceleration-mm-s2", type=float, default=2.0)
    return parser.parse_args()


async def main_async() -> None:
    """Build the controller and run the down/up motion test."""
    args = parse_args()
    controller = build_controller(
        use_dummy_driver=not args.real_hardware,
        interface=args.interface,
        port=args.port,
    )
    try:
        await run_down_up_test(
            controller,
            distance_mm=args.distance_mm,
            speed_mm_s=args.speed_mm_s,
            acceleration_mm_s2=args.acceleration_mm_s2,
        )
    finally:
        controller.cleanup()


if __name__ == "__main__":
    asyncio.run(main_async())
