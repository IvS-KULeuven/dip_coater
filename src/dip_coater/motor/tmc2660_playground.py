"""
Move a motor back and forth using velocity and position mode of the TMC2660.
"""
import time
import pytrinamic
from pytrinamic.modules import Landungsbruecke

from TMC_2209._TMC_2209_logger import Loglevel
from dip_coater.motor.tmc2660 import TMC2660_MotorDriver
from dip_coater.motor.mechanical_setup import MechanicalSetup

pytrinamic.show_info()

USE_DUMMY = False
FULL_STEPS = 200
MM_PER_REVOLUTION = 4  # Adjust this value based on your mechanical setup


def print_lb_content(lb: Landungsbruecke):
    print("ID EEPROM content:")
    print("Mc: ", lb.eeprom_drv.read_id_info())
    print("Drv:", lb.eeprom_mc.read_id_info())

    print("Board IDs:")
    print(lb.get_board_ids())

    print("Board Names:")
    print(lb.get_board_names())


class DummyAppState:
    def __init__(self, mechanical_setup):
        self.mechanical_setup = mechanical_setup


# Create a dummy app state with a mechanical setup
mechanical_setup = MechanicalSetup(mm_per_revolution=MM_PER_REVOLUTION, steps_per_revolution=FULL_STEPS)
app_state = DummyAppState(mechanical_setup)

# Initialize the TMC2660 driver
driver = TMC2660_MotorDriver(
    app_state,
    interface_type="usb_tmcl" if not USE_DUMMY else "dummy_tmcl",
    port="/dev/ttyACM0" if not USE_DUMMY else None,
    step_mode=128,
    current_mA=2000,
    current_standstill_mA=200,
    loglevel=Loglevel.INFO
)

# Print Landungsbrücke content
lb = Landungsbruecke(driver.interface)
print_lb_content(lb)

# Configure the motor
driver.set_acceleration(100)  # 100 mm/s^2

# Wait for the driver to be ready
time.sleep(0.5)

# Enable the driver
driver.enable_motor()

print("Rotating...")
driver.rotate(5, 2)    # Rotate 2 revolutions at 1 rps
driver.wait_until_target_reached()

print("Stopping...")
driver.stop_motor()
time.sleep(1)

print("Rotating...")
driver.rotate(-1, 0.25)   # Rotate 1 revolution at 0.25 rps
driver.wait_until_target_reached()

print("Stopping...")
driver.motor.stop()

# Clean up
driver.cleanup()

print("\nReady.")