import logging
from enum import Enum


class TMC5160LogLevel(Enum):
    """TMC5160 log levels."""

    ALL = 1
    MOVEMENT = 5
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL
    NONE = 100


class TMC5160Logger:
    """Logger wrapper for the TMC5160 driver."""

    def __init__(
        self,
        loglevel: TMC5160LogLevel = TMC5160LogLevel.INFO,
        logprefix: str = "TMC5160",
        handlers: list = None,
        formatter: logging.Formatter = None,
    ):
        if logprefix is None:
            logprefix = "TMC5160"

        for level in [
            TMC5160LogLevel.ALL,
            TMC5160LogLevel.MOVEMENT,
            TMC5160LogLevel.NONE,
        ]:
            self._add_logging_level(level.name, level.value)

        self.logger = logging.getLogger(logprefix)

        self.loglevel = loglevel
        self.set_loglevel(loglevel)
        if formatter is None:
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
        self.formatter = formatter

        if handlers is None:
            handlers = [logging.StreamHandler()]

        for handler in handlers:
            handler.setFormatter(self.formatter)
            self.logger.addHandler(handler)

        self.logger.propagate = True

    def set_loglevel(self, loglevel: TMC5160LogLevel):
        if loglevel is None:
            loglevel = TMC5160LogLevel.INFO
        self.loglevel = loglevel
        self.logger.setLevel(loglevel.value)

    def add_handler(self, handler, formatter=None):
        if formatter is None:
            formatter = self.formatter
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def remove_handler(self, handler):
        self.logger.removeHandler(handler)

    @staticmethod
    def _add_logging_level(level_name: str, level_num: int, method_name: str = None):
        if not method_name:
            method_name = level_name.lower()

        def log_for_level(self, message, *args, **kwargs):
            if self.isEnabledFor(level_num):
                self._log(level_num, message, args, **kwargs)

        def log_to_root(message, *args, **kwargs):
            logging.log(level_num, message, *args, **kwargs)

        logging.addLevelName(level_num, level_name)
        setattr(logging, level_name, level_num)
        setattr(logging.getLoggerClass(), method_name, log_for_level)
        setattr(logging, method_name, log_to_root)

    def log(self, message, loglevel: TMC5160LogLevel = TMC5160LogLevel.INFO):
        if self.loglevel is not TMC5160LogLevel.NONE:
            self.logger.log(loglevel.value, message)
