from ._TMC_2209_logger import TMC_logger, Loglevel

import time
import logging

class TMC_2209:
    from ._TMC_2209_comm import (set_direction_reg, set_current, set_interpolation, get_spreadcycle, set_spreadcycle,
                                 set_microstepping_resolution, set_internal_rsense)

    from ._TMC_2209_move import (set_max_speed, set_acceleration, run_to_position_revolutions,
                                 run_to_position_revolutions_threaded, run_to_position_steps_threaded,
                                 wait_for_movement_finished_threaded,
                                 set_movement_abs_rel, get_current_position, set_current_position, distance_to_go)

    from ._TMC_2209_test import (
        test_stallguard_threshold
    )

    def __init__(self, pin_en, pin_step=-1, pin_dir=-1, baudrate=115200, serialport="/dev/serial0",
                 driver_address=0, gpio_mode=None, loglevel=None, logprefix=None,
                 log_handlers: list = None, log_formatter: logging.Formatter = None,
                 skip_uart_init: bool = False):
        self.tmc_logger = TMC_logger(loglevel, logprefix, log_handlers, log_formatter)

        self.tmc_logger.log("Using mock TMC library", Loglevel.WARNING)
        self.tmc_logger.log("Init", Loglevel.INFO)

    def set_step_mode(self, _step_mode: int):
        pass

    def set_motor_enabled(self, en):
        self.tmc_logger.log(f"Motor output active: {en}", Loglevel.INFO)

    def set_vactual(self, flag: bool):
        pass

    def set_vactual_rps(self, rps, duration=0, revolutions=0, acceleration=0):
        pass

    def read_steps_per_rev(self):
        return 200

    def do_homing(self, diag_pin, revolutions=10, threshold=None, speed_rpm=None):
        """homes the motor in the given direction using stallguard.
        this method is using vactual to move the motor and an interrupt on the DIAG pin

        Args:
            diag_pin (int): DIAG pin number
            revolutions (int): max number of revolutions. Can be negative for inverse direction
                (Default value = 10)
            threshold (int): StallGuard detection threshold (Default value = None)
            speed_rpm (float):speed in revolutions per minute (Default value = None)

        Returns:
            not homing_failed (bool): true when homing was successful
        """
        # Simulate the homing process
        time.sleep(5)

    def do_homing2(self, revolutions, threshold=None):
        """homes the motor in the given direction using stallguard
        old function, uses STEP/DIR to move the motor and pulls the StallGuard result
        from the interface

        Args:
            revolutions (int): max number of revolutions. Can be negative for inverse direction
            threshold (int, optional): StallGuard detection threshold (Default value = None)
        """
        # Simulate the homing process
        time.sleep(5)
