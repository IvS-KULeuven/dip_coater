from ._TMC_2209_logger import TMC_logger, Loglevel

class TMC_2209:
    from ._TMC_2209_comm import (set_direction_reg, set_current, set_interpolation, set_spreadcycle,
                                 set_microstepping_resolution, set_internal_rsense)

    def __init__(self, pin_en, pin_step=-1, pin_dir=-1, baudrate=115200, serialport="/dev/serial0",
                 driver_address=0, gpio_mode=None, loglevel=None, skip_uart_init=False):
        self.tmc_logger = TMC_logger(loglevel, f"TMC2209 {driver_address}")

    def set_stepmode(self, ):
        pass

    def set_motor_enabled(self, en):
        pass

    def set_vactual_rps(self, rps, duration=0, revolutions=0, acceleration=0):
        pass
