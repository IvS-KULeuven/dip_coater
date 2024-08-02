"""
Move a motor back and forth using velocity and position mode of the TMC2660.
"""
import time
import pytrinamic
from pytrinamic.connections import ConnectionManager
from pytrinamic.evalboards import TMC2660_eval
from pytrinamic.modules import Landungsbruecke

pytrinamic.show_info()


USE_DUMMY = False
FULL_STEPS = 200


def print_lb_content(lb: Landungsbruecke):
    print("ID EEPROM content:")
    print("Mc: ", lb.eeprom_drv.read_id_info())
    print("Drv:", lb.eeprom_mc.read_id_info())

    print("Board IDs:")
    print(lb.get_board_ids())

    print("Board Names:")
    print(lb.get_board_names())


def convert_microsteps_idx_to_steps(microsteps: int):
    match microsteps:
        case 0:
            return 1
        case 1:
            return 2
        case 2:
            return 4
        case 3:
            return 8
        case 4:
            return 16
        case 5:
            return 32
        case 6:
            return 64
        case 7:
            return 128
        case 8:
            return 256

def get_microsteps(eval_board, motor, axis) -> int:
    mstep = eval_board.get_axis_parameter(motor.AP.MicrostepResolution, axis)
    return convert_microsteps_idx_to_steps(mstep)

def get_vpps_from_rps(microsteps: int, rps:float) -> int:
    return int(round(FULL_STEPS * microsteps * rps))

def print_register_dump(eval_board):
    drv = eval_board.ics[0]
    print("Driver info: " + str(drv.get_info()))
    print("Register dump for " + str(drv.get_name()) + ":")

    print("DRVSTATUS_MSTEP:       0x{0:08X}".format(eval_board.read_register(drv.REG.DRVSTATUS_MSTEP)))
    print("DRVSTATUS_SG:          0x{0:08X}".format(eval_board.read_register(drv.REG.DRVSTATUS_SG)))
    print("DRVSTATUS_SG_SE:       0x{0:08X}".format(eval_board.read_register(drv.REG.DRVSTATUS_SG_SE)))
    print("DRVCTRL:               0x{0:08X}".format(eval_board.read_register(drv.REG.DRVCTRL)))
    print("CHOPCONF:              0x{0:08X}".format(eval_board.read_register(drv.REG.CHOPCONF)))
    print("SMARTEN:               0x{0:08X}".format(eval_board.read_register(drv.REG.SMARTEN)))
    print("SGCSCONF:              0x{0:08X}".format(eval_board.read_register(drv.REG.SGCSCONF)))
    print("DRVCONF:               0x{0:08X}".format(eval_board.read_register(drv.REG.DRVCONF)))

if USE_DUMMY:
    my_interface = ConnectionManager("--interface dummy_tmcl").connect()
else:
    my_interface = ConnectionManager("--interface usb_tmcl --port interactive").connect()
print(my_interface)

# Create TMC2660-EVAL class which communicates over the Landungsbrücke via TMCL
eval_board = TMC2660_eval(my_interface)
print_register_dump(eval_board)

# Get the Landungsbrücke module and print its contents
lb = Landungsbruecke(my_interface)
print_lb_content(lb)

# Get the motor instance
motor = eval_board.motors[0]

# Disable the driver
active_state = my_interface.get_global_parameter(lb.GP.DriversEnable)
print("Driver active: " + str(active_state))
my_interface.set_global_parameter(lb.GP.DriversEnable, 0)
active_state = my_interface.get_global_parameter(lb.GP.DriversEnable)
print("Driver active: " + str(active_state))



# Configure the motor
motor.set_axis_parameter(motor.AP.MaxVelocity, 1000)
motor.set_axis_parameter(motor.AP.MaxAcceleration, 10000)
# TODO:

# Enable the driver
my_interface.set_global_parameter(lb.GP.DriversEnable, 1)
# TODO

print("Rotating...")
microsteps = get_microsteps(eval_board, motor, 0)
motor.rotate(get_vpps_from_rps(microsteps, 0.5))
time.sleep(2)

print("Stopping...")
motor.stop()
time.sleep(1)

print("Moving back to 0...")
motor.move_to(0, 10*25600)

# Wait until position 0 is reached
while motor.actual_position != 0:
    print("Actual position: " + str(motor.actual_position))
    time.sleep(0.2)

print("Reached position 0")

my_interface.close()

print("\nReady.")