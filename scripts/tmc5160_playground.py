#!/usr/bin/env python3
"""TMC5160 playground script.

Connects to a TMC5160-EVAL via Landungsbrücke and dumps all registers.

Usage:
    # With real hardware (auto-detect USB port):
    python scripts/tmc5160_playground.py

    # With a specific port:
    python scripts/tmc5160_playground.py --port /dev/tty.usbmodemTMCEVAL1

    # Dummy mode (no hardware needed):
    python scripts/tmc5160_playground.py --dummy
"""
import argparse
import sys
from types import SimpleNamespace

from dip_coater.logging.tmc5160_logger import TMC5160LogLevel
from dip_coater.mechanical.mechanical_setup import MechanicalSetup
from dip_coater.motor.tmc5160 import MotorDriverTMC5160


def make_app_state(*, use_dummy: bool):
    return SimpleNamespace(
        mechanical_setup=MechanicalSetup(mm_per_revolution=4.0),
        config=SimpleNamespace(
            USE_DUMMY_DRIVER=use_dummy,
            DEFAULT_GLOBAL_SCALER=0,
            DEFAULT_RSENSE=75,
        ),
    )


def main():
    parser = argparse.ArgumentParser(description="TMC5160 playground")
    parser.add_argument(
        "--dummy", action="store_true", help="Use dummy backend (no hardware)"
    )
    parser.add_argument(
        "--interface", default="usb_tmcl", help="Interface type (default: usb_tmcl)"
    )
    parser.add_argument(
        "--port", default="interactive", help="Port (default: interactive)"
    )
    args = parser.parse_args()

    app_state = make_app_state(use_dummy=args.dummy)

    interface_type = "dummy_tmcl" if args.dummy else args.interface
    port = None if args.dummy else args.port

    print("Connecting to TMC5160...")
    try:
        driver = MotorDriverTMC5160(
            app_state,
            interface_type=interface_type,
            port=port,
            step_mode=256,
            current_mA=2800,
            current_standstill_mA=100,
            loglevel=TMC5160LogLevel.INFO,
        )
    except Exception as e:
        print(f"Failed to connect: {e}", file=sys.stderr)
        sys.exit(1)

    print("\n=== Register Dump ===\n")
    driver.register_dump()

    print("\nDone. Cleaning up...")
    driver.cleanup()


if __name__ == "__main__":
    main()
