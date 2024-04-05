import RPi.GPIO as GPIO
from RpiMotorLib import RpiMotorLib
import time

# ===== GLOBAL VARS =====
ROD_PITCH = 2  # The pitch of the motor rod screw thread in mm
motor_driver = None # (Call init_motor_driver to initialize this var)

def get_DIP_positions_for_mode(step_mode):
    dip_positions = {
        "Full": "MS3: 0\tMS2: 0\tMS1: 0",
        "Half": "MS3: 0\tMS2: 0\tMS1: 1",
        "1/4": "MS3: 0\tMS2: 1\tMS1: 0",
        "1/8": "MS3: 0\tMS2: 1\tMS1: 1",
        "1/16": "MS3: 1\tMS2: 1\tMS1: 1"
    }
    return dip_positions[step_mode]

def calculate_steps_and_delay(speed_mm_s, distance_mm, step_mode):
    # For 1 revolution, you move up 9 mm
    # For each step mode, the number of steps required to do
    # one full revolution differs:
    #  - Full mode: 200 steps/rev
    #  - Half mode: 400 steps/rev
    #  - 1/4 mode:  800 steps/rev
    #  - 1/8 mode:  1600 steps/rev
    #  - 1/16 mode: 3200 steps/rev
    # We know that one full revolution moves the plate up
    # 9 mm (= the height of one full spiral on the motor
    # threaded rod). So, we can calculate the translation
    # that one step accomplishes for each step mode, for
    # example for full step mode:
    #    step_distance = 9mm/rev / 200 steps/rev = 0.045 mm/step
    step_distances = {
        "Full": 0.045,
        "Half": 0.0225,
        "1/4": 0.01125,
        "1/8": 0.005625,
        "1/16": 0.0028125
    }

    distance_per_step = step_distances[step_mode]
    steps = int(distance_mm / distance_per_step)
    steps_per_second = speed_mm_s / distance_per_step
    delay = 1 / steps_per_second
    return steps, delay

def init_motor_driver():
    global EN_pin, motor_driver

    # Define the GPIO pins
    direction_pin = 7  # Direction (DIR) GPIO Pin
    step_pin = 21      # Step GPIO Pin
    EN_pin = 16        # enable pin (LOW to enable)

    # Declare a instance of class pass GPIO pins numbers and the motor type
    motor_driver = RpiMotorLib.A4988Nema(direction_pin, step_pin, (-1,-1,-1), "DRV8825")
    GPIO.setup(EN_pin, GPIO.OUT) # set enable pin as output

def enable_motor():
    """ Arm the motor"""
    GPIO.output(EN_pin, GPIO.LOW)

def disable_motor():
    """ Disarm the motor """
    GPIO.output(EN_pin, GPIO.HIGH)

def drive_motor(distance_mm, speed_mm_s, step_mode, clockwise=False, verbose=False):
    steps, step_delay = calculate_steps_and_delay(speed_mm_s, distance_mm, step_mode)
    motor_driver.motor_go(clockwise, # True=Clockwise, False=Counter-Clockwise
                     step_mode , # Step type (Full,Half,1/4,1/8,1/16,1/32)
                     steps, # number of steps
                     step_delay, # step delay [sec]
                     verbose, # True = print verbose output
                     0.05) # initial delay [sec]

def move_up(distance_mm, speed_mm_s, step_mode, verbose=False):
    """
    Move up <distance> mm at <speed> mm/s using <step_mode> step mode..
    """
    drive_motor(distance_mm, speed_mm_s, step_mode, False, verbose)

def move_down(distance_mm, speed_mm_s, step_mode, verbose=False):
    """
    Move down <distance> mm at <speed> mm/s using <step_mode> step mode.
    """
    drive_motor(distance_mm, speed_mm_s, step_mode, True, verbose)

if __name__ == "__main__":
    # Step mode ('Full', 'Half', '1/4', '1/8' or '1/16')
    # Lower step modes have a more smooth progression, but
    # we have a cheap knock-off driver which can't handle
    # too low modes.
    step_mode = "1/4"
    print("Adjust the driver's DIP switches according to step mode", step_mode, "!!!")
    print(get_DIP_positions_for_mode(step_mode))
    #input("Verify the DIP switches. Press 'Enter' to continue...")

    # Movement speed in mm/s
    speed_up = 10
    speed_down = 10

    # Time to wait (in s) between going up and down
    wait_time = 1

    # Vertical travel distance in mm
    distance_up = 50
    distance_down = 50

    # ======== INIT ========
    init_motor_driver()

    enable_motor()

    # ======== MOVE DOWN ========
    move_down(distance_down, speed_down, step_mode)

    # ======== WAIT ========
    time.sleep(wait_time)

    # ======== MOVE UP ========
    move_up(distance_up, speed_up, step_mode)

    disable_motor()

    GPIO.cleanup() # clear GPIO allocations after run
