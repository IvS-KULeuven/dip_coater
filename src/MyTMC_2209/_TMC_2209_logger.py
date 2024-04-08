from enum import Enum

class Loglevel(Enum):
    """loglevel"""
    NONE = 0
    ERROR = 10
    INFO = 20
    DEBUG = 30
    MOVEMENT = 40
    ALL = 100


class TMC_logger:
    def __init__(self, loglevel=Loglevel.INFO, logprefix="TMC2209"):
        pass

    def set_loglevel(self, loglevel):
        pass
