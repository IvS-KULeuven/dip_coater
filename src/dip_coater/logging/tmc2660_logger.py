import logging
from enum import Enum


class TMC2660LogLevel(Enum):
    """TMC2660 Log Levels"""
    ALL = 1
    MOVEMENT = 5
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL
    NONE = 100


class TMC2660Logger:
    """TMC2660 Logger

    This class handles logging for the TMC2660 driver.
    """

    def __init__(self,
                 loglevel: TMC2660LogLevel = TMC2660LogLevel.INFO,
                 logprefix: str = "TMC2660",
                 handlers: list = None,
                 formatter: logging.Formatter = None):
        """Constructor

        Args:
            logprefix (str): Logger name prefix (default: "TMC2660")
            loglevel (TMC2660LogLevel): Initial log level
            handlers (list): List of logging handlers (default: None)
            formatter (logging.Formatter): Log message formatter (default: None)
        """
        if logprefix is None:
            logprefix = "TMC2660"

        # Add custom log levels
        for level in [TMC2660LogLevel.ALL, TMC2660LogLevel.MOVEMENT, TMC2660LogLevel.NONE]:
            self._add_logging_level(level.name, level.value)

        self.logger = logging.getLogger(logprefix)

        self.loglevel = loglevel
        self.set_loglevel(loglevel)
        if formatter is None:
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.formatter = formatter

        if handlers is None:
            handlers = [logging.StreamHandler()]

        for handler in handlers:
            handler.setFormatter(self.formatter)
            self.logger.addHandler(handler)

        self.logger.propagate = True

    def set_logprefix(self, logprefix: str):
        """Set the log prefix (logger name)"""
        self.logger.name = logprefix

    def set_loglevel(self, loglevel: TMC2660LogLevel):
        """Set the log level"""
        if loglevel is None:
            loglevel = TMC2660LogLevel.INFO
        self.loglevel = loglevel
        self.logger.setLevel(loglevel.value)

    def add_handler(self, handler, formatter=None):
        """Add a handler to the logger"""
        if formatter is None:
            formatter = self.formatter
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def remove_handler(self, handler):
        """Remove a handler from the logger"""
        self.logger.removeHandler(handler)

    def remove_all_handlers(self):
        """Remove all handlers from the logger"""
        for handler in self.logger.handlers:
            self.logger.removeHandler(handler)

    def set_formatter(self, formatter, handlers=None):
        """Set a new formatter for the log messages"""
        self.formatter = formatter
        if handlers is None:
            handlers = self.logger.handlers
        for handler in handlers:
            handler.setFormatter(formatter)

    @staticmethod
    def _add_logging_level(level_name: str, level_num: int, method_name: str = None):
        """Add a new logging level to the `logging` module"""
        if not method_name:
            method_name = level_name.lower()

        def logForLevel(self, message, *args, **kwargs):
            if self.isEnabledFor(level_num):
                self._log(level_num, message, args, **kwargs)

        def logToRoot(message, *args, **kwargs):
            logging.log(level_num, message, *args, **kwargs)

        logging.addLevelName(level_num, level_name)
        setattr(logging, level_name, level_num)
        setattr(logging.getLoggerClass(), method_name, logForLevel)
        setattr(logging, method_name, logToRoot)

    def log(self, message, loglevel: TMC2660LogLevel = TMC2660LogLevel.INFO):
        """Log a message"""
        if self.loglevel is not TMC2660LogLevel.NONE:
            self.logger.log(loglevel.value, message)