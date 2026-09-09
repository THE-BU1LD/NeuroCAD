# logging_config.py

import logging
from config import config


def setup_logging():
    level = logging.DEBUG if config.pipeline.debug else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def get_logger(name: str):
    return logging.getLogger(name)
