"""
Logging configuration for KrickBot.

Provides a centralized logger factory so every module uses a consistent format.
Usage:
    from app.utils.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Something happened")
"""

import logging
import sys
from app.config import settings


def get_logger(name: str) -> logging.Logger:
    """
    Create and return a logger with the given name.

    All loggers share:
    - The log level from settings (LOG_LEVEL env var, default INFO)
    - A consistent format: [timestamp] [level] [module] message
    - Output to stdout (not stderr) for easy container/cloud log capture
    """
    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers if get_logger is called multiple times
    if not logger.handlers:
        logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

        formatter = logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
