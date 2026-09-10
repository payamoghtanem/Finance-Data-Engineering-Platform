"""Tests for src/common/logging_config.py (engineering-standards.md §5)."""

from __future__ import annotations

import io
import json
import logging

from src.common.logging_config import setup_logging


def _capture(logger: logging.Logger) -> io.StringIO:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(logger.handlers[0].formatter)
    logger.handlers = [handler]
    return stream


class TestSetupLogging:
    def test_emits_valid_json(self) -> None:
        logger = setup_logging("test.json.valid")
        stream = _capture(logger)

        logger.info("hello world")

        line = stream.getvalue().strip()
        parsed = json.loads(line)
        assert parsed["message"] == "hello world"
        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test.json.valid"
        assert "timestamp" in parsed

    def test_extra_fields_pass_through(self) -> None:
        logger = setup_logging("test.json.extra")
        stream = _capture(logger)

        logger.error(
            "ALERT consecutive_failures",
            extra={"alert_type": "consecutive_failures", "dataset_id": "fred_cpiaucsl"},
        )

        parsed = json.loads(stream.getvalue().strip())
        assert parsed["alert_type"] == "consecutive_failures"
        assert parsed["dataset_id"] == "fred_cpiaucsl"

    def test_reused_logger_does_not_duplicate_handlers(self) -> None:
        first = setup_logging("test.json.reuse")
        second = setup_logging("test.json.reuse")
        assert first is second
        assert len(first.handlers) == 1
