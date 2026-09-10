"""Logging configuration for the finance data platform.

Implements docs/engineering/engineering-standards.md §5 literally: structured
JSON logs, never plain text -- so a log line's `run_id`, `dataset_id`,
`alert_type`, or any other field passed via `extra={...}` is queryable by a
log processor (or a human) without regex-parsing a formatted string. This
module previously emitted a human-readable but non-JSON line despite its own
docstring claiming "structured logging" -- a real doc/code gap, fixed here
because EPIC-08's alerting (src/common/alerting.py) is the first real
consumer that needs these lines to actually be machine-parseable.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

# Every attribute a stdlib LogRecord carries by default -- excluded so a
# formatted line's top-level keys are only the standard ones below plus
# whatever a caller passed via `extra={...}`.
_STANDARD_LOG_RECORD_ATTRS = frozenset(
    {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "taskName",
        "message",
    }
)


class _JSONFormatter(logging.Formatter):
    """Renders one log line as one JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in vars(record).items():
            if key not in _STANDARD_LOG_RECORD_ATTRS:
                payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def setup_logging(
    name: str,
    level: str = "INFO",
    correlation_id: str | None = None,
) -> logging.Logger:
    """Set up a logger emitting one JSON object per line.

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
    handler.setFormatter(_JSONFormatter())
    logger.addHandler(handler)
    logger.propagate = False

    if correlation_id:
        logger.info("Initialized", extra={"correlation_id": correlation_id})

    return logger
