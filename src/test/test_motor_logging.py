import logging
from uuid import uuid4

import pytest

from dip_coater.logging.tmc2660_logger import (
    TMC2660LogLevel,
    TMC2660Logger,
)
from dip_coater.logging.tmc5160_logger import (
    TMC5160LogLevel,
    TMC5160Logger,
)


@pytest.mark.parametrize(
    ("logger_type", "level"),
    [
        (TMC2660Logger, TMC2660LogLevel.INFO),
        (TMC5160Logger, TMC5160LogLevel.INFO),
    ],
)
def test_motor_logger_removes_only_handlers_it_owns(logger_type, level):
    logger_name = f"{__name__}.{uuid4()}"
    logger = logging.getLogger(logger_name)
    external_handler = logging.NullHandler()
    owned_handler_1 = logging.NullHandler()
    owned_handler_2 = logging.NullHandler()
    logger.addHandler(external_handler)

    try:
        motor_logger = logger_type(
            logprefix=logger_name,
            loglevel=level,
            handlers=[owned_handler_1],
        )
        motor_logger.add_handler(owned_handler_2)

        motor_logger.remove_all_handlers()

        assert logger.handlers == [external_handler]
    finally:
        logger.handlers.clear()
