"""Simple logging configuration for MiSalud Entendida.

Usage:
    from src.logger import get_logger

    logger = get_logger(__name__)
    logger.info("Processing prescription...")
    logger.debug("Raw response: %s", response[:100])
    logger.error("Failed to parse JSON: %s", str(e))

Environment variables:
    LOG_LEVEL: Set to DEBUG, INFO, WARNING, ERROR (default: INFO)
"""

import functools
import logging
import os
import sys
from contextlib import contextmanager
from time import perf_counter
from typing import Iterator

# Default format: timestamp - module - level - message
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%H:%M:%S"  # Keep it short for console

_configured = False


def _configure_root():
    """Configure root logger once."""
    global _configured
    if _configured:
        return

    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))

    # Configure root logger for src.* modules
    root = logging.getLogger("src")
    root.setLevel(level)
    root.addHandler(handler)
    root.propagate = False  # Don't double-log to root

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger for a module.

    Args:
        name: Module name, typically __name__

    Returns:
        Configured logger instance
    """
    _configure_root()
    return logging.getLogger(name)


@contextmanager
def log_timing(
    logger: logging.Logger, label: str, level: int = logging.INFO
) -> Iterator[None]:
    """Log the duration of a code block.

    Example:
        with log_timing(logger, "load_model"):
            ...
    """
    start = perf_counter()
    try:
        yield
    finally:
        elapsed = perf_counter() - start
        logger.log(level, "%s took %.2fs", label, elapsed)


def timed(
    logger: logging.Logger, label: str | None = None, level: int = logging.INFO
):
    """Decorator to log function duration with a shared logger."""

    def decorator(func):
        name = label or func.__name__

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with log_timing(logger, name, level=level):
                return func(*args, **kwargs)

        return wrapper

    return decorator
