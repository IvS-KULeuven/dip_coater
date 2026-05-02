#!/usr/bin/env python3
"""TMC5160 homing and absolute-position example for the large lift.

What this script shows:
- how to set up the TMC5160 with the large setup profile
- how to home the lift using the configured reference switch direction
- how to move to absolute positions with explicit speeds and accelerations

Safe dummy run:
    uv run python examples/tmc5160_homing_example.py

Real hardware run:
    uv run python examples/tmc5160_homing_example.py --real-hardware --port /dev/ttyACM0

Edit ``POSITION_MOVES`` below to define your own target positions.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from dataclasses import dataclass

from dip_coater.app_state import AppState
from dip_coater.logging.motor_logger import TempLoggerHandler
from dip_coater.motor_driver.driver_registry import get_driver_spec
from dip_coater.motor_driver.motor_driver_interface import AvailableMotorDrivers
from dip_coater.services import MotionController
from dip_coater.setup_profiles import get_machine_profile
from dip_coater.setup_profiles.machine_profile import AvailableMachineSetups


DRIVER = AvailableMotorDrivers.TMC5160
SETUP = AvailableMachineSetups.LARGE_COATER


@dataclass(frozen=True)
class PositionMove:
    """Absolute target position and motion limits for one TMC5160 move."""

    position_mm: float
    speed_mm_s: float
    acceleration_mm_s2: float


POSITION_MOVES = (
    PositionMove(position_mm=10.0, speed_mm_s=2.0, acceleration_mm_s2=4.0),
    PositionMove(position_mm=25.0, speed_mm_s=5.0, acceleration_mm_s2=8.0),
    PositionMove(position_mm=5.0, speed_mm_s=1.5, acceleration_mm_s2=3.0),
)


def build_controller(
    *,
    use_dummy_driver: bool,
    interface: str,
    port: str,
) -> MotionController:
    """Create a motion controller for the TMC5160 large-coater setup."""
    driver_spec = get_driver_spec(DRIVER)
    setup_profile = driver_spec.adjust_setup_profile(get_machine_profile(SETUP))

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


async def run_homing_and_positions(
    controller: MotionController,
    *,
    homing_speed_mm_s: float,
) -> None:
    """Home the lift, then visit each configured absolute position."""
    controller.enable_motor()
    try:
        print(f"Homing at {homing_speed_mm_s:g} mm/s")
        homing_found = await controller.home_async(homing_speed_mm_s)
        if not homing_found:
            raise RuntimeError("Homing did not find the reference switch.")

        for move in POSITION_MOVES:
            print(
                f"Moving to {move.position_mm:g} mm at "
                f"{move.speed_mm_s:g} mm/s"
            )
            controller.move_to_position(
                move.position_mm,
                speed_mm_s=move.speed_mm_s,
                acceleration_mm_s2=move.acceleration_mm_s2,
            )
            await controller.wait_for_motor_done_async()
    finally:
        controller.disable_motor()


def parse_args() -> argparse.Namespace:
    """Read command-line options for hardware selection and homing speed."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--real-hardware", action="store_true")
    parser.add_argument("--interface", default="usb_tmcl")
    parser.add_argument("--port", default="/dev/ttyACM0")
    parser.add_argument("--homing-speed-mm-s", type=float, default=2.0)
    return parser.parse_args()


async def main_async() -> None:
    """Build the controller and run the homing position sequence."""
    args = parse_args()
    controller = build_controller(
        use_dummy_driver=not args.real_hardware,
        interface=args.interface,
        port=args.port,
    )
    try:
        await run_homing_and_positions(
            controller,
            homing_speed_mm_s=args.homing_speed_mm_s,
        )
    finally:
        controller.cleanup()


if __name__ == "__main__":
    asyncio.run(main_async())
