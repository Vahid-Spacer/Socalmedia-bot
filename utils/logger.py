"""Centralized, professional logging configuration for the bot manager."""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured_loggers: set[str] = set()


def setup_logger(name: str, log_dir: str = "logs") -> logging.Logger:
    """Create (or return an already configured) logger.

    The logger writes:
        - all records of level INFO and above to ``{log_dir}/manager.log``
        - all records of level ERROR and above to ``{log_dir}/errors.log``
        - all records of level INFO and above to the console

    Args:
        name: Logger name, typically ``__name__`` of the calling module.
        log_dir: Directory in which log files are stored. Created if missing.

    Returns:
        A fully configured ``logging.Logger`` instance.
    """
    logger = logging.getLogger(name)

    if name in _configured_loggers:
        return logger

    os.makedirs(log_dir, exist_ok=True)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    general_handler = RotatingFileHandler(
        filename=os.path.join(log_dir, "manager.log"),
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    general_handler.setLevel(logging.INFO)
    general_handler.setFormatter(formatter)

    error_handler = RotatingFileHandler(
        filename=os.path.join(log_dir, "errors.log"),
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger.addHandler(general_handler)
    logger.addHandler(error_handler)
    logger.addHandler(console_handler)

    _configured_loggers.add(name)
    return logger
