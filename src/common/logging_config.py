"""Logging configuration for the finance data platform.

Provides structured logging with correlation IDs for traceability across
ingestion, validation, and transformation stages.
"""

import logging
import sys
from typing import Optional


def setup_logging(
    name: str,
    level: str = "INFO",
    correlation_id: Optional[str] = None,
) -> logging.Logger:
    """Set up a logger with structured formatting.

    Args:
        name: Logger name (typically __name__).
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        correlation_id: Optional ID to track related operations across services.

    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Avoid adding multiple handlers if logger already configured
    if logger.handlers:
        return logger

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Structured format with timestamp, level, logger name, and message
    formatter = logging.Formatter(
        fmt=(
            "%(asctime)s | %(levelname)-8s | %(name)s | "
            "%(message)s"
        ),
        datefmt="%Y-%m-%d %H:%M:%S UTC",
    )

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False

    if correlation_id:
        logger.info("Initialized with correlation_id=%s", correlation_id)

    return logger
