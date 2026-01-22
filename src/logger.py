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

import logging
import os
import sys

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
