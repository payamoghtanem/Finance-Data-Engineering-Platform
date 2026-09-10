"""Unit tests for src/common/alerting.py (FR-OPS-002, NFR-FRESH-003, EPIC-08)."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta

from src.common.alerting import (
    AlertEvent,
    detect_blocking_quality_failure,
    detect_consecutive_failures,
    detect_freshness_breach,
    emit_alert,
)
from src.common.data_quality_result import DataQualityResult
from src.common.ingestion_run import IngestionRun
from src.common.logging_config import _JSONFormatter

_T0 = datetime(2026, 9, 10, 12, 0, 0, tzinfo=UTC)


def _run(
    *, status: str, hours_offset: int = 0, run_id: str = "run-1", error: str | None = None
) -> IngestionRun:
    started = _T0 + timedelta(hours=hours_offset)
    return IngestionRun(
        run_id=run_id,
        dataset_id="fred_cpiaucsl",
        connector_version="0.1.0",
        started_at=started,
        finished_at=started + timedelta(seconds=1),
        status=status,
        request_hash="abc123",
        retry_count=0,
        raw_storage_path=None,
        error=error,
    )


class TestDetectConsecutiveFailures:
    def test_no_runs_returns_none(self) -> None:
        assert detect_consecutive_failures([]) is None

    def test_below_threshold_returns_none(self) -> None:
        runs = [_run(status="failed", hours_offset=0)]
        assert detect_consecutive_failures(runs, threshold=2) is None

    def test_at_threshold_fires(self) -> None:
        runs = [
            _run(status="failed", hours_offset=0, run_id="run-1"),
            _run(status="failed", hours_offset=1, run_id="run-2", error="timeout"),
        ]
        alert = detect_consecutive_failures(runs, threshold=2)
        assert alert is not None
        assert alert.alert_type == "consecutive_failures"
        assert alert.dataset_id == "fred_cpiaucsl"
        assert alert.details["consecutive_failures"] == 2
        assert alert.details["latest_run_id"] == "run-2"
        assert alert.details["latest_error"] == "timeout"

    def test_a_success_breaks_the_streak(self) -> None:
        runs = [
            _run(status="failed", hours_offset=0),
            _run(status="failed", hours_offset=1),
            _run(status="success", hours_offset=2),
        ]
        assert detect_consecutive_failures(runs, threshold=2) is None

    def test_only_counts_the_trailing_streak(self) -> None:
        runs = [
            _run(status="failed", hours_offset=0),
            _run(status="success", hours_offset=1),
            _run(status="failed", hours_offset=2),
        ]
        # One failure at the end, one earlier -- not consecutive.
        assert detect_consecutive_failures(runs, threshold=2) is None


class TestDetectFreshnessBreach:
    def test_no_run_at_all_fires(self) -> None:
        alert = detect_freshness_breach(None, max_lag=timedelta(hours=1))
        assert alert is not None
        assert alert.alert_type == "freshness_breach"

    def test_latest_run_failed_fires(self) -> None:
        run = _run(status="failed")
        alert = detect_freshness_breach(
            run, max_lag=timedelta(hours=1), now=_T0 + timedelta(seconds=1)
        )
        assert alert is not None
        assert "did not succeed" in alert.message

    def test_within_max_lag_passes(self) -> None:
        run = _run(status="success")
        now = run.finished_at + timedelta(minutes=30)
        assert detect_freshness_breach(run, max_lag=timedelta(hours=1), now=now) is None

    def test_beyond_max_lag_fires(self) -> None:
        run = _run(status="success")
        now = run.finished_at + timedelta(hours=2)
        alert = detect_freshness_breach(run, max_lag=timedelta(hours=1), now=now)
        assert alert is not None
        assert alert.alert_type == "freshness_breach"
        assert alert.details["lag_seconds"] == 2 * 3600


class TestDetectBlockingQualityFailure:
    def test_no_results_returns_none(self) -> None:
        assert detect_blocking_quality_failure([]) is None

    def test_all_passing_returns_none(self) -> None:
        results = [
            DataQualityResult(
                test_id="value_positive",
                table_name="fact_economic_observation",
                run_id="run-1",
                status="pass",
                failed_rows=0,
                evaluated_at=_T0,
            )
        ]
        assert detect_blocking_quality_failure(results) is None

    def test_a_failure_fires(self) -> None:
        results = [
            DataQualityResult(
                test_id="value_positive",
                table_name="fact_economic_observation",
                run_id="run-1",
                status="fail",
                failed_rows=5,
                evaluated_at=_T0,
            ),
            DataQualityResult(
                test_id="primary_key_unique",
                table_name="fact_economic_observation",
                run_id="run-1",
                status="pass",
                failed_rows=0,
                evaluated_at=_T0,
            ),
        ]
        alert = detect_blocking_quality_failure(results)
        assert alert is not None
        assert alert.alert_type == "data_quality_blocking_failure"
        assert alert.dataset_id == "fact_economic_observation"
        assert alert.details["failing_test_ids"] == ["value_positive"]


class TestEmitAlert:
    def test_logs_at_error_level_as_json_with_details(self, caplog) -> None:
        alert = AlertEvent(
            alert_type="consecutive_failures",
            dataset_id="fred_cpiaucsl",
            message="2 consecutive ingestion failures for fred_cpiaucsl",
            details={"consecutive_failures": 2},
        )
        with caplog.at_level(logging.ERROR, logger="src.common.alerting"):
            emit_alert(alert)
        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.levelname == "ERROR"
        assert record.alert_type == "consecutive_failures"  # type: ignore[attr-defined]
        assert record.dataset_id == "fred_cpiaucsl"  # type: ignore[attr-defined]

    def test_emitted_line_is_valid_json(self, caplog) -> None:
        # emit_alert's logger binds its handler to sys.stdout once, at
        # import time -- before capsys can intercept it -- so we format the
        # captured record through the same formatter instead of reading stdout.
        alert = AlertEvent(
            alert_type="freshness_breach",
            dataset_id="fred_cpiaucsl",
            message="stale data",
        )
        with caplog.at_level(logging.ERROR, logger="src.common.alerting"):
            emit_alert(alert)
        line = _JSONFormatter().format(caplog.records[0])
        parsed = json.loads(line)
        assert parsed["level"] == "ERROR"
        assert parsed["alert_type"] == "freshness_breach"
        assert parsed["dataset_id"] == "fred_cpiaucsl"
