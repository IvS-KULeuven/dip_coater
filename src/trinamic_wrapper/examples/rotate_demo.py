"""
Rotate-demo equivalent using the wrapper.

Compare this to:
  examples/evalboards/TMC5160/rotate_demo.py in pytrinamic

The only thing you need to change to switch between the TMC5160 and the
TMC2660 is the CHIP string at the top.
"""

from __future__ import annotations

import time
from typing import Any

from trinamic_wrapper import (
    Chip,
    Direction,
    MotorConfig,
    StepMode,
    connection,
    create_motor,
)


# --- Change these to match your setup ------------------------------------
CHIP = Chip.TMC5160
PORT = "/dev/tty.usbmodemTMCEVAL1"   # macOS; on Linux typically /dev/ttyACM0
SENSE_RESISTOR_OHMS = 0.075 if CHIP is Chip.TMC5160 else 0.1
# -------------------------------------------------------------------------


def print_connection_info(conn: Any) -> None:
    print(f"TMCL connection: {conn}")

    try:
        version = conn.get_version_string()
    except Exception as exc:
        print(f"Board version query failed: {exc!r}")
    else:
        print(f"Board version: {version}")


def main() -> None:
    config = MotorConfig(
        full_steps_per_rev=200,
        sense_resistor_ohms=SENSE_RESISTOR_OHMS,
        clock_hz=16_000_000.0,
        default_microsteps=StepMode.USTEP_256,
        max_current_mA_limit=1500.0,
    )

    # Pass PORT=None (or drop the argument) to let pytrinamic pick the first
    # available USB-TMCL device — convenient when only the Landungsbrücke
    # is connected.
    with connection(PORT) as conn:
        print_connection_info(conn)
        motor = create_motor(CHIP, conn, config=config)

        # Configure
        motor.set_step_mode(StepMode.USTEP_256)
        motor.set_run_current_mA(1500)
        motor.set_standstill_current_mA(200)
        motor.set_speed_rps(0.05)
        motor.set_acceleration_rps2(1.0)

        # Optional: silent mode if supported
        if motor.has_feature("stealthchop"):
            motor.set_stealthchop(False, threshold_rps=3.0)
        if motor.has_feature("interpolation"):
            motor.set_interpolation(False)

        motor.enable()

        print("Rotating forward…")
        motor.rotate(direction=Direction.CW)
        time.sleep(2.0)

        print("Stopping…")
        motor.stop()
        time.sleep(0.5)

        '''print("Rotating backward by 0.5 revolutions…")
        motor.reset_position()
        motor.rotate_by(0.5, direction=Direction.CCW)

        # Block until the relative move completes (or 10 s timeout)
        reached = motor.wait_until_reached(timeout_s=10.0)
        print(f"Reached target: {reached}")
        print(f"Final position: {motor.get_actual_position_rot():.3f} rev")'''

        motor.disable()


if __name__ == "__main__":
    main()
