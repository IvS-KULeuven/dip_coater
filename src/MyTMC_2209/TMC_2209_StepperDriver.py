from ._TMC_2209_logger import TMC_logger, Loglevel

class TMC_2209:
    from ._TMC_2209_comm import (set_direction_reg, set_current, set_interpolation, set_spreadcycle,
                                 set_microstepping_resolution, set_internal_rsense)

    from ._TMC_2209_move import (set_max_speed, set_acceleration, run_to_position_revolutions, set_movement_abs_rel)

    def __init__(self, pin_en, pin_step=-1, pin_dir=-1, baudrate=115200, serialport="/dev/serial0",
                 driver_address=0, gpio_mode=None, loglevel=None, logprefix=None,
                 log_handlers=None, skip_uart_init=False):
        self.tmc_logger = TMC_logger(loglevel, logprefix, log_handlers)

        self.tmc_logger.log("Using mock TMC library", Loglevel.WARNING)
        self.tmc_logger.log("Init", Loglevel.INFO)

    def set_stepmode(self, _stepmode: int):
        pass

    def set_motor_enabled(self, en):
        self.tmc_logger.log(f"Motor output active: {en}", Loglevel.INFO)

    def set_vactual(self, flag: bool):
        pass

    def set_vactual_rps(self, rps, duration=0, revolutions=0, acceleration=0):
        pass

    def read_steps_per_rev(self):
        return 200
